from re import sub
from numpy import pi
from pydx12 import *
import sys
import atexit
import random
import traceback


class App:
    running = True


def enable_debug():
    D3D12GetDebugInterface().EnableDebugLayer()


def get_best_adapter():
    factory = CreateDXGIFactory2()
    return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[-1]


def print_debug(info):
    for index in range(0, info.GetNumStoredMessages()):
        print(info.GetMessage(index).pDescription)
    info.ClearStoredMessages()


def setup_debug(device):
    info = ID3D12InfoQueue(device)

    def d3d12_debug_hook(*exc):
        traceback.print_exception(*exc)
        print_debug(info)
        App.running = False

    def d3d12_debug_exit_hook():
        print_debug(info)

    sys.excepthook = d3d12_debug_hook
    atexit.register(d3d12_debug_exit_hook)


class UploadBuffer:

    def __init__(self, device, size):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        buffer_desc.Width = size
        buffer_desc.Height = 1
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_UNKNOWN
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_GENERIC_READ, None)

    def upload(self, data):
        self.resource.upload(data)


class ResourceBuffer:
    def __init__(self, device, data):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        buffer_desc.Width = data.nbytes
        buffer_desc.Height = 1
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_UNKNOWN
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_GENERIC_READ, None)

        resource.upload(data)

        self.vertex_resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_COPY_DEST, None)

        command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
            Type=D3D12_COMMAND_LIST_TYPE_COPY)
        queue = device.CreateCommandQueue(command_queue_desc)

        fence = device.CreateFence()
        fence_event = Event()
        fence_value = fence.GetCompletedValue()
        fence_value += 1

        allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY)
        command_list = device.CreateCommandList(
            0, D3D12_COMMAND_LIST_TYPE_COPY, allocator)
        command_list.CopyResource(self.vertex_resource, resource)
        command_list.Close()

        queue.ExecuteCommandLists([command_list])
        queue.Signal(fence, fence_value)
        if fence.GetCompletedValue() < fence_value:
            fence.SetEventOnCompletion(fence_value, fence_event)
            fence_event.wait()


class Mesh:
    def __init__(self, device):
        self.has_index_buffer = False
        self.has_color_buffer = False
        self.device = device
        self.nvertices = 0
        self.matrix = None

    def set_vertex_buffer(self, buffer):
        self.vertex_buffer = ResourceBuffer(self.device, buffer)
        self.vertex_buffer_view = D3D12_VERTEX_BUFFER_VIEW(
            BufferLocation=self.vertex_buffer.vertex_resource.GetGPUVirtualAddress())
        self.vertex_buffer_view.SizeInBytes = buffer.nbytes
        self.vertex_buffer_view.StrideInBytes = 4 * 3

    def set_color_buffer(self, buffer):
        self.color_buffer = ResourceBuffer(self.device, buffer)
        self.color_buffer_view = D3D12_VERTEX_BUFFER_VIEW(
            BufferLocation=self.color_buffer.vertex_resource.GetGPUVirtualAddress())
        self.color_buffer_view.SizeInBytes = buffer.nbytes
        self.color_buffer_view.StrideInBytes = 4 * 3
        self.has_color_buffer = True

    def set_index_buffer(self, buffer):
        self.index_buffer = ResourceBuffer(self.device, buffer)
        self.index_buffer_view = D3D12_INDEX_BUFFER_VIEW(
            BufferLocation=self.index_buffer.vertex_resource.GetGPUVirtualAddress())
        self.index_buffer_view.SizeInBytes = buffer.nbytes
        self.index_buffer_view.Format = DXGI_FORMAT_R32_UINT
        self.has_index_buffer = True

    def set_nvertices(self, n):
        self.nvertices = n


class Texture:

    def __init__(self, device, width, height, uav=False, name=None):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D
        buffer_desc.Width = width
        buffer_desc.Height = height
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1
        if uav:
            buffer_desc.Flags = D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS
        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_COMMON, None)
        if name:
            self.resource.SetName(name)


class ReadbackBuffer:

    def __init__(self, device, size):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        buffer_desc.Width = size
        buffer_desc.Height = 1
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_UNKNOWN
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_READBACK), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_COPY_DEST, None)


class Barrier:

    def __init__(self, resource, before, after):
        self.barrier_desc = D3D12_RESOURCE_BARRIER(
            Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
        self.barrier_desc.Transition.pResource = resource
        self.barrier_desc.Transition.StateBefore = before
        self.barrier_desc.Transition.StateAfter = after


class Raytracer:

    def __init__(self, device):
        idxc_library = DxcCreateInstance(IDxcLibrary)
        idxc_compiler = DxcCreateInstance(IDxcCompiler)
        raygen_shader_code = """
struct HitInfo
{
	float4 ShadedColorAndHitT;
};

RWTexture2D<float4> RTOutput				: register(u0);
RaytracingAccelerationStructure SceneBVH : register(t0);

[shader("raygeneration")]
void RayGen()
{
	uint2 offset = DispatchRaysIndex().xy;
	float2 d = (((offset + 0.5f) / DispatchRaysDimensions().xy) * 2.f - 1.f);

	RayDesc ray;
	ray.Origin = float3(d.x, -d.y, -1);
	ray.Direction = float3(0, 0, 1);
	ray.TMin = 0.1f;
	ray.TMax = 1000.f;

	HitInfo payload;
	payload.ShadedColorAndHitT = float4(0.f, 0.f, 0.f, 0.f);

	TraceRay(
		SceneBVH,
		RAY_FLAG_NONE,
		0xFF,
		0,
		0,
		0,
		ray,
		payload);

	RTOutput[offset] = float4(payload.ShadedColorAndHitT.rgb, 1.f);
}
        """
        raygen_shader = idxc_compiler.Compile(idxc_library.CreateBlobWithEncodingOnHeapCopy(
            raygen_shader_code.encode('utf8')), 'shaders\\RayGen.hlsl', '', 'lib_6_3')
        print(raygen_shader)
        raygen_lib_desc = D3D12_DXIL_LIBRARY_DESC()
        raygen_lib_desc.DXILLibrary.pShaderBytecode = raygen_shader
        raygen_lib_desc.DXILLibrary.BytecodeLength = raygen_shader.GetBufferSize()
        raygen_lib_desc.NumExports = 1
        print(raygen_lib_desc.NumExports)
        raygen_lib_desc.pExports = [D3D12_EXPORT_DESC(
            Name='Raygen001', ExportToRename='RayGen')]
        print(raygen_lib_desc)

        raygen_subobject = D3D12_STATE_SUBOBJECT(
            Type=D3D12_STATE_SUBOBJECT_TYPE_DXIL_LIBRARY, pDesc=raygen_lib_desc)

        print(bytearray(raygen_lib_desc))
        print(raygen_subobject, len(bytearray(raygen_lib_desc)))

        shader_config = D3D12_RAYTRACING_SHADER_CONFIG(
            MaxPayloadSizeInBytes=16, MaxAttributeSizeInBytes=D3D12_RAYTRACING_MAX_ATTRIBUTE_SIZE_IN_BYTES)
        shader_config_subobject = D3D12_STATE_SUBOBJECT(
            Type=D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_SHADER_CONFIG, pDesc=shader_config)

        raytracing_pipeline_config_subobject = D3D12_STATE_SUBOBJECT(
            Type=D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_PIPELINE_CONFIG, pDesc=D3D12_RAYTRACING_PIPELINE_CONFIG(MaxTraceRecursionDepth=1))

        versioned_root_signature = D3D12_VERSIONED_ROOT_SIGNATURE_DESC(
            Version=D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned_root_signature.Version = D3D_ROOT_SIGNATURE_VERSION_1_1
        param0 = D3D12_ROOT_PARAMETER1(
            ParameterType=D3D12_ROOT_PARAMETER_TYPE_SRV)
        param1 = D3D12_ROOT_PARAMETER1(
            ParameterType=D3D12_ROOT_PARAMETER_TYPE_UAV)
        versioned_root_signature.Desc_1_1 = D3D12_ROOT_SIGNATURE_DESC1(
            NumParameters=1,
            pParameters=(param0, param1),
            Flags=D3D12_ROOT_SIGNATURE_FLAG_LOCAL_ROOT_SIGNATURE)

        print('DONE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

        serialized_root_signature = D3D12SerializeVersionedRootSignature(
            versioned_root_signature)
        root_signature = device.CreateRootSignature(
            0, serialized_root_signature)


        print('root signature', root_signature)
        root_signature_subobject = D3D12_STATE_SUBOBJECT(
            Type=D3D12_STATE_SUBOBJECT_TYPE_LOCAL_ROOT_SIGNATURE, pDesc=root_signature)

        """
        export_association = D3D12_SUBOBJECT_TO_EXPORTS_ASSOCIATION(NumExports=1, pExports=[
            'RayGen001'], pSubobjectToAssociate=root_signature_subobject.get_ptr())

        print('READY...', hex(root_signature_subobject.get_ptr()), export_association.to_dict())
        association_subobject = D3D12_STATE_SUBOBJECT(Type=D3D12_STATE_SUBOBJECT_TYPE_SUBOBJECT_TO_EXPORTS_ASSOCIATION, pDesc=export_association)

        print('subobject', association_subobject.to_dict())
        """
        #subobjects = (raygen_subobject, shader_config_subobject,
        #              raytracing_pipeline_config_subobject, root_signature_subobject)

        subobjects = [root_signature_subobject]
        pipeline_desc = D3D12_STATE_OBJECT_DESC(
            Type=D3D12_STATE_OBJECT_TYPE_RAYTRACING_PIPELINE)
        pipeline_desc.NumSubobjects = len(subobjects)
        pipeline_desc.pSubobjects = subobjects

        print(pipeline_desc.to_dict())
        print('root signature', root_signature_subobject.to_dict())
        pipeline = device.CreateStateObject(pipeline_desc)
        print(pipeline)

        pipeline_state_desc = D3D12_GRAPHICS_PIPELINE_STATE_DESC()
        pipeline_state_desc.pRootSignature = self.root_signature
        pipeline_state_desc.VS = D3D12_SHADER_BYTECODE(
            pShaderBytecode=vertex_shader, BytecodeLength=vertex_shader.GetBufferSize())
        pipeline_state_desc.PS = D3D12_SHADER_BYTECODE(
            pShaderBytecode=pixel_shader, BytecodeLength=pixel_shader.GetBufferSize())
        pipeline_state_desc.RasterizerState.FillMode = D3D12_FILL_MODE_SOLID
        pipeline_state_desc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE
        pipeline_state_desc.InputLayout.pInputElementDescs = [
            D3D12_INPUT_ELEMENT_DESC(
                SemanticName='POSITION', Format=DXGI_FORMAT_R32G32B32_FLOAT),
            D3D12_INPUT_ELEMENT_DESC(
                SemanticName='COLOR', InputSlot=1, Format=DXGI_FORMAT_R32G32B32_FLOAT)
        ]
        pipeline_state_desc.InputLayout.NumElements = 2
        pipeline_state_desc.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE
        pipeline_state_desc.NumRenderTargets = 1
        pipeline_state_desc.RTVFormats = (DXGI_FORMAT_R8G8B8A8_UNORM, )
        pipeline_state_desc.SampleDesc.Count = 1
        pipeline_state_desc.SampleMask = 0xFFFFFFFF
        pipeline_state_desc.BlendState.RenderTarget[0].RenderTargetWriteMask = D3D12_COLOR_WRITE_ENABLE_ALL
        self.pipeline_state = device.CreateGraphicsPipelineState(
            pipeline_state_desc)

        self.allocator = device.CreateCommandAllocator(
            D3D12_COMMAND_LIST_TYPE_DIRECT)
        self.command_list = device.CreateCommandList(
            0, D3D12_COMMAND_LIST_TYPE_DIRECT, self.allocator)
        self.command_list.Close()

    def execute(self, queue, back_buffer, rtv, width, height, meshes):
        self.command_list.Reset(self.allocator, self.pipeline_state)

        self.command_list.SetGraphicsRootSignature(self.root_signature)
        self.command_list.IASetPrimitiveTopology(
            D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
        self.command_list.OMSetRenderTargets([rtv])
        self.command_list.RSSetViewports(
            [D3D12_VIEWPORT(Width=width, Height=height, MinDepth=0, MaxDepth=1)])
        self.command_list.RSSetScissorRects(
            [D3D12_RECT(left=0, top=0, right=width, bottom=height)])

        self.command_list.ResourceBarrier([Barrier(
            back_buffer, D3D12_RESOURCE_STATE_PRESENT, D3D12_RESOURCE_STATE_RENDER_TARGET).barrier_desc])

        self.command_list.ClearRenderTargetView(
            rtv, (0, 0, 0, 1))

        for mesh in meshes:
            self.command_list.IASetVertexBuffers(0, [mesh.vertex_buffer_view])
            if mesh.has_color_buffer:
                self.command_list.IASetVertexBuffers(
                    1, [mesh.color_buffer_view])
            if mesh.matrix is not None:
                self.command_list.SetGraphicsRoot32BitConstants(0, mesh.matrix)
            if mesh.has_index_buffer:
                self.command_list.IASetIndexBuffer(mesh.index_buffer_view)
                self.command_list.DrawIndexedInstanced(
                    mesh.nvertices, 1, 0, 0, 0)
            else:
                self.command_list.DrawInstanced(mesh.nvertices, 1, 0, 0)

        self.command_list.ResourceBarrier([Barrier(
            back_buffer, D3D12_RESOURCE_STATE_RENDER_TARGET, D3D12_RESOURCE_STATE_PRESENT).barrier_desc])

        self.command_list.Close()

        queue.ExecuteCommandLists([self.command_list])
