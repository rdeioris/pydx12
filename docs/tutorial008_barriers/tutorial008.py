import time
from pydx12 import *
from utils import get_best_adapter, enable_debug, print_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer
from PIL import Image
import gc
import sys

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

setup_debug(device)

image = Image.open('python-logo.png')
width, height = image.size
print(width, height)
texture = Texture(device, width, height)
footprint, num_rows, row_size_in_bytes, total_bytes = device.GetCopyableFootprints(
    texture.resource.GetDesc(), 0, 1, 0)

print(footprint.Footprint.to_dict(), num_rows, row_size_in_bytes, total_bytes)

original_bytes = image.tobytes()
bitmap_size = footprint.Footprint.RowPitch * footprint.Footprint.Height
fixed_bytes = bytearray(bitmap_size)

row_pitch = footprint.Footprint.RowPitch

for y in range(0, footprint.Footprint.Height):
    destination_offset = row_pitch * y
    source_offset = width * 4 * y
    fixed_bytes[destination_offset:destination_offset +
                (width * 4)] = original_bytes[source_offset:source_offset + (width * 4)]

print(len(fixed_bytes))

upload_buffer = UploadBuffer(device, bitmap_size)
upload_buffer.upload(fixed_bytes)

texture_uav = Texture(device, width, height, uav=True)

readback_buffer = ReadbackBuffer(device, bitmap_size)

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_COMPUTE)
queue = device.CreateCommandQueue(command_queue_desc)

fence = device.CreateFence()
fence_event = Event()

cs_code = """
Texture2D<float4> input : register(t0);
RWTexture2D<float4> output : register(u0);

[numthreads(8, 8, 1)]
void main(uint3 ThreadId : SV_DispatchThreadID)
{
    float4 color = input[ThreadId.xy];
    float r = color.r;
    color.r = color.b;
    color.b = r;
    output[ThreadId.xy] = color;
}
"""
compute_shader = D3DCompile(cs_code, None, None, None, 'main', 'cs_5_0')

versioned_root_signature = D3D12_VERSIONED_ROOT_SIGNATURE_DESC(
    Version=D3D_ROOT_SIGNATURE_VERSION_1_1)
versioned_root_signature.Desc_1_1.NumParameters = 1
versioned_root_signature.Desc_1_1.pParameters = [
    D3D12_ROOT_PARAMETER1(ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE,
                          DescriptorTable=D3D12_ROOT_DESCRIPTOR_TABLE1(NumDescriptorRanges=2, pDescriptorRanges=[
                              D3D12_DESCRIPTOR_RANGE1(
                                  RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV, NumDescriptors=1, Flags=D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE),
                              D3D12_DESCRIPTOR_RANGE1(
                                  RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=1, Flags=D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE, OffsetInDescriptorsFromTableStart=D3D12_DESCRIPTOR_RANGE_OFFSET_APPEND),
                          ]))
]

serialized_root_signature = D3D12SerializeVersionedRootSignature(
    versioned_root_signature)
root_signature = device.CreateRootSignature(0, serialized_root_signature)

print(root_signature)

descriptor_heap_desc = D3D12_DESCRIPTOR_HEAP_DESC(
    Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV,
    NumDescriptors=2,
    Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE)
descriptor_heap = device.CreateDescriptorHeap(descriptor_heap_desc)
cpu_descriptors = descriptor_heap.cpu((0, 1))
gpu_descriptors = descriptor_heap.gpu((0, 1))

device.CreateShaderResourceView(texture.resource, None, cpu_descriptors[0])
device.CreateUnorderedAccessView(
    texture_uav.resource, None, None, cpu_descriptors[1])

compute_pipeline_compute_state_desc = D3D12_COMPUTE_PIPELINE_STATE_DESC()
compute_pipeline_compute_state_desc.pRootSignature = root_signature
compute_pipeline_compute_state_desc.CS = D3D12_SHADER_BYTECODE(
    pShaderBytecode=compute_shader, BytecodeLength=compute_shader.GetBufferSize())

compute_pipeline_state = device.CreateComputePipelineState(
    compute_pipeline_compute_state_desc)

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COMPUTE)
command_list = device.CreateCommandList(
    0, D3D12_COMMAND_LIST_TYPE_COMPUTE, allocator, compute_pipeline_state)

texture_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture.resource)

texture_uav_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture_uav.resource)

upload_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=upload_buffer.resource, PlacedFootprint=footprint)

readback_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=readback_buffer.resource, PlacedFootprint=footprint)

command_list.CopyTextureRegion(
    texture_copy_location, 0, 0, 0, upload_buffer_copy_location, None)
barrier000 = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
barrier000.Transition.pResource = texture.resource
barrier000.Transition.StateBefore = D3D12_RESOURCE_STATE_COPY_DEST
barrier000.Transition.StateAfter = D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE
command_list.ResourceBarrier([barrier000])
command_list.SetDescriptorHeaps([descriptor_heap])
command_list.SetComputeRootSignature(root_signature)
command_list.SetComputeRootDescriptorTable(0, gpu_descriptors[0])
command_list.Dispatch(320, 21, 1)
barrier001 = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
barrier001.Transition.pResource = texture.resource
barrier001.Transition.StateBefore = D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE
barrier001.Transition.StateAfter = D3D12_RESOURCE_STATE_COPY_SOURCE
command_list.ResourceBarrier([barrier001])
command_list.CopyTextureRegion(
    readback_buffer_copy_location, 0, 0, 0, texture_uav_copy_location, None)
command_list.Close()

queue.ExecuteCommandLists([command_list])
queue.Signal(fence, 1)
if fence.GetCompletedValue() < 1:
    fence.SetEventOnCompletion(1, fence_event)
    fence_event.wait()

destination = Image.frombytes(
    'RGBA', (footprint.Footprint.RowPitch // 4, height), readback_buffer.resource.download())
destination.save('foo.png')