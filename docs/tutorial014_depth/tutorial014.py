"""Tutorial 014: Depth buffer (and loading glTF models)

Loads a glTF model (Duck.gltf by default, pass another file as argument) and
draws a ring of copies that intersect each other. Instead of sorting
triangles we now attach a depth buffer (DSV) to the output merger and enable
depth testing in the pipeline: the nearest surface wins per pixel.
Shading is a simple Lambert term computed from the model normals.

Run: python tutorial014.py [model.gltf|model.glb] [--frames N]
"""
import argparse
import math

import numpy
from pyrr import matrix44

from pydx12 import *
from utils import (GLTF, App, DepthBuffer, Mesh, SwapChain, compile_shader, create_root_signature, enable_debug,
                   get_best_adapter, graphics_pipeline_desc, perspective, root_constants, setup_debug, transition,
                   viewport_and_scissor)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('model', nargs='?', default='Duck.gltf')
parser.add_argument('--frames', type=int, default=0)
args = parser.parse_args()

enable_debug()
device = D3D12CreateDevice(get_best_adapter())
info = setup_debug(device)
queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))

app = App('pydx12: Tutorial 014 (Depth)', 1280, 720)
app.root.bind('<KeyPress-f>', lambda event: app.toggle_fullscreen())
swap_chain = SwapChain(device, queue, app)
depth_buffer = DepthBuffer(device, app.width, app.height)

# --- the model: positions and normals in two vertex buffers -------------------------------------
gltf = GLTF(args.model)
attributes, indices, model_matrix = gltf.primitive(0)
positions = attributes['POSITION']
normals = attributes.get('NORMAL', numpy.zeros_like(positions))
# bring the model to a unit size centered at the origin
world = numpy.c_[positions, numpy.ones(len(positions), dtype=numpy.float32)] @ model_matrix
low, high = world[:, :3].min(axis=0), world[:, :3].max(axis=0)
fit = matrix44.create_from_translation(-(low + high) / 2, dtype=numpy.float32) @ \
    matrix44.create_from_scale([1.5 / max(high - low)] * 3, dtype=numpy.float32)
mesh = Mesh(device, queue, [positions, normals], indices)
print('%s: %d vertices, %d indices' % (args.model, len(positions), len(indices)))

shader = """
cbuffer Transform : register(b0)
{
    row_major float4x4 matrix_mvp;   // model -> clip space
    row_major float4x4 matrix_model; // model -> world (for the normals)
};

struct vsout { float4 position : SV_Position; float3 normal : NORMAL; };

vsout vs(float3 position : POSITION, float3 normal : NORMAL)
{
    vsout OUT;
    OUT.position = mul(float4(position, 1), matrix_mvp);
    OUT.normal = mul(float4(normal, 0), matrix_model).xyz;
    return OUT;
}

float4 ps(vsout IN) : SV_Target
{
    float3 light = normalize(float3(0.5, 1, 0.8));
    float lambert = saturate(dot(normalize(IN.normal), light));
    return float4(float3(1, 0.8, 0.2) * (0.25 + 0.75 * lambert), 1);
}
"""
root_signature = create_root_signature(device, [root_constants(0, 32)])
pipeline_desc = graphics_pipeline_desc(
    root_signature, compile_shader(shader, 'vs', 'vs_5_0'), compile_shader(shader, 'ps', 'ps_5_0'), [
        D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=0),
        D3D12_INPUT_ELEMENT_DESC(SemanticName='NORMAL', Format=DXGI_FORMAT_R32G32B32_FLOAT, InputSlot=1),
    ])
pipeline_desc.RasterizerState.CullMode = D3D12_CULL_MODE_BACK
pipeline_desc.RasterizerState.FrontCounterClockwise = True  # glTF triangles are counter clockwise
# depth testing: keep the fragment only if it is nearer than what is already in the depth buffer
pipeline_desc.DSVFormat = depth_buffer.format
pipeline_desc.DepthStencilState.DepthEnable = True
pipeline_desc.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ALL
pipeline_desc.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_LESS
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
        depth_buffer.resize(app.width, app.height)
    back_buffer, rtv = swap_chain.current()
    viewports, scissors = viewport_and_scissor(swap_chain.width, swap_chain.height)

    theta += 0.01
    view = matrix44.create_from_translation((0, -0.4, -4.2), dtype=numpy.float32)
    projection = perspective(60, swap_chain.width / swap_chain.height, 0.1, 100)

    allocator.Reset()
    command_list.Reset(allocator, pipeline_state)
    command_list.SetGraphicsRootSignature(root_signature)
    command_list.RSSetViewports(viewports)
    command_list.RSSetScissorRects(scissors)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_PRESENT,
                                             D3D12_RESOURCE_STATE_RENDER_TARGET)])
    command_list.OMSetRenderTargets(1, [rtv], False, depth_buffer.dsv)
    command_list.ClearRenderTargetView(rtv, (0.1, 0.1, 0.15, 1))
    command_list.ClearDepthStencilView(depth_buffer.dsv, D3D12_CLEAR_FLAG_DEPTH, 1.0, 0)
    command_list.IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
    for i in range(6):  # six intersecting copies on a rotating ring, drawn in no particular order
        angle = theta + i * math.pi / 3
        model = model_matrix @ fit @ matrix44.create_from_y_rotation(-angle * 2, dtype=numpy.float32) @ \
            matrix44.create_from_translation((math.cos(angle) * 1.1, 0, math.sin(angle) * 1.1), dtype=numpy.float32)
        command_list.SetGraphicsRoot32BitConstants(0, 16, model.astype(numpy.float32), 16)
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
