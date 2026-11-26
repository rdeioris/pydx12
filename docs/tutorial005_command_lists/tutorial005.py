import time

from PIL import Image

from pydx12 import *
from utils import (get_best_adapter, enable_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer,
                   get_footprint, pad_rows)

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

info = setup_debug(device)

image = Image.open('python-logo.png').convert('RGBA')
width, height = image.size
print(width, height)
texture = Texture(device, width, height)

# textures have an opaque GPU layout: GetCopyableFootprints tells how a subresource
# must be laid out in a buffer to be copied from/to it (rows are 256 bytes aligned)
footprint, num_rows, row_size_in_bytes, total_bytes = get_footprint(device, texture.resource)
print(footprint.Footprint.to_dict(), num_rows, row_size_in_bytes, total_bytes)

row_pitch = footprint.Footprint.RowPitch
# the last row is not padded (total_bytes is smaller), but a full grid of rows is easier to read back
bitmap_size = row_pitch * num_rows
fixed_bytes = pad_rows(image.tobytes(), width * 4, row_pitch, num_rows)
print(len(fixed_bytes))

upload_buffer = UploadBuffer(device, bitmap_size)
upload_buffer.upload(fixed_bytes)

readback_buffer = ReadbackBuffer(device, bitmap_size)

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_COPY)
queue = device.CreateCommandQueue(command_queue_desc)

# commands are recorded in a command list, whose memory comes from a command allocator
allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY)
command_list = device.CreateCommandList(
    0, D3D12_COMMAND_LIST_TYPE_COPY, allocator, None)

texture_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture.resource, SubresourceIndex=0)

upload_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=upload_buffer.resource, PlacedFootprint=footprint)

readback_buffer_copy_location = D3D12_TEXTURE_COPY_LOCATION(
    Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=readback_buffer.resource, PlacedFootprint=footprint)

# upload buffer -> texture -> readback buffer
command_list.CopyTextureRegion(
    texture_copy_location, 0, 0, 0, upload_buffer_copy_location, None)
command_list.CopyTextureRegion(
    readback_buffer_copy_location, 0, 0, 0, texture_copy_location, None)
command_list.Close()

queue.ExecuteCommandLists([command_list])

# the GPU works asynchronously: here we just wait "long enough" (the next tutorial does it properly)
time.sleep(1)

destination = Image.frombytes('RGBA', (row_pitch // 4, height), readback_buffer.download())
destination.crop((0, 0, width, height)).save('foo.png')
print('saved foo.png')
