"""Tutorial 012: Cube

Indexed drawing and the first transformation matrix: a cube is stored as a
position buffer (slot 0), a color buffer (slot 1) and an index buffer. Each
frame a rotation matrix (built with pyrr) times an orthographic projection is
passed to the vertex shader as 16 root constants, and back faces are culled.

Run: python tutorial012.py [--frames N]
"""
import numpy
from pyrr import matrix44

from pydx12 import *
from utils import (App, Mesh, SwapChain, compile_shader, create_root_signature, cube, enable_debug,
                   get_best_adapter, graphics_pipeline_desc, orthographic, parse_args, root_constants,
                   setup_debug, transition, viewport_and_scissor)

args = parse_args(__doc__)

enable_debug()
device = D3D12CreateDevice(get_best_adapter())
info = setup_debug(device)
queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))

app = App('pydx12: Tutorial 012 (Cube)', 1024, 1024)
swap_chain = SwapChain(device, queue, app)

positions, colors, indices = cube()
mesh = Mesh(device, queue, [positions, colors], indices)

shader = """
cbuffer Transform : register(b0)
{
    row_major float4x4 matrix_mvp; // numpy/pyrr matrices are row major
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
# root parameter 0: 16 floats seen by the shaders as cbuffer b0
root_signature = create_root_signature(device, [root_constants(0, 16)])
pipeline_desc = graphics_pipeline_desc(
    root_signature, compile_shader(shader, 'vs', 'vs_5_0'), compile_shader(shader, 'ps', 'ps_5_0'), [
        D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=0),
        D3D12_INPUT_ELEMENT_DESC(SemanticName='COLOR', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=1),
    ])
# without a depth buffer, culling the faces looking away from the camera is enough for a convex object
pipeline_desc.RasterizerState.CullMode = D3D12_CULL_MODE_BACK
pipeline_desc.RasterizerState.FrontCounterClockwise = True
pipeline_state = device.CreateGraphicsPipelineState(pipeline_desc)

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
command_list = device.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
command_list.Close()

theta = 0
frame = 0
while app.pump() and (not args.frames or frame < args.frames):
    if app.resized:
        app.resized = False
        swap_chain.resize(app.width, app.height)
    back_buffer, rtv = swap_chain.current()
    viewports, scissors = viewport_and_scissor(swap_chain.width, swap_chain.height)

    theta += 0.02
    rotation = matrix44.create_from_y_rotation(theta, dtype=numpy.float32) @ \
        matrix44.create_from_x_rotation(theta * 0.7, dtype=numpy.float32)
    camera = matrix44.create_from_translation((0, 0, -3), dtype=numpy.float32)
    aspect = swap_chain.width / swap_chain.height
    mesh.matrix = rotation @ camera @ orthographic(3 * aspect, 3, 0.1, 10)

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
    mesh.draw(command_list)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_RENDER_TARGET,
                                             D3D12_RESOURCE_STATE_PRESENT)])
    command_list.Close()
    queue.ExecuteCommandLists([command_list])
    swap_chain.present()
    frame += 1

app.destroy()
print('END')
