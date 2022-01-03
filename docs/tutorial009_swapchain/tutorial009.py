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

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_DIRECT)
queue = device.CreateCommandQueue(command_queue_desc)

fence = device.CreateFence()
fence_event = Event()
fence_value = fence.GetCompletedValue()

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
print(allocator)
command_list = device.CreateCommandList(
    0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
print(command_list)

texture_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture.resource)
upload_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=upload_buffer.resource, PlacedFootprint=footprint)
command_list.CopyTextureRegion(
    texture_copy_location, 0, 0, 0, upload_buffer_copy_location, None)
command_list.Close()

queue.ExecuteCommandLists([command_list])
queue.Signal(fence, fence_value)
if fence.GetCompletedValue() < fence_value:
    fence.SetEventOnCompletion(fence_value, fence_event)
    fence_event.wait()
    fence_value += 1

window = Window('pydx12: Tutorial 009 (SwapChain)', 1024, 1024)

swap_chain_desc1 = DXGI_SWAP_CHAIN_DESC1(Format=DXGI_FORMAT_R8G8B8A8_UNORM, BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT,
                                         BufferCount=2, Scaling=DXGI_SCALING_STRETCH, SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD)
swap_chain_desc1.SampleDesc.Count = 1
swap_chain = CreateDXGIFactory2().CreateSwapChainForHwnd(
    queue, window, swap_chain_desc1)

print(swap_chain)


print('ok')

while True:
    while window.dequeue():
        pass
    back_buffer_index = swap_chain.GetCurrentBackBufferIndex()
    back_buffer = swap_chain.GetBuffer(back_buffer_index)

    print('back buffer', back_buffer_index, back_buffer)

    command_list.Reset(allocator)

    back_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
        Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=back_buffer)

    print('done release')

    barrier000 = D3D12_RESOURCE_BARRIER(
        Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    barrier000.Transition.pResource = texture.resource
    barrier000.Transition.StateBefore = D3D12_RESOURCE_STATE_COPY_DEST
    barrier000.Transition.StateAfter = D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE
    command_list.ResourceBarrier([barrier000])

    command_list.CopyTextureRegion(
        back_buffer_copy_location, 0, 0, 0, texture_copy_location, None)

    barrier001 = D3D12_RESOURCE_BARRIER(
        Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    barrier001.Transition.pResource = texture.resource
    barrier001.Transition.StateBefore = D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE
    barrier001.Transition.StateAfter = D3D12_RESOURCE_STATE_COPY_SOURCE
    command_list.ResourceBarrier([barrier001])

    command_list.Close()

    queue.ExecuteCommandLists([command_list])
    queue.Signal(fence, fence_value)
    if fence.GetCompletedValue() < fence_value:
        fence.SetEventOnCompletion(fence_value, fence_event)
        fence_event.wait()
        fence_value += 1

    swap_chain.Present(1)
