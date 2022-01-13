from numpy import pi
from pydx12 import *
import sys
import atexit
import random

class App:
    running = True

def enable_debug():
    D3D12GetDebugInterface().EnableDebugLayer()


def get_best_adapter():
    factory = CreateDXGIFactory2()
    return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[0]


def print_debug(info):
    for index in range(0, info.GetNumStoredMessages()):
        print(info.GetMessage(index).pDescription)


def setup_debug(device):
    info = ID3D12InfoQueue(device)

    def d3d12_debug_hook(*exc):
        print_debug(info)
        print(exc)
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


class Rasterizer:

    def __init__(self, device):
        vs_code = """
cbuffer Matrix : register(b0)
{
    matrix proj;
};

struct vsin
{
    float3 position : POSITION;
    float3 color: COLOR;
};

struct vsout
{
    float4 position : SV_Position;
    float3 color : OUT_COLOR;
};

vsout main(vsin IN)
{
    vsout OUT;
    OUT.position = mul(float4(IN.position.xyz, 1), proj);
    OUT.color = IN.color;
    return OUT;
}
"""
        vertex_shader = D3DCompile(
            vs_code, None, None, None, 'main', 'vs_5_0', 0, 0)

        ps_code = """
struct psin
{
    float4 position : SV_Position;
    float3 color : OUT_COLOR;
};

float4 main(psin IN) : SV_Target
{
    return float4(IN.color, 1);
}
"""
        pixel_shader = D3DCompile(
            ps_code, None, None, None, 'main', 'ps_5_0', 0, 0)

        versioned_root_signature = D3D12_VERSIONED_ROOT_SIGNATURE_DESC(
            Version=D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned_root_signature.Version = D3D_ROOT_SIGNATURE_VERSION_1_1
        print(D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS)
        param0 = D3D12_ROOT_PARAMETER1(
            ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS)
        param0.Constants.Num32BitValues = 16
        print('SERIAL0')
        versioned_root_signature.Desc_1_1 = D3D12_ROOT_SIGNATURE_DESC1(
            NumParameters=1,
            pParameters=[param0],
            Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT)
        print('SERIAL1')
        # versioned_root_signature.Desc_1_1.pParameters=[param0]

        serialized_root_signature = D3D12SerializeVersionedRootSignature(
            versioned_root_signature)
        print('SERIAL2')
        self.root_signature = device.CreateRootSignature(
            0, serialized_root_signature)

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
