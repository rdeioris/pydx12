"""Tutorial 009: SwapChain

Creates a DXGI flip-model swapchain on a tkinter window and, every frame,
copies a texture (the Python logo, uploaded once) into the back buffer at a
random position before presenting it.

Run: python tutorial009.py [--frames N]
"""
import ctypes
import random

from PIL import Image

from pydx12 import *
from utils import (App, Fence, create_buffer, enable_debug, execute_and_wait, get_best_adapter, parse_args,
                   setup_debug, transition)

args = parse_args(__doc__)

enable_debug()
device = D3D12CreateDevice(get_best_adapter())
info = setup_debug(device)

queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))

# --- upload the logo into a texture -------------------------------------------------
image = Image.open('python-logo.png').convert('RGBA')
width, height = image.size

texture_desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=width, Height=height,
                                   DepthOrArraySize=1, MipLevels=1, Format=DXGI_FORMAT_R8G8B8A8_UNORM)
texture_desc.SampleDesc.Count = 1
texture = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(Type=D3D12_HEAP_TYPE_DEFAULT),
                                         D3D12_HEAP_FLAG_NONE, texture_desc, D3D12_RESOURCE_STATE_COPY_DEST)
texture.SetName('Python Logo')

# textures rows in an upload buffer must be aligned to D3D12_TEXTURE_DATA_PITCH_ALIGNMENT:
# GetCopyableFootprints tells us the exact layout
# (one entry per requested subresource, here just the first one)
footprints, num_rows, row_sizes, total_bytes = device.GetCopyableFootprints(texture_desc, 0, 1, 0)
footprint = footprints[0]
row_pitch = footprint.Footprint.RowPitch
print('footprint', footprint.Footprint, 'rows', num_rows[0], 'row size', row_sizes[0], 'total', total_bytes)

upload = create_buffer(device, total_bytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ)
pixels = image.tobytes()
address = upload.Map(0)
for y in range(height):
    ctypes.memmove(address + y * row_pitch, pixels[y * width * 4:(y + 1) * width * 4], width * 4)
upload.Unmap(0)

texture_location = D3D12_TEXTURE_COPY_LOCATION(Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=texture)
upload_location = D3D12_TEXTURE_COPY_LOCATION(Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT, pResource=upload,
                                              PlacedFootprint=footprint)


def record_upload(command_list):
    command_list.CopyTextureRegion(texture_location, 0, 0, 0, upload_location)
    command_list.ResourceBarrier([transition(texture, D3D12_RESOURCE_STATE_COPY_DEST,
                                             D3D12_RESOURCE_STATE_COPY_SOURCE)])


execute_and_wait(device, queue, record_upload)

# --- the swapchain ---------------------------------------------------------------------
app = App('pydx12: Tutorial 009 (SwapChain)', 1024, 1024)

swap_chain_desc = DXGI_SWAP_CHAIN_DESC1(Width=app.width, Height=app.height, Format=DXGI_FORMAT_R8G8B8A8_UNORM,
                                        BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=2,
                                        Scaling=DXGI_SCALING_STRETCH, SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD)
swap_chain_desc.SampleDesc.Count = 1
# IDXGISwapChain3 adds GetCurrentBackBufferIndex()
swap_chain = IDXGISwapChain3(CreateDXGIFactory2().CreateSwapChainForHwnd(queue, app.hwnd, swap_chain_desc))
back_buffers = [swap_chain.GetBuffer(0), swap_chain.GetBuffer(1)]  # ID3D12Resource by default

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
command_list = device.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
command_list.Close()
fence = Fence(device)

frame = 0
while app.pump() and (not args.frames or frame < args.frames):
    back_buffer = back_buffers[swap_chain.GetCurrentBackBufferIndex()]

    allocator.Reset()
    command_list.Reset(allocator)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_PRESENT,
                                             D3D12_RESOURCE_STATE_COPY_DEST)])
    back_buffer_location = D3D12_TEXTURE_COPY_LOCATION(Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX,
                                                       pResource=back_buffer)
    # the source box keeps the copy inside the back buffer
    x, y = random.randint(0, app.width - 1), random.randint(0, app.height - 1)
    box = D3D12_BOX(right=min(width, swap_chain_desc.Width - x), bottom=min(height, swap_chain_desc.Height - y),
                    back=1)
    command_list.CopyTextureRegion(back_buffer_location, x, y, 0, texture_location, box)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_COPY_DEST,
                                             D3D12_RESOURCE_STATE_PRESENT)])
    command_list.Close()
    queue.ExecuteCommandLists([command_list])

    swap_chain.Present(1, 0)
    fence.flush(queue)  # wait for the GPU before reusing the allocator
    frame += 1

app.destroy()
print('END')
