from numpy import pi
from pydx12 import *
import sys
import atexit
import random
import json
import base64
import math


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

    def d3d12_debug_exit_hook():
        print_debug(info)

    sys.excepthook = d3d12_debug_hook
    atexit.register(d3d12_debug_exit_hook)


class GLTF:
    def __init__(self, filename):
        self.asset = json.load(open(filename, 'rb'))
        self.size_table = {
            5123: 2,  # unsigned short
            5126: 4,  # float
            5125: 4,  # unsigned int
            'VEC3': 3,
            'VEC2': 2,
            'VEC4': 4,
            'SCALAR': 1
        }

    def get_accessor_bytes(self, accessor_index):
        accessor = self.asset['accessors'][accessor_index]
        buffer_view = self.asset['bufferViews'][accessor['bufferView']]
        print('bufferView', buffer_view)
        prefix = 'data:application/octet-stream;base64,'
        buffer = base64.b64decode(
            self.asset['buffers'][buffer_view['buffer']]['uri'][len(prefix):])
        print('buffer size', len(buffer))
        buffer_data = buffer[buffer_view['byteOffset']:buffer_view['byteOffset']+buffer_view['byteLength']]
        print('buffer data size', len(buffer_data))
        accessor_data_start = accessor['byteOffset']
        accessor_data_size = accessor['count'] * \
            self.size_table[accessor['componentType']] * \
            self.size_table[accessor['type']]
        return buffer_data[accessor_data_start:
                           accessor_data_start+accessor_data_size]

    def get_indices(self, mesh_index):
        mesh = self.asset['meshes'][mesh_index]
        primitive = mesh['primitives'][0]
        indices = primitive['indices']
        return self.get_accessor_bytes(indices)

    def get_vertices(self, mesh_index):
        mesh = self.asset['meshes'][mesh_index]
        primitive = mesh['primitives'][0]
        position = primitive['attributes']['POSITION']
        return self.get_accessor_bytes(position)

    def get_colors(self, mesh_index):
        mesh = self.asset['meshes'][mesh_index]
        primitive = mesh['primitives'][0]
        color = primitive['attributes']['COLOR_0']
        return self.get_accessor_bytes(color)

    def get_nvertices(self, mesh_index):
        mesh = self.asset['meshes'][mesh_index]
        primitive = mesh['primitives'][0]
        indices = primitive['indices']
        return self.asset['accessors'][indices]['count']


class ResourceBuffer:
    def __init__(self, device, data):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        buffer_desc.Width = len(data)
        buffer_desc.Height = 1
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_UNKNOWN
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_GENERIC_READ, None)

        self.resource.upload(data)

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
        command_list.CopyResource(self.vertex_resource, self.resource)
        command_list.Close()

        queue.ExecuteCommandLists([command_list])
        queue.Signal(fence, fence_value)
        if fence.GetCompletedValue() < fence_value:
            fence.SetEventOnCompletion(fence_value, fence_event)
            fence_event.wait()


class DepthStencilTexture:

    def __init__(self, device, width, height, uav=False, name=None):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D
        buffer_desc.Width = width
        buffer_desc.Height = height
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_D24_UNORM_S8_UINT
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1
        buffer_desc.Flags = D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL
        if uav:
            buffer_desc.Flags = D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS
        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_DEPTH_WRITE, D3D12_CLEAR_VALUE(Format=DXGI_FORMAT_D24_UNORM_S8_UINT, Color=(1, 1, 1, 1)))
        if name:
            self.resource.SetName(name)


class Mesh:
    def __init__(self, device):
        self.has_index_buffer = False
        self.has_color_buffer = False
        self.device = device
        self.nvertices = 0
        self.npositions = 0
        self.matrix = None

    def set_vertex_buffer(self, buffer):
        self.vertex_buffer = ResourceBuffer(self.device, buffer)
        self.vertex_buffer_view = D3D12_VERTEX_BUFFER_VIEW(
            BufferLocation=self.vertex_buffer.vertex_resource.GetGPUVirtualAddress())
        self.vertex_buffer_view.SizeInBytes = len(buffer)
        self.vertex_buffer_view.StrideInBytes = 4 * 3
        self.npositions = self.vertex_buffer_view.SizeInBytes // 4

    def set_color_buffer(self, buffer):
        self.color_buffer = ResourceBuffer(self.device, buffer)
        self.color_buffer_view = D3D12_VERTEX_BUFFER_VIEW(
            BufferLocation=self.color_buffer.vertex_resource.GetGPUVirtualAddress())
        self.color_buffer_view.SizeInBytes = len(buffer)
        self.color_buffer_view.StrideInBytes = 4 * 3
        self.has_color_buffer = True

    def set_index_buffer(self, buffer):
        self.index_buffer = ResourceBuffer(self.device, buffer)
        self.index_buffer_view = D3D12_INDEX_BUFFER_VIEW(
            BufferLocation=self.index_buffer.vertex_resource.GetGPUVirtualAddress())
        self.index_buffer_view.SizeInBytes = len(buffer)
        self.index_buffer_view.Format = DXGI_FORMAT_R16_UINT
        self.has_index_buffer = True

    def set_nvertices(self, n):
        self.nvertices = n


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
struct vsin
{
    float3 controlpoint : POSITION;
};

struct vsout
{
    float3 controlpoint : CONTROLPOINT;
};

vsout main(vsin IN)
{
    vsout OUT;
    OUT.controlpoint = IN.controlpoint;
    return OUT;
}
"""
        vertex_shader = D3DCompile(
            vs_code, None, [], None, 'main', 'vs_5_0', 0, 0)

        print('VERTEX SHADER', vertex_shader)

        hs_code = """
struct hsin
{
    float3 controlpoint : CONTROLPOINT;
};

struct constant_out
{
    float edges[3] : SV_TessFactor;
    float inside : SV_InsideTessFactor;
};

struct hsout
{
    float3 controlpoint : CONTROLPOINT;
};

cbuffer tessellation_config : register(b0)
{
    uint inside;
}

constant_out constant_func(InputPatch<hsin, 1> inputPatch, uint patchId : SV_PrimitiveID)
{    
    constant_out OUT;
    OUT.edges[0] = 1;
    OUT.edges[1] = 1;
    OUT.edges[2] = 1;
    OUT.inside = inside;
    return OUT;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(1)]
[patchconstantfunc("constant_func")]
hsout main(InputPatch<hsin, 1> patch, uint pointId : SV_OutputControlPointID, uint patchId : SV_PrimitiveID)
{
    hsout OUT;
    OUT.controlpoint = patch[0].controlpoint;
    return OUT;
}
        """

        hull_shader = D3DCompile(
            hs_code, None, [], None, 'main', 'hs_5_0', 0, 0)

        ds_code = """
struct constant_out
{
    float edges[3] : SV_TessFactor;
    float inside : SV_InsideTessFactor;
};

struct hsout
{
    float3 controlpoint : CONTROLPOINT;
};

struct psin
{
    float4 position : SV_Position;
    float red : RED;
};

[domain("tri")]
psin main(constant_out IN, float3 uvw : SV_DomainLocation, const OutputPatch<hsout, 1> patch, uint patchId : SV_PrimitiveID)
{
    psin OUT;
    float x = patch[0].controlpoint.x + uvw.x;
    float y = patch[0].controlpoint.y + uvw.y;
    float r = patch[0].controlpoint.z;
    float rx = x * cos(r) - y * sin(r);
    float ry = x * sin(r) + y * cos(r);
    float2 xy = float2(rx, ry) * 0.5;
    OUT.position = float4(xy, 0, 1);
    OUT.red = patch[0].controlpoint.z / (PI * 0.5);
    return OUT;
}
        """

        domain_shader = D3DCompile(
            ds_code, None, [D3D_SHADER_MACRO(Name='PI', Definition=str(math.pi))], None, 'main', 'ds_5_0', 0, 0)

        ps_code = """
struct psin
{
    float4 position : SV_Position;
    float red : RED;
};

float4 main(psin IN) : SV_Target
{
    return float4(IN.red / 4, 0, 1, 1);
}

"""
        pixel_shader = D3DCompile(
            ps_code, None, None, None, 'main', 'ps_5_0', 0, 0)

        versioned_root_signature = D3D12_VERSIONED_ROOT_SIGNATURE_DESC(
            Version=D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned_root_signature.Version = D3D_ROOT_SIGNATURE_VERSION_1_1
        param0 = D3D12_ROOT_PARAMETER1(
            ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS)
        param0.Constants.Num32BitValues = 16
        param0.Constants.ShaderRegister = 1
        param1 = D3D12_ROOT_PARAMETER1(
            ParameterType=D3D12_ROOT_PARAMETER_TYPE_CBV)
        param1.Descriptor.ShaderRegister = 0
        versioned_root_signature.Desc_1_1 = D3D12_ROOT_SIGNATURE_DESC1(
            Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT)
        versioned_root_signature.Desc_1_1.pParameters = (param0, param1)
        versioned_root_signature.Desc_1_1.NumParameters = 2

        serialized_root_signature = D3D12SerializeVersionedRootSignature(
            versioned_root_signature)
        self.root_signature = device.CreateRootSignature(
            0, serialized_root_signature)

        pipeline_state_desc = D3D12_GRAPHICS_PIPELINE_STATE_DESC()
        pipeline_state_desc.pRootSignature = self.root_signature
        pipeline_state_desc.VS = D3D12_SHADER_BYTECODE(
            pShaderBytecode=vertex_shader, BytecodeLength=vertex_shader.GetBufferSize())
        pipeline_state_desc.HS = D3D12_SHADER_BYTECODE(
            pShaderBytecode=hull_shader, BytecodeLength=hull_shader.GetBufferSize())
        pipeline_state_desc.DS = D3D12_SHADER_BYTECODE(
            pShaderBytecode=domain_shader, BytecodeLength=domain_shader.GetBufferSize())
        pipeline_state_desc.PS = D3D12_SHADER_BYTECODE(
            pShaderBytecode=pixel_shader, BytecodeLength=pixel_shader.GetBufferSize())
        pipeline_state_desc.RasterizerState.FillMode = D3D12_FILL_MODE_WIREFRAME
        pipeline_state_desc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE
        pipeline_state_desc.InputLayout.pInputElementDescs = [
            D3D12_INPUT_ELEMENT_DESC(
                SemanticName='POSITION', Format=DXGI_FORMAT_R32G32B32_FLOAT),
            D3D12_INPUT_ELEMENT_DESC(
                SemanticName='COLOR', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=1),
        ]

        pipeline_state_desc.InputLayout.NumElements = 2
        pipeline_state_desc.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_PATCH
        pipeline_state_desc.NumRenderTargets = 1
        pipeline_state_desc.RTVFormats = (DXGI_FORMAT_R8G8B8A8_UNORM, )
        pipeline_state_desc.DSVFormat = DXGI_FORMAT_D24_UNORM_S8_UINT
        pipeline_state_desc.DepthStencilState.DepthEnable = True
        pipeline_state_desc.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ALL
        pipeline_state_desc.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_LESS
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

        self.depth_texture = DepthStencilTexture(device, 1024, 1024)
        descriptor_heap_desc = D3D12_DESCRIPTOR_HEAP_DESC(
            Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV,
            NumDescriptors=1)
        descriptor_heap = device.CreateDescriptorHeap(descriptor_heap_desc)
        self.dsv = descriptor_heap.cpu(0)

        device.CreateDepthStencilView(
            self.depth_texture.resource, None, self.dsv)

    def execute(self, queue, back_buffer, rtv, meshes, tessellation_config):
        self.command_list.Reset(self.allocator, self.pipeline_state)

        self.command_list.SetGraphicsRootSignature(self.root_signature)
        self.command_list.IASetPrimitiveTopology(
            D3D_PRIMITIVE_TOPOLOGY_1_CONTROL_POINT_PATCHLIST)
        self.command_list.OMSetRenderTargets([rtv], self.dsv)
        self.command_list.RSSetViewports(
            [D3D12_VIEWPORT(Width=1024, Height=1024, MinDepth=0., MaxDepth=1.)])
        self.command_list.RSSetScissorRects(
            [D3D12_RECT(left=0, top=0, right=1024, bottom=1024)])

        self.command_list.SetGraphicsRootConstantBufferView(
            1, tessellation_config.resource.GetGPUVirtualAddress())

        self.command_list.ResourceBarrier([Barrier(
            back_buffer, D3D12_RESOURCE_STATE_PRESENT, D3D12_RESOURCE_STATE_RENDER_TARGET).barrier_desc])

        self.command_list.ClearRenderTargetView(
            rtv, (0, 0, 0, 1))
        self.command_list.ClearDepthStencilView(
            self.dsv, D3D12_CLEAR_FLAG_DEPTH, 1, 0)

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
