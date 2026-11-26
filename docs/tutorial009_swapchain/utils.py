"""Helpers shared by the windowed tutorials (009-017).

Everything here is plain tutorial code written against the raw pydx12 API:
pydx12 itself only exposes DirectX, so windows come from tkinter, timing
from time.perf_counter and so on.
"""
import argparse
import atexit
import ctypes
import time
import tkinter

import numpy

from pydx12 import *

FRAME_COUNT = 2  # swapchain back buffers


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--frames', type=int, default=0,
                        help='exit after N frames (default: run until the window is closed)')
    return parser.parse_args()


# ---------------------------------------------------------------------------
# device and debug layer
# ---------------------------------------------------------------------------

def enable_debug():
    D3D12GetDebugInterface().EnableDebugLayer()


def get_best_adapter():
    return CreateDXGIFactory2().EnumAdapterByGpuPreference(0, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)


def get_messages(info):
    """Yield (severity, text) for every message stored in an ID3D12InfoQueue."""
    for index in range(info.GetNumStoredMessages()):
        size = ctypes.c_size_t()
        info.GetMessage(index, None, ctypes.byref(size))  # first call: size of the message
        buf = ctypes.create_string_buffer(size.value)
        message = ctypes.cast(buf, ctypes.POINTER(D3D12_MESSAGE))
        info.GetMessage(index, message, ctypes.byref(size))
        yield message.contents.Severity, message.contents.pDescription


def count_errors(info):
    return sum(1 for severity, _ in get_messages(info) if severity <= D3D12_MESSAGE_SEVERITY_ERROR)


def setup_debug(device):
    """Print the debug layer messages at exit; returns the ID3D12InfoQueue."""
    info = ID3D12InfoQueue(device)

    def dump():
        for severity, text in get_messages(info):
            print('[D3D12]', text)
        print('debug layer errors:', count_errors(info))
    atexit.register(dump)
    return info


# ---------------------------------------------------------------------------
# resources
# ---------------------------------------------------------------------------

def buffer_desc(size, flags=D3D12_RESOURCE_FLAG_NONE):
    desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                               DepthOrArraySize=1, MipLevels=1, Format=DXGI_FORMAT_UNKNOWN,
                               Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR, Flags=flags)
    desc.SampleDesc.Count = 1
    return desc


def create_buffer(device, size, heap_type, state, flags=D3D12_RESOURCE_FLAG_NONE):
    return device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(Type=heap_type), D3D12_HEAP_FLAG_NONE,
                                          buffer_desc(size, flags), state)


def write_resource(resource, data, offset=0):
    """Copy bytes (or any buffer: numpy arrays, ctypes objects...) into a mappable resource."""
    view = memoryview(data).cast('B')
    address = resource.Map(0, D3D12_RANGE(0, 0))  # we won't read from it
    ctypes.memmove(address + offset, (ctypes.c_ubyte * len(view)).from_buffer_copy(view), len(view))
    resource.Unmap(0)


def read_resource(resource, size):
    address = resource.Map(0, D3D12_RANGE(0, size))
    data = ctypes.string_at(address, size)
    resource.Unmap(0, D3D12_RANGE(0, 0))
    return data


def upload_buffer(device, data):
    """An upload-heap buffer filled with data (fine for small/dynamic data)."""
    size = memoryview(data).nbytes
    resource = create_buffer(device, size, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ)
    write_resource(resource, data)
    return resource


def transition(resource, before, after):
    barrier = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    barrier.Transition = D3D12_RESOURCE_TRANSITION_BARRIER(
        pResource=resource, StateBefore=before, StateAfter=after,
        Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
    return barrier


def uav_barrier(resource):
    barrier = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_UAV)
    barrier.UAV.pResource = resource
    return barrier


def cpu_handles(device, heap, heap_type, count):
    """CPU descriptor handles for the first `count` slots of a descriptor heap."""
    start = heap.GetCPUDescriptorHandleForHeapStart().ptr
    step = device.GetDescriptorHandleIncrementSize(heap_type)
    return [D3D12_CPU_DESCRIPTOR_HANDLE(start + i * step) for i in range(count)]


class Fence:
    """A fence plus a counter: signal() and wait until the GPU caught up."""

    def __init__(self, device):
        self.fence = device.CreateFence(0)
        self.value = 0

    def flush(self, queue):
        self.value += 1
        queue.Signal(self.fence, self.value)
        if self.fence.GetCompletedValue() < self.value:
            self.fence.SetEventOnCompletion(self.value, None)  # NULL event: blocks until reached


def execute_and_wait(device, queue, record, list_type=D3D12_COMMAND_LIST_TYPE_DIRECT):
    """Record a one-shot command list with record(command_list), run it and wait."""
    allocator = device.CreateCommandAllocator(list_type)
    command_list = device.CreateCommandList(0, list_type, allocator)
    record(command_list)
    command_list.Close()
    queue.ExecuteCommandLists([command_list])
    Fence(device).flush(queue)


def default_buffer(device, queue, data, final_state):
    """A default-heap (GPU only) buffer initialized through a temporary upload buffer."""
    size = memoryview(data).nbytes
    staging = upload_buffer(device, data)
    resource = create_buffer(device, size, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON)

    def record(command_list):
        command_list.CopyResource(resource, staging)
        command_list.ResourceBarrier([transition(resource, D3D12_RESOURCE_STATE_COPY_DEST, final_state)])
    execute_and_wait(device, queue, record)
    return resource


# ---------------------------------------------------------------------------
# window and swapchain
# ---------------------------------------------------------------------------

class App:
    """A tkinter window whose client area hosts a DXGI swapchain."""

    def __init__(self, title, width, height):
        self.title = title
        self.root = tkinter.Tk()
        self.root.title(title)
        self.frame = tkinter.Frame(self.root, width=width, height=height, bg='')
        self.frame.pack(fill=tkinter.BOTH, expand=True)
        self.root.update()
        self.hwnd = self.frame.winfo_id()
        self.width, self.height = width, height
        self.resized = False
        self.running = True
        self.fullscreen = False
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.frame.bind('<Configure>', self._on_configure)
        self.root.bind('<Escape>', lambda e: self.close())
        self._frames = 0
        self._last = time.perf_counter()

    def _on_configure(self, event):
        if event.width > 0 and event.height > 0 and (event.width, event.height) != (self.width, self.height):
            self.width, self.height = event.width, event.height
            self.resized = True

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)

    def close(self):
        self.running = False

    def pump(self):
        """Process window events; returns False once the window has been closed."""
        self.root.update()
        self._frames += 1
        now = time.perf_counter()
        if now - self._last >= 1:
            self.fps = self._frames / (now - self._last)
            self.root.title('%s - %.0f fps' % (self.title, self.fps))
            self._frames, self._last = 0, now
        return self.running

    def destroy(self):
        self.root.destroy()


class SwapChain:
    """Flip-model swapchain + one RTV per back buffer."""

    def __init__(self, device, queue, app, format=DXGI_FORMAT_R8G8B8A8_UNORM):
        self.device = device
        self.queue = queue
        self.format = format
        desc = DXGI_SWAP_CHAIN_DESC1(Width=app.width, Height=app.height, Format=format,
                                     BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=FRAME_COUNT,
                                     Scaling=DXGI_SCALING_STRETCH, SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD)
        desc.SampleDesc.Count = 1
        self.swapchain = IDXGISwapChain3(CreateDXGIFactory2().CreateSwapChainForHwnd(queue, app.hwnd, desc))
        self.rtv_heap = device.CreateDescriptorHeap(D3D12_DESCRIPTOR_HEAP_DESC(
            Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV, NumDescriptors=FRAME_COUNT))
        self.rtvs = cpu_handles(device, self.rtv_heap, D3D12_DESCRIPTOR_HEAP_TYPE_RTV, FRAME_COUNT)
        self.fence = Fence(device)
        self.width, self.height = app.width, app.height
        self._create_views()

    def _create_views(self):
        self.buffers = [self.swapchain.GetBuffer(i) for i in range(FRAME_COUNT)]
        for buffer, rtv in zip(self.buffers, self.rtvs):
            self.device.CreateRenderTargetView(buffer, None, rtv)

    def resize(self, width, height):
        self.fence.flush(self.queue)  # the GPU must not use the old buffers anymore
        self.buffers = []  # release every reference before ResizeBuffers
        self.swapchain.ResizeBuffers(FRAME_COUNT, width, height)
        self.width, self.height = width, height
        self._create_views()

    def current(self):
        """(back buffer resource, its RTV) for this frame.

        The returned wrapper does not hold a COM reference (addref=False and not owned):
        ResizeBuffers() fails while anybody still references the old buffers, and a
        `back_buffer` variable surviving from the previous frame would be enough.
        """
        index = self.swapchain.GetCurrentBackBufferIndex()
        return ID3D12Resource.from_address(self.buffers[index].value, addref=False), self.rtvs[index]

    def present(self, sync_interval=1):
        self.swapchain.Present(sync_interval, 0)
        self.fence.flush(self.queue)  # keep it simple: one frame in flight
