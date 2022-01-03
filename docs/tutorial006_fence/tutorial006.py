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

readback_buffer = ReadbackBuffer(device, bitmap_size)

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_COPY)
queue = device.CreateCommandQueue(command_queue_desc)

fence = device.CreateFence()
fence_event = Event()

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY)
command_list = device.CreateCommandList(
    0, D3D12_COMMAND_LIST_TYPE_COPY, allocator, None)

texture_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture.resource)

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
    fence_event.wait()

destination = Image.frombytes(
    'RGBA', (footprint.Footprint.RowPitch // 4, height), readback_buffer.resource.download())
destination.save('foo.png')