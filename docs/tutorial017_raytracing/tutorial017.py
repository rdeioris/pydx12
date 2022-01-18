import time
from pydx12 import *
from utils import App, get_best_adapter, enable_debug, print_debug, setup_debug, UploadBuffer, Texture, ReadbackBuffer, Barrier, Raytracer, Mesh
from PIL import Image
import gc
import sys
import time
import random
import numpy
import threading
from queue import Queue
from pyrr import matrix44

enable_debug()

device = D3D12CreateDevice(get_best_adapter(), D3D_FEATURE_LEVEL_12_1)

setup_debug(device)

window = Window('pydx12: Tutorial 017 (Raytracing)', 1920, 1080)

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


raytracer = Raytracer(device)

fps = 0

message_queue = Queue()

left, top, right, bottom = window.get_client_rect()
swap_chain_resized = (False, right - left, bottom - top)


def render_loop():
    global swap_chain_resized

    theta = 0
    forward = 0
    fence = device.CreateFence()
    fence_event = Event()
    fence_value = fence.GetCompletedValue()
    fence_value += 1

    frame_counter = 0
    counter = 0
    frequency = QueryPerformanceFrequency()

    now = QueryPerformanceCounter()
    while App.running:
        resize, width, height = swap_chain_resized
        if resize:
            queue.Signal(fence, fence_value)
            if fence.GetCompletedValue() < fence_value:
                fence.SetEventOnCompletion(fence_value, fence_event)
                fence_event.wait()
            fence_value += 1
            back_buffer = None
            swap_chain.ResizeBuffers(0, width, height)
            print(width, height)
            device.CreateRenderTargetView(
                swap_chain.GetBuffer(0), None, rtvs[0])
            device.CreateRenderTargetView(
                swap_chain.GetBuffer(1), None, rtvs[1])
            swap_chain_resized = (False, width, height)

        back_buffer_index = swap_chain.GetCurrentBackBufferIndex()
        back_buffer = swap_chain.GetBuffer(back_buffer_index)

        queue.Signal(fence, fence_value)
        if fence.GetCompletedValue() < fence_value:
            fence.SetEventOnCompletion(fence_value, fence_event)
            fence_event.wait()
        fence_value += 1

        swap_chain.Present(0)
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


def window_proc(win, message, wparam, lparam):
    global swap_chain_resized, swap_chain
    if message in (WM_QUIT, WM_CLOSE):
        App.running = False
    elif message == WM_SIZE:
        width, height = (lparam >> 16), lparam & 0xFFFF
        swap_chain_resized = (True, width, height)
    elif message == WM_KEYUP:
        if wparam == ord('F'):
            win.set_fullscreen(not win.get_fullscreen())
            left, top, right, bottom = win.get_client_rect()
            swap_chain_resized = (True, right-left, bottom - top)
        if wparam == VK_ESCAPE:
            App.running = False


window.set_proc(window_proc)

while App.running:
    window.dequeue()
    if not message_queue.empty():
        new_title = message_queue.get_nowait()
        window.set_title(new_title)

App.running = False
t.join()
