"""Tutorial 013: Perspective

Replaces the orthographic projection with a perspective one: a grid of cubes
spreads away from a camera that slowly moves forward, so far cubes look
smaller. The window can be resized (the swapchain buffers are resized to
match and the aspect ratio follows), F toggles fullscreen and Escape quits.

Note there is still no depth buffer: cubes are drawn far to near, which is
enough here (tutorial 014 adds depth testing).

Run: python tutorial013.py [--frames N]
"""
import numpy
from pyrr import matrix44

from pydx12 import *
from utils import (App, Mesh, SwapChain, compile_shader, create_root_signature, cube, enable_debug,
                   get_best_adapter, graphics_pipeline_desc, parse_args, perspective, root_constants, setup_debug,
                   transition, viewport_and_scissor)

args = parse_args(__doc__)

enable_debug()
device = D3D12CreateDevice(get_best_adapter())
info = setup_debug(device)
queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))

app = App('pydx12: Tutorial 013 (Perspective)', 1280, 720)
app.root.bind('<KeyPress-f>', lambda event: app.toggle_fullscreen())
swap_chain = SwapChain(device, queue, app)

positions, colors, indices = cube()
mesh = Mesh(device, queue, [positions, colors], indices)

shader = """
cbuffer Transform : register(b0)
{
    row_major float4x4 matrix_mvp;
};

struct vsout { float4 position : SV_Position; float3 color : COLOR; };

vsout vs(float3 position : POSITION, float3 color : COLOR)
{
    vsout OUT;
    OUT.position = mul(float4(position, 1), matrix_mvp);
    OUT.color = color;
    return OUT;
}

float4 ps(vsout IN) : SV_Target
{
    return float4(IN.color, 1);
}
"""
root_signature = create_root_signature(device, [root_constants(0, 16)])
pipeline_desc = graphics_pipeline_desc(
    root_signature, compile_shader(shader, 'vs', 'vs_5_0'), compile_shader(shader, 'ps', 'ps_5_0'), [
        D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=0),
        D3D12_INPUT_ELEMENT_DESC(SemanticName='COLOR', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=1),
    ])
pipeline_desc.RasterizerState.CullMode = D3D12_CULL_MODE_BACK
pipeline_desc.RasterizerState.FrontCounterClockwise = True
pipeline_state = device.CreateGraphicsPipelineState(pipeline_desc)

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
command_list = device.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
command_list.Close()

# a 5x3 grid of cubes, from z=-4 to z=-40, sorted far to near
grid = sorted(((x * 2.5, y * 2.5, -4.0 - z * 4) for x in range(-2, 3) for y in range(-1, 2) for z in range(10)),
              key=lambda p: p[2])

theta = 0
forward = 0
frame = 0
while app.pump() and (not args.frames or frame < args.frames):
    if app.resized:
        app.resized = False
        swap_chain.resize(app.width, app.height)
    back_buffer, rtv = swap_chain.current()
    viewports, scissors = viewport_and_scissor(swap_chain.width, swap_chain.height)

    theta += 0.03
    forward = (forward + 0.05) % 8
    view = matrix44.create_from_translation((0, 0, forward), dtype=numpy.float32)
    projection = perspective(60, swap_chain.width / swap_chain.height, 0.1, 100)
    rotation = matrix44.create_from_y_rotation(theta, dtype=numpy.float32) @ \
        matrix44.create_from_x_rotation(theta * 0.5, dtype=numpy.float32)

    allocator.Reset()
    command_list.Reset(allocator, pipeline_state)
    command_list.SetGraphicsRootSignature(root_signature)
    command_list.RSSetViewports(viewports)
    command_list.RSSetScissorRects(scissors)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_PRESENT,
                                             D3D12_RESOURCE_STATE_RENDER_TARGET)])
    command_list.OMSetRenderTargets(1, [rtv], False)
    command_list.ClearRenderTargetView(rtv, (0.1, 0.1, 0.15, 1))
    command_list.IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
    for position in grid:
        model = rotation @ matrix44.create_from_translation(position, dtype=numpy.float32)
        mesh.matrix = model @ view @ projection
        mesh.draw(command_list)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_RENDER_TARGET,
                                             D3D12_RESOURCE_STATE_PRESENT)])
    command_list.Close()
    queue.ExecuteCommandLists([command_list])
    swap_chain.present()
    frame += 1

app.destroy()
print('END')
