"""Tutorial 011: Triangle

The first real draw call: a vertex buffer with three vertices, a root
signature, vertex and pixel shaders and a graphics pipeline state object
(PSO). The command list sets the viewport, binds the render target and the
vertex buffer and draws.

Run: python tutorial011.py [--frames N]
"""
import math

import numpy

from pydx12 import *
from utils import (App, SwapChain, compile_shader, create_root_signature, enable_debug, get_best_adapter,
                   graphics_pipeline_desc, parse_args, setup_debug, transition, vertex_buffer_view,
                   viewport_and_scissor)

args = parse_args(__doc__)

enable_debug()
device = D3D12CreateDevice(get_best_adapter())
info = setup_debug(device)
queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))

app = App('pydx12: Tutorial 011 (Triangle)', 1024, 1024)
swap_chain = SwapChain(device, queue, app)

# x, y, r, g, b for each vertex
vertices = numpy.array([
    0.0, 0.8, 1, 0, 0,
    0.8, -0.8, 0, 1, 0,
    -0.8, -0.8, 0, 0, 1,
], dtype=numpy.float32)
vertex_buffer, vertex_buffer_view = vertex_buffer_view(device, queue, vertices, stride=5 * 4)

shader = """
struct vsout { float4 position : SV_Position; float3 color : COLOR; };

vsout vs(float2 position : POSITION, float3 color : COLOR)
{
    vsout OUT;
    OUT.position = float4(position, 0, 1);
    OUT.color = color;
    return OUT;
}

float4 ps(vsout IN) : SV_Target
{
    return float4(IN.color, 1);
}
"""
vertex_shader = compile_shader(shader, 'vs', 'vs_5_0')
pixel_shader = compile_shader(shader, 'ps', 'ps_5_0')

# no parameters: this pipeline only reads the input assembler
root_signature = create_root_signature(device)

pipeline_state = device.CreateGraphicsPipelineState(graphics_pipeline_desc(
    root_signature, vertex_shader, pixel_shader, [
        D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=DXGI_FORMAT_R32G32_FLOAT),
        D3D12_INPUT_ELEMENT_DESC(SemanticName='COLOR', Format=DXGI_FORMAT_R32G32B32_FLOAT,
                                 AlignedByteOffset=D3D12_APPEND_ALIGNED_ELEMENT),
    ]))

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
command_list = device.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
command_list.Close()

frame = 0
while app.pump() and (not args.frames or frame < args.frames):
    if app.resized:
        app.resized = False
        swap_chain.resize(app.width, app.height)
    back_buffer, rtv = swap_chain.current()
    viewports, scissors = viewport_and_scissor(swap_chain.width, swap_chain.height)

    allocator.Reset()
    command_list.Reset(allocator, pipeline_state)
    command_list.SetGraphicsRootSignature(root_signature)
    command_list.RSSetViewports(viewports)
    command_list.RSSetScissorRects(scissors)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_PRESENT,
                                             D3D12_RESOURCE_STATE_RENDER_TARGET)])
    command_list.OMSetRenderTargets(1, [rtv], False)
    pulse = 0.1 + 0.05 * math.sin(frame * 0.05)
    command_list.ClearRenderTargetView(rtv, (pulse, pulse, pulse * 1.5, 1))
    command_list.IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
    command_list.IASetVertexBuffers(0, [vertex_buffer_view])
    command_list.DrawInstanced(3, 1, 0, 0)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_RENDER_TARGET,
                                             D3D12_RESOURCE_STATE_PRESENT)])
    command_list.Close()
    queue.ExecuteCommandLists([command_list])
    swap_chain.present()
    frame += 1

app.destroy()
print('END')
