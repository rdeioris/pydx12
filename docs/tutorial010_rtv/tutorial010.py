import time
from pydx12 import *
from utils import get_best_adapter, enable_debug, print_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer, Barrier
from PIL import Image
import gc
import sys
import time
import random

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

setup_debug(device)

image = Image.open('python-logo.png')
width, height = image.size
print(width, height)
texture = Texture(device, width, height, name='Python Logo')
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

command_list.ResourceBarrier([Barrier(
    texture.resource, D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_COPY_SOURCE).barrier_desc])
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

descriptor_heap_desc = D3D12_DESCRIPTOR_HEAP_DESC(
    Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV,
    NumDescriptors=2)
descriptor_heap = device.CreateDescriptorHeap(descriptor_heap_desc)
rtvs = descriptor_heap.cpu((0, 1))

device.CreateRenderTargetView(swap_chain.GetBuffer(0), None, rtvs[0])
device.CreateRenderTargetView(swap_chain.GetBuffer(1), None, rtvs[1])

running = True
fps = 0
counter = 0
frequency = QueryPerformanceFrequency()

now = QueryPerformanceCounter()

while not window.is_closed():
    window.dequeue()

    back_buffer_index = swap_chain.GetCurrentBackBufferIndex()
    back_buffer = swap_chain.GetBuffer(back_buffer_index)

    command_list.Reset(allocator)

    command_list.ResourceBarrier([Barrier(
        back_buffer, D3D12_RESOURCE_STATE_PRESENT, D3D12_RESOURCE_STATE_RENDER_TARGET).barrier_desc])

    command_list.ClearRenderTargetView(rtvs[back_buffer_index], (1, 0, 0, 1))

    back_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
        Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=back_buffer)

    command_list.ResourceBarrier([Barrier(
        back_buffer, D3D12_RESOURCE_STATE_RENDER_TARGET, D3D12_RESOURCE_STATE_COPY_DEST).barrier_desc])

    command_list.CopyTextureRegion(
        back_buffer_copy_location, random.randint(0, 512), random.randint(0, 512), 0, texture_copy_location, None)

    command_list.ResourceBarrier([Barrier(
        back_buffer, D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_PRESENT).barrier_desc])

    command_list.Close()

    queue.ExecuteCommandLists([command_list])
    queue.Signal(fence, fence_value)
    if fence.GetCompletedValue() < fence_value:
        fence.SetEventOnCompletion(fence_value, fence_event)
        fence_event.wait()
    fence_value += 1

    swap_chain.Present(1)
    new_now = QueryPerformanceCounter()
    counter += new_now - now
    now = new_now
    if counter >= frequency:
        window.set_title(str(fps))
        counter -= frequency
        fps = 1
    else:
        fps += 1

print('END')
