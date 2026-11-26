"""Tutorial 017: Raytracing (DXR)

Renders a set of spinning cubes with DirectX Raytracing instead of the
rasterizer:

* a bottom level acceleration structure (BLAS) holds the cube triangles;
* a top level acceleration structure (TLAS) holds one instance per cube with
  its transform, and is rebuilt every frame as the cubes move;
* a raytracing pipeline state object (ID3D12StateObject) is assembled from
  subobjects: the DXIL library compiled by DXC (ray generation, miss and
  closest hit shaders), a hit group, the shader/pipeline configs and the
  global root signature;
* the shader table holds the shader identifiers DispatchRays starts from;
* every pixel's ray writes its color into a UAV texture that is finally
  copied into the swapchain back buffer. Closest hit shaders cast a second
  ray toward the light, so cubes cast shadows on each other.

Requires a GPU with D3D12_RAYTRACING_TIER_1_0 or better.

Run: python tutorial017.py [--frames N]
"""
import ctypes
import math

import numpy
from pyrr import matrix44

from pydx12 import *
from utils import (App, SwapChain, build_acceleration_structure, compile_library, create_buffer,
                   create_root_signature, cube, default_buffer, enable_debug, get_best_adapter, instance_desc,
                   parse_args, perspective, root_constants, setup_debug, transition, uav_barrier, upload_buffer,
                   write_resource)

args = parse_args(__doc__)

enable_debug()
device = D3D12CreateDevice(get_best_adapter(), D3D_FEATURE_LEVEL_12_1, ID3D12Device5)
info = setup_debug(device)

options5 = D3D12_FEATURE_DATA_D3D12_OPTIONS5()
device.CheckFeatureSupport(D3D12_FEATURE_D3D12_OPTIONS5, ctypes.byref(options5), ctypes.sizeof(options5))
if options5.RaytracingTier < D3D12_RAYTRACING_TIER_1_0:
    raise SystemExit('this GPU does not support DirectX Raytracing')
print('raytracing tier: %d.%d' % divmod(options5.RaytracingTier, 10))

queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))
app = App('pydx12: Tutorial 017 (Raytracing)', 1280, 720)
app.root.bind('<KeyPress-f>', lambda event: app.toggle_fullscreen())
swap_chain = SwapChain(device, queue, app)

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
command_list = device.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator, None,
                                        ID3D12GraphicsCommandList4)

# --- geometry and the bottom level acceleration structure -------------------------------------
positions, colors, indices = cube()
vertex_buffer = default_buffer(device, queue, positions, D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE)
index_buffer = default_buffer(device, queue, indices, D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE)

geometry = D3D12_RAYTRACING_GEOMETRY_DESC(Type=D3D12_RAYTRACING_GEOMETRY_TYPE_TRIANGLES,
                                          Flags=D3D12_RAYTRACING_GEOMETRY_FLAG_OPAQUE)
geometry.Triangles = D3D12_RAYTRACING_GEOMETRY_TRIANGLES_DESC(
    IndexFormat=DXGI_FORMAT_R16_UINT, IndexCount=len(indices), IndexBuffer=index_buffer.GetGPUVirtualAddress(),
    VertexFormat=DXGI_FORMAT_R32G32B32_FLOAT, VertexCount=len(positions),
    VertexBuffer=D3D12_GPU_VIRTUAL_ADDRESS_AND_STRIDE(StartAddress=vertex_buffer.GetGPUVirtualAddress(),
                                                      StrideInBytes=12))
blas_inputs = D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
    Type=D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL,
    Flags=D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_TRACE,
    NumDescs=1, DescsLayout=D3D12_ELEMENTS_LAYOUT_ARRAY)
blas_inputs.pGeometryDescs = ctypes.pointer(geometry)  # `geometry` stays referenced by this module

blas, blas_scratch = build_acceleration_structure(device, command_list, blas_inputs)
command_list.Close()
queue.ExecuteCommandLists([command_list])
swap_chain.fence.flush(queue)

# --- the instances: a ring of cubes around a big flat one acting as the floor ----------------------
NUM_CUBES = 8
instance_buffer = create_buffer(device, NUM_CUBES * 2 * ctypes.sizeof(D3D12_RAYTRACING_INSTANCE_DESC),
                                D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ)


def instances(theta):
    descs = [instance_desc(matrix44.create_from_scale((12, 0.2, 12), dtype=numpy.float32) @
                           matrix44.create_from_translation((0, -1.2, 0), dtype=numpy.float32), blas, 0)]
    for i in range(NUM_CUBES):
        angle = theta * 0.3 + i * 2 * math.pi / NUM_CUBES
        model = matrix44.create_from_y_rotation(theta + i, dtype=numpy.float32) @ \
            matrix44.create_from_x_rotation(theta * 0.7 + i, dtype=numpy.float32) @ \
            matrix44.create_from_translation((math.cos(angle) * 3, 0.3 + math.sin(theta + i) * 0.5,
                                              math.sin(angle) * 3), dtype=numpy.float32)
        descs.append(instance_desc(model, blas, i + 1))
    return (D3D12_RAYTRACING_INSTANCE_DESC * len(descs))(*descs)


tlas_inputs = D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
    Type=D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL,
    Flags=D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_BUILD,
    NumDescs=NUM_CUBES + 1, DescsLayout=D3D12_ELEMENTS_LAYOUT_ARRAY,
    InstanceDescs=instance_buffer.GetGPUVirtualAddress())

# --- shaders --------------------------------------------------------------------------------------
shaders = """
struct Payload { float4 color; };
struct ShadowPayload { float lit; };

cbuffer Camera : register(b0)
{
    row_major float4x4 inverse_view_projection;
    float4 camera_position;
    float4 light_direction;
};
RaytracingAccelerationStructure scene : register(t0);
RWTexture2D<float4> output : register(u0);

static const float3 face_colors[6] = {
    float3(1, 0.2, 0.2), float3(0.2, 1, 1), float3(0.2, 1, 0.2),
    float3(1, 0.2, 1), float3(0.2, 0.2, 1), float3(1, 1, 0.2)
};
static const float3 face_normals[6] = {
    float3(1, 0, 0), float3(-1, 0, 0), float3(0, 1, 0), float3(0, -1, 0), float3(0, 0, 1), float3(0, 0, -1)
};

[shader("raygeneration")]
void RayGen()
{
    uint2 pixel = DispatchRaysIndex().xy;
    float2 ndc = ((pixel + 0.5) / DispatchRaysDimensions().xy) * 2 - 1;
    float4 target = mul(float4(ndc.x, -ndc.y, 1, 1), inverse_view_projection);

    RayDesc ray;
    ray.Origin = camera_position.xyz;
    ray.Direction = normalize(target.xyz / target.w - ray.Origin);
    ray.TMin = 0.001;
    ray.TMax = 1000;

    Payload payload;
    payload.color = float4(0, 0, 0, 0);
    // ray contribution to hit group index 0, geometry multiplier 0, miss shader 0
    TraceRay(scene, RAY_FLAG_NONE, 0xFF, 0, 0, 0, ray, payload);
    output[pixel] = float4(payload.color.rgb, 1);
}

[shader("miss")]
void Miss(inout Payload payload)
{
    float t = WorldRayDirection().y * 0.5 + 0.5;
    payload.color = float4(lerp(float3(0.9, 0.9, 1), float3(0.3, 0.5, 0.9), t), 1);
}

[shader("miss")]
void ShadowMiss(inout ShadowPayload payload)
{
    payload.lit = 1;
}

[shader("closesthit")]
void ClosestHit(inout Payload payload, in BuiltInTriangleIntersectionAttributes attributes)
{
    uint face = PrimitiveIndex() / 2; // two triangles per cube face
    float3 normal = normalize(mul(face_normals[face], (float3x3)ObjectToWorld3x4()));
    float3 color = InstanceID() == 0 ? float3(0.8, 0.8, 0.8) : face_colors[face];

    // shadow ray toward the light: skip closest hit shaders, use miss shader 1
    RayDesc shadow;
    shadow.Origin = WorldRayOrigin() + WorldRayDirection() * RayTCurrent() + normal * 0.001;
    shadow.Direction = -light_direction.xyz;
    shadow.TMin = 0.001;
    shadow.TMax = 1000;
    ShadowPayload shadow_payload;
    shadow_payload.lit = 0;
    TraceRay(scene, RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH | RAY_FLAG_SKIP_CLOSEST_HIT_SHADER, 0xFF, 0, 0, 1,
             shadow, shadow_payload);

    float lambert = saturate(dot(normal, -light_direction.xyz)) * shadow_payload.lit;
    payload.color = float4(color * (0.25 + 0.75 * lambert), 1);
}
"""
library = compile_library(shaders, 'lib_6_3')

# global root signature: [0] descriptor table with the output UAV, [1] TLAS as root SRV, [2] camera constants
uav_range = D3D12_DESCRIPTOR_RANGE1(RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=1,
                                    BaseShaderRegister=0)
table = D3D12_ROOT_PARAMETER1(ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE)
table.DescriptorTable = D3D12_ROOT_DESCRIPTOR_TABLE1(pDescriptorRanges=[uav_range])
root_signature = create_root_signature(device, [
    table,
    D3D12_ROOT_PARAMETER1(ParameterType=D3D12_ROOT_PARAMETER_TYPE_SRV,
                          Descriptor=D3D12_ROOT_DESCRIPTOR1(ShaderRegister=0)),
    root_constants(0, 24),
], flags=D3D12_ROOT_SIGNATURE_FLAG_NONE)

# --- the raytracing pipeline state object ---------------------------------------------------------
# every subobject points (pDesc) to its own desc structure: keep them all referenced
library_desc = D3D12_DXIL_LIBRARY_DESC(DXILLibrary=D3D12_SHADER_BYTECODE(pShaderBytecode=library))  # export all
hit_group_desc = D3D12_HIT_GROUP_DESC(HitGroupExport='HitGroup', Type=D3D12_HIT_GROUP_TYPE_TRIANGLES,
                                      ClosestHitShaderImport='ClosestHit')
shader_config = D3D12_RAYTRACING_SHADER_CONFIG(MaxPayloadSizeInBytes=16,
                                               MaxAttributeSizeInBytes=D3D12_RAYTRACING_MAX_ATTRIBUTE_SIZE_IN_BYTES)
pipeline_config = D3D12_RAYTRACING_PIPELINE_CONFIG(MaxTraceRecursionDepth=2)  # camera ray + shadow ray
global_root_signature = D3D12_GLOBAL_ROOT_SIGNATURE(pGlobalRootSignature=root_signature)
subobject_descs = [
    (D3D12_STATE_SUBOBJECT_TYPE_DXIL_LIBRARY, library_desc),
    (D3D12_STATE_SUBOBJECT_TYPE_HIT_GROUP, hit_group_desc),
    (D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_SHADER_CONFIG, shader_config),
    (D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_PIPELINE_CONFIG, pipeline_config),
    (D3D12_STATE_SUBOBJECT_TYPE_GLOBAL_ROOT_SIGNATURE, global_root_signature),
]
state_object = device.CreateStateObject(D3D12_STATE_OBJECT_DESC(
    Type=D3D12_STATE_OBJECT_TYPE_RAYTRACING_PIPELINE,
    pSubobjects=[D3D12_STATE_SUBOBJECT(Type=kind, pDesc=ctypes.addressof(desc)) for kind, desc in subobject_descs]))

# --- the shader table: one 64 bytes aligned record per shader (identifier only, no local arguments) -----
properties = ID3D12StateObjectProperties(state_object)
RECORD = D3D12_RAYTRACING_SHADER_TABLE_BYTE_ALIGNMENT
table_data = bytearray(RECORD * 4)
for slot, export in enumerate(('RayGen', 'Miss', 'ShadowMiss', 'HitGroup')):
    identifier = properties.GetShaderIdentifier(export)
    table_data[slot * RECORD:slot * RECORD + D3D12_SHADER_IDENTIFIER_SIZE_IN_BYTES] = \
        ctypes.string_at(identifier, D3D12_SHADER_IDENTIFIER_SIZE_IN_BYTES)
shader_table = upload_buffer(device, table_data)
table_address = shader_table.GetGPUVirtualAddress()
dispatch_desc = D3D12_DISPATCH_RAYS_DESC(
    RayGenerationShaderRecord=D3D12_GPU_VIRTUAL_ADDRESS_RANGE(StartAddress=table_address, SizeInBytes=RECORD),
    MissShaderTable=D3D12_GPU_VIRTUAL_ADDRESS_RANGE_AND_STRIDE(
        StartAddress=table_address + RECORD, SizeInBytes=RECORD * 2, StrideInBytes=RECORD),
    HitGroupTable=D3D12_GPU_VIRTUAL_ADDRESS_RANGE_AND_STRIDE(
        StartAddress=table_address + RECORD * 3, SizeInBytes=RECORD, StrideInBytes=RECORD),
    Depth=1)

# --- the output texture and its UAV in a shader visible descriptor heap ---------------------------
descriptor_heap = device.CreateDescriptorHeap(D3D12_DESCRIPTOR_HEAP_DESC(
    Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, NumDescriptors=1, Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE))


def create_output(width, height):
    desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=width, Height=height,
                               DepthOrArraySize=1, MipLevels=1, Format=DXGI_FORMAT_R8G8B8A8_UNORM,
                               Flags=D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
    desc.SampleDesc.Count = 1
    texture = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(Type=D3D12_HEAP_TYPE_DEFAULT),
                                             D3D12_HEAP_FLAG_NONE, desc, D3D12_RESOURCE_STATE_UNORDERED_ACCESS)
    device.CreateUnorderedAccessView(texture, None, D3D12_UNORDERED_ACCESS_VIEW_DESC(
        Format=DXGI_FORMAT_R8G8B8A8_UNORM, ViewDimension=D3D12_UAV_DIMENSION_TEXTURE2D),
        descriptor_heap.GetCPUDescriptorHandleForHeapStart())
    return texture


output = create_output(swap_chain.width, swap_chain.height)
light = numpy.array([-0.4, -1, -0.3], dtype=numpy.float32)
light /= numpy.linalg.norm(light)

theta = 0
frame = 0
while app.pump() and (not args.frames or frame < args.frames):
    if app.resized:
        app.resized = False
        swap_chain.resize(app.width, app.height)
        output = create_output(app.width, app.height)
    back_buffer, rtv = swap_chain.current()
    width, height = swap_chain.width, swap_chain.height

    theta += 0.01
    eye = numpy.array([math.sin(theta * 0.5) * 7, 3, math.cos(theta * 0.5) * 7], dtype=numpy.float32)
    view = matrix44.create_look_at(eye, (0, 0, 0), (0, 1, 0), dtype=numpy.float32)
    view_projection = view @ perspective(60, width / height, 0.1, 100)
    camera = numpy.concatenate([numpy.linalg.inv(view_projection).ravel(), eye, [1], light, [0]]).astype(
        numpy.float32)
    write_resource(instance_buffer, instances(theta))

    allocator.Reset()
    command_list.Reset(allocator)
    # rebuild the TLAS with the new transforms (scratch/result are kept until the frame is done)
    tlas, tlas_scratch = build_acceleration_structure(device, command_list, tlas_inputs)

    command_list.SetPipelineState1(state_object)
    command_list.SetComputeRootSignature(root_signature)  # raytracing uses the compute root signature
    command_list.SetDescriptorHeaps([descriptor_heap])
    command_list.SetComputeRootDescriptorTable(0, descriptor_heap.GetGPUDescriptorHandleForHeapStart())
    command_list.SetComputeRootShaderResourceView(1, tlas.GetGPUVirtualAddress())
    command_list.SetComputeRoot32BitConstants(2, len(camera), camera, 0)
    dispatch_desc.Width, dispatch_desc.Height = width, height
    command_list.DispatchRays(dispatch_desc)

    # copy the raytraced image into the back buffer
    command_list.ResourceBarrier([
        transition(output, D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_SOURCE),
        transition(back_buffer, D3D12_RESOURCE_STATE_PRESENT, D3D12_RESOURCE_STATE_COPY_DEST)])
    command_list.CopyResource(back_buffer, output)
    command_list.ResourceBarrier([
        transition(output, D3D12_RESOURCE_STATE_COPY_SOURCE, D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        transition(back_buffer, D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_PRESENT)])
    command_list.Close()
    queue.ExecuteCommandLists([command_list])
    swap_chain.present()
    frame += 1

app.destroy()
print('END')
