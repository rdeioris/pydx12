import time
from pydx12 import *
from utils import get_best_adapter, enable_debug, print_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer, Barrier, VertexBuffer, Rasterizer
from PIL import Image
import gc
import sys
import time
import random
import numpy
import threading
from queue import Queue

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

setup_debug(device)

window = Window('pydx12: Tutorial 011 (SwapChain)', 1024, 1024)

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(
    Type=D3D12_COMMAND_LIST_TYPE_DIRECT)
queue = device.CreateCommandQueue(command_queue_desc)

swap_chain_desc1 = DXGI_SWAP_CHAIN_DESC1(Format=DXGI_FORMAT_R8G8B8A8_UNORM, BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT,
                                         BufferCount=2, Scaling=DXGI_SCALING_STRETCH, SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD)
swap_chain_desc1.SampleDesc.Count = 1
swap_chain = CreateDXGIFactory2().CreateSwapChainForHwnd(
    queue, window, swap_chain_desc1)

descriptor_heap_desc = D3D12_DESCRIPTOR_HEAP_DESC(
    Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV,
    NumDescriptors=2)
descriptor_heap = device.CreateDescriptorHeap(descriptor_heap_desc)
rtvs = descriptor_heap.cpu((0, 1))

device.CreateRenderTargetView(swap_chain.GetBuffer(0), None, rtvs[0])
device.CreateRenderTargetView(swap_chain.GetBuffer(1), None, rtvs[1])

vertex_buffer = VertexBuffer(device, numpy.array(
    [0, 1, -1, -1, 1, -1], dtype=numpy.float32), 3)

print(vertex_buffer)

rasterizer = Rasterizer(device)

running = True
fps = 0

message_queue = Queue()

def render_loop():
    fence = device.CreateFence()
    fence_event = Event()
    fence_value = fence.GetCompletedValue()
    fence_value += 1

    frame_counter = 0
    counter = 0
    frequency = QueryPerformanceFrequency()

    now = QueryPerformanceCounter()
    while running:
        back_buffer_index = swap_chain.GetCurrentBackBufferIndex()
        back_buffer = swap_chain.GetBuffer(back_buffer_index)

        rasterizer.execute(queue, back_buffer,
                           rtvs[back_buffer_index], [vertex_buffer])

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
            counter -= frequency
            fps = frame_counter
            message_queue.put(str(fps))
            frame_counter = 1
        else:
            frame_counter += 1


t = threading.Thread(target=render_loop)
t.start()

while not window.is_closed():
    window.dequeue()
    if not message_queue.empty():
        new_title = message_queue.get_nowait()
        window.set_title(new_title)

running = False
t.join()

print('END')
