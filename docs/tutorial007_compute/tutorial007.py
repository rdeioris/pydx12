from PIL import Image

from pydx12 import *
from utils import (get_best_adapter, enable_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer,
                   get_footprint, pad_rows, Fence)

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

setup_debug(device)

image = Image.open('python-logo.png').convert('RGBA')
width, height = image.size
print(width, height)
texture = Texture(device, width, height)
footprint, num_rows, row_size_in_bytes, total_bytes = get_footprint(device, texture.resource)

row_pitch = footprint.Footprint.RowPitch
bitmap_size = row_pitch * num_rows
upload_buffer = UploadBuffer(device, bitmap_size)
upload_buffer.upload(pad_rows(image.tobytes(), width * 4, row_pitch, num_rows))

# The compute shader writes into this texture through an Unordered Access View.
# We do not know about barriers yet (next tutorial), so we use ALLOW_SIMULTANEOUS_ACCESS:
# such textures are implicitly promoted to whatever state a command needs (UAV, copy source...).
texture_uav = Texture(device, width, height,
                      D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS | D3D12_RESOURCE_FLAG_ALLOW_SIMULTANEOUS_ACCESS)

readback_buffer = ReadbackBuffer(device, bitmap_size)

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_COMPUTE)
queue = device.CreateCommandQueue(command_queue_desc)

fence = Fence(device)

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

# the root signature declares what the shader can access: here a descriptor table with an SRV and an UAV
versioned_root_signature = D3D12_VERSIONED_ROOT_SIGNATURE_DESC(
    Version=D3D_ROOT_SIGNATURE_VERSION_1_1)
# assigning a list to a pointer field also sets its count field (NumParameters, NumDescriptorRanges)
versioned_root_signature.Desc_1_1.pParameters = [
    D3D12_ROOT_PARAMETER1(ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE,
                          DescriptorTable=D3D12_ROOT_DESCRIPTOR_TABLE1(pDescriptorRanges=[
                              D3D12_DESCRIPTOR_RANGE1(
                                  RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV, NumDescriptors=1,
                                  Flags=D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE),
                              D3D12_DESCRIPTOR_RANGE1(
                                  RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=1,
                                  Flags=D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE,
                                  OffsetInDescriptorsFromTableStart=D3D12_DESCRIPTOR_RANGE_OFFSET_APPEND),
                          ]))
]
print('root parameters:', versioned_root_signature.Desc_1_1.NumParameters)

serialized_root_signature = D3D12SerializeVersionedRootSignature(
    versioned_root_signature)
root_signature = device.CreateRootSignature(0, serialized_root_signature)

print(root_signature)

# a shader visible heap with 2 descriptors: [0] = SRV of the source, [1] = UAV of the destination
descriptor_heap_desc = D3D12_DESCRIPTOR_HEAP_DESC(
    Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV,
    NumDescriptors=2,
    Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE)
descriptor_heap = device.CreateDescriptorHeap(descriptor_heap_desc)
increment = device.GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)
cpu_start = descriptor_heap.GetCPUDescriptorHandleForHeapStart().ptr
gpu_start = descriptor_heap.GetGPUDescriptorHandleForHeapStart().ptr
cpu_descriptors = [D3D12_CPU_DESCRIPTOR_HANDLE(cpu_start + i * increment) for i in range(2)]
gpu_descriptors = [D3D12_GPU_DESCRIPTOR_HANDLE(gpu_start + i * increment) for i in range(2)]

print(cpu_descriptors[0].ptr, cpu_descriptors[1].ptr)
print(gpu_descriptors[0].ptr, gpu_descriptors[1].ptr)

# None descriptions mean "default view of the whole resource"
device.CreateShaderResourceView(texture.resource, None, cpu_descriptors[0])
device.CreateUnorderedAccessView(texture_uav.resource, None, None, cpu_descriptors[1])

print('SRV/UAV created')

compute_pipeline_state_desc = D3D12_COMPUTE_PIPELINE_STATE_DESC()
compute_pipeline_state_desc.pRootSignature = root_signature
# assigning a blob to a bytecode pointer also sets BytecodeLength
compute_pipeline_state_desc.CS = D3D12_SHADER_BYTECODE(pShaderBytecode=compute_shader)

compute_pipeline_state = device.CreateComputePipelineState(compute_pipeline_state_desc)

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COMPUTE)
command_list = device.CreateCommandList(
    0, D3D12_COMMAND_LIST_TYPE_COMPUTE, allocator, compute_pipeline_state)

texture_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture.resource, SubresourceIndex=0)

texture_uav_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture_uav.resource, SubresourceIndex=0)

upload_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=upload_buffer.resource, PlacedFootprint=footprint)

readback_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=readback_buffer.resource, PlacedFootprint=footprint)

# 1) upload the image. Without barriers each step goes in its own ExecuteCommandLists():
#    at the end of an execution, implicitly promoted resources decay back to the COMMON state
command_list.CopyTextureRegion(
    texture_copy_location, 0, 0, 0, upload_buffer_copy_location, None)
command_list.Close()
queue.ExecuteCommandLists([command_list])
fence.signal_and_wait(queue)

# 2) swap red and blue
allocator.Reset()
command_list.Reset(allocator, compute_pipeline_state)
command_list.SetDescriptorHeaps([descriptor_heap])
command_list.SetComputeRootSignature(root_signature)
command_list.SetComputeRootDescriptorTable(0, gpu_descriptors[0])
command_list.Dispatch((width + 7) // 8, (height + 7) // 8, 1)
command_list.Close()
queue.ExecuteCommandLists([command_list])
fence.signal_and_wait(queue)

# 3) read the result back
allocator.Reset()
command_list.Reset(allocator, compute_pipeline_state)
command_list.CopyTextureRegion(
    readback_buffer_copy_location, 0, 0, 0, texture_uav_copy_location, None)
command_list.Close()
queue.ExecuteCommandLists([command_list])
fence.signal_and_wait(queue)

destination = Image.frombytes('RGBA', (row_pitch // 4, height), readback_buffer.download())
destination.crop((0, 0, width, height)).save('foo.png')

print('done')
