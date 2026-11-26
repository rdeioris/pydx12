from PIL import Image

from pydx12 import *
from utils import (get_best_adapter, enable_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer,
                   get_footprint, pad_rows, kernel32, INFINITE)

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

setup_debug(device)

image = Image.open('python-logo.png').convert('RGBA')
width, height = image.size
print(width, height)
texture = Texture(device, width, height)
footprint, num_rows, row_size_in_bytes, total_bytes = get_footprint(device, texture.resource)
print(footprint.Footprint.to_dict(), num_rows, row_size_in_bytes, total_bytes)

row_pitch = footprint.Footprint.RowPitch
# the last row is not padded (total_bytes is smaller), but a full grid of rows is easier to read back
bitmap_size = row_pitch * num_rows
upload_buffer = UploadBuffer(device, bitmap_size)
upload_buffer.upload(pad_rows(image.tobytes(), width * 4, row_pitch, num_rows))

readback_buffer = ReadbackBuffer(device, bitmap_size)

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_COPY)
queue = device.CreateCommandQueue(command_queue_desc)

# a fence is a 64 bit counter the GPU sets (via queue.Signal) when it reaches that point of the queue;
# the CPU can wait for a value through a Win32 event (created with ctypes, no wrapper needed)
fence = device.CreateFence(0, D3D12_FENCE_FLAG_NONE)
fence_event = kernel32.CreateEventW(None, False, False, None)

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY)
command_list = device.CreateCommandList(
    0, D3D12_COMMAND_LIST_TYPE_COPY, allocator, None)

texture_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture.resource, SubresourceIndex=0)

upload_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=upload_buffer.resource, PlacedFootprint=footprint)

readback_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=readback_buffer.resource, PlacedFootprint=footprint)

command_list.CopyTextureRegion(
    texture_copy_location, 0, 0, 0, upload_buffer_copy_location, None)
command_list.CopyTextureRegion(
    readback_buffer_copy_location, 0, 0, 0, texture_copy_location, None)
command_list.Close()

queue.ExecuteCommandLists([command_list])
queue.Signal(fence, 1)
if fence.GetCompletedValue() < 1:
    fence.SetEventOnCompletion(1, fence_event)
    kernel32.WaitForSingleObject(fence_event, INFINITE)
# (passing None instead of an event makes SetEventOnCompletion itself block until completion)

destination = Image.frombytes('RGBA', (row_pitch // 4, height), readback_buffer.download())
destination.crop((0, 0, width, height)).save('foo.png')
print('saved foo.png')
