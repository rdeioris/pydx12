"""Tutorial 010: Render Target Views

A render target view (RTV) is a descriptor that lets the pipeline write into a
resource. RTVs live in a CPU-only descriptor heap of type RTV: here we create
one for each swapchain back buffer and use it with ClearRenderTargetView to
paint a color cycling background, then copy the logo on top of it.

Run: python tutorial010.py [--frames N]
"""
import colorsys
import random

from pydx12 import *
from utils import App, Fence, enable_debug, get_best_adapter, load_texture, parse_args, setup_debug, transition

args = parse_args(__doc__)

enable_debug()
device = D3D12CreateDevice(get_best_adapter())
info = setup_debug(device)
queue = device.CreateCommandQueue(D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_DIRECT))

logo, logo_width, logo_height = load_texture(device, queue, 'python-logo.png')
logo_location = D3D12_TEXTURE_COPY_LOCATION(Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=logo)

app = App('pydx12: Tutorial 010 (RTV)', 1024, 1024)
swap_chain_desc = DXGI_SWAP_CHAIN_DESC1(Width=app.width, Height=app.height, Format=DXGI_FORMAT_R8G8B8A8_UNORM,
                                        BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=2,
                                        Scaling=DXGI_SCALING_STRETCH, SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD)
swap_chain_desc.SampleDesc.Count = 1
swap_chain = IDXGISwapChain3(CreateDXGIFactory2().CreateSwapChainForHwnd(queue, app.hwnd, swap_chain_desc))
back_buffers = [swap_chain.GetBuffer(0), swap_chain.GetBuffer(1)]

# --- the RTV descriptor heap --------------------------------------------------------
rtv_heap = device.CreateDescriptorHeap(D3D12_DESCRIPTOR_HEAP_DESC(Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV,
                                                                  NumDescriptors=2))
# a CPU descriptor handle is just an address: slot N is start + N * increment size
heap_start = rtv_heap.GetCPUDescriptorHandleForHeapStart()
increment = device.GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV)
rtvs = [D3D12_CPU_DESCRIPTOR_HANDLE(heap_start.ptr + i * increment) for i in range(2)]
for back_buffer, rtv in zip(back_buffers, rtvs):
    device.CreateRenderTargetView(back_buffer, None, rtv)  # None: view the whole resource with its format

allocator = device.CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT)
command_list = device.CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
command_list.Close()
fence = Fence(device)

frame = 0
while app.pump() and (not args.frames or frame < args.frames):
    index = swap_chain.GetCurrentBackBufferIndex()
    back_buffer = back_buffers[index]

    allocator.Reset()
    command_list.Reset(allocator)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_PRESENT,
                                             D3D12_RESOURCE_STATE_RENDER_TARGET)])
    color = colorsys.hsv_to_rgb((frame % 360) / 360, 0.6, 0.8) + (1,)
    command_list.ClearRenderTargetView(rtvs[index], color)

    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_RENDER_TARGET,
                                             D3D12_RESOURCE_STATE_COPY_DEST)])
    x = random.randint(0, swap_chain_desc.Width - logo_width)
    y = random.randint(0, swap_chain_desc.Height - logo_height)
    command_list.CopyTextureRegion(
        D3D12_TEXTURE_COPY_LOCATION(Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX, pResource=back_buffer),
        x, y, 0, logo_location)
    command_list.ResourceBarrier([transition(back_buffer, D3D12_RESOURCE_STATE_COPY_DEST,
                                             D3D12_RESOURCE_STATE_PRESENT)])
    command_list.Close()
    queue.ExecuteCommandLists([command_list])

    swap_chain.Present(1, 0)
    fence.flush(queue)
    frame += 1

app.destroy()
print('END')
