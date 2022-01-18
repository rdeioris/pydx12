import time
from pydx12 import *
from utils import get_best_adapter, enable_debug, print_debug, setup_debug, Barrier, Rasterizer, Mesh, GLTF, ResourceBuffer
from PIL import Image
import gc
import sys
import time
import random
import numpy
import threading
from queue import Queue
from pyrr import matrix44
import struct
import math

enable_debug()

device = D3D12CreateDevice(get_best_adapter())

print(device)

setup_debug(device)

print('DEBUG SET')

window = Window('pydx12: Tutorial 015 (Tessellation)', 1024, 1024)

print(window)

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

mesh = Mesh(device)
mesh.set_index_buffer(bytearray(numpy.array(
    [
        0, 1, 2, 3
    ], dtype=numpy.uint16)))
mesh.set_vertex_buffer(bytearray(numpy.array(
    [
        0, 0, 0,
        0, 0, math.pi/2,
        0, 0, math.pi,
        0, 0, math.pi * 1.5
    ], dtype=numpy.float32)))
mesh.set_nvertices(4)
rasterizer = Rasterizer(device)

running = True
fps = 0

message_queue = Queue()

tessellation_config = ResourceBuffer(
    device, struct.pack('I', 1))  # default to 1

def render_loop():
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
    while running:
        theta += 0.05
        forward = -2  # 10.01
        scale = matrix44.create_from_scale((1, 1, 1), dtype='float32')
        rotation = matrix44.create_from_y_rotation(theta, dtype='float32')
        translation = matrix44.create_from_translation(
            (0, 0, forward), dtype='float32')
        perspective = matrix44.create_perspective_projection(
            60., 1., 0.1, 1000., dtype='float32')
        #mesh.matrix = scale @ rotation @ translation @ perspective
        mesh.matrix = scale @ rotation @ translation @ perspective

        back_buffer_index = swap_chain.GetCurrentBackBufferIndex()
        back_buffer = swap_chain.GetBuffer(back_buffer_index)

        rasterizer.execute(queue, back_buffer,
                           rtvs[back_buffer_index], [mesh], tessellation_config)

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

while running:
    for message, wparam, lparam in window.dequeue():
        if message in (WM_QUIT, WM_CLOSE):
            running = False
        elif message == WM_KEYUP:
            if ord('1') <= wparam <= ord('9'):
                tessellation_config.resource.upload(struct.pack('I', wparam - ord('0')))
    if not message_queue.empty():
        new_title = message_queue.get_nowait()
        window.set_title(new_title)

running = False
t.join()

print('END')
