import atexit
import ctypes
import sys

from pydx12 import *


def enum_adapters(factory):
    adapters = []
    index = 0
    while True:
        try:
            adapters.append(factory.EnumAdapters1(index))
        except DXError as e:
            if e.hresult != DXGI_ERROR_NOT_FOUND:
                raise
            return adapters
        index += 1


def get_best_adapter():
    return max(enum_adapters(CreateDXGIFactory2()), key=lambda a: a.GetDesc1().DedicatedVideoMemory)


def enable_debug():
    D3D12GetDebugInterface().EnableDebugLayer()


def print_debug(info):
    for index in range(info.GetNumStoredMessages()):
        # two calls: the first one returns the size of the message, the second one fills it
        size = ctypes.c_size_t()
        info.GetMessage(index, None, ctypes.byref(size))
        message = ctypes.cast(ctypes.create_string_buffer(size.value), ctypes.POINTER(D3D12_MESSAGE))
        info.GetMessage(index, message, ctypes.byref(size))
        print(message[0].pDescription)


def setup_debug(device):
    info = ID3D12InfoQueue(device)

    def d3d12_debug_hook(*exc):
        print_debug(info)
        sys.__excepthook__(*exc)

    def d3d12_debug_exit_hook():
        print_debug(info)

    sys.excepthook = d3d12_debug_hook
    atexit.register(d3d12_debug_exit_hook)
    return info


def buffer_desc(size):
    desc = D3D12_RESOURCE_DESC()
    desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
    desc.Width = size
    desc.Height = 1
    desc.DepthOrArraySize = 1
    desc.Format = DXGI_FORMAT_UNKNOWN
    desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
    desc.MipLevels = 1
    desc.SampleDesc.Count = 1
    return desc


class UploadBuffer:

    def __init__(self, device, size):
        self.size = size
        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, buffer_desc(size), D3D12_RESOURCE_STATE_GENERIC_READ)

    def upload(self, data):
        data = bytes(data)
        address = self.resource.Map(0, D3D12_RANGE(0, 0))  # we are not going to read it
        ctypes.memmove(address, data, min(len(data), self.size))
        self.resource.Unmap(0)


class ReadbackBuffer:

    def __init__(self, device, size):
        self.size = size
        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_READBACK), D3D12_HEAP_FLAG_NONE, buffer_desc(size), D3D12_RESOURCE_STATE_COPY_DEST)

    def download(self):
        address = self.resource.Map(0, D3D12_RANGE(0, self.size))
        data = ctypes.string_at(address, self.size)
        self.resource.Unmap(0, D3D12_RANGE(0, 0))  # we did not write anything
        return data


class Texture:

    def __init__(self, device, width, height, flags=D3D12_RESOURCE_FLAG_NONE, state=D3D12_RESOURCE_STATE_COMMON):
        desc = D3D12_RESOURCE_DESC()
        desc.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D
        desc.Width = width
        desc.Height = height
        desc.DepthOrArraySize = 1
        desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM
        desc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN
        desc.MipLevels = 1
        desc.SampleDesc.Count = 1
        desc.Flags = flags
        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, desc, state)


def get_footprint(device, resource):
    """Layout of the first subresource of ``resource`` when stored in a buffer."""
    # returns one entry per requested subresource, plus the total size in bytes
    footprints, num_rows, row_sizes, total_bytes = device.GetCopyableFootprints(resource.GetDesc(), 0, 1, 0)
    return footprints[0], num_rows[0], row_sizes[0], total_bytes


def pad_rows(data, row_size, row_pitch, num_rows):
    """Copy tightly packed rows into a buffer whose rows are row_pitch (256 bytes aligned) apart."""
    padded = bytearray(row_pitch * num_rows)
    for y in range(num_rows):
        padded[row_pitch * y:row_pitch * y + row_size] = data[row_size * y:row_size * (y + 1)]
    return padded


kernel32 = ctypes.WinDLL('kernel32')
kernel32.CreateEventW.restype = ctypes.c_void_p
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p]
kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
INFINITE = 0xFFFFFFFF


class Fence:
    """A fence plus a Win32 event (from kernel32 via ctypes) to wait on it."""

    def __init__(self, device):
        self.fence = device.CreateFence(0, D3D12_FENCE_FLAG_NONE)
        self.value = 0
        self.event = kernel32.CreateEventW(None, False, False, None)

    def signal_and_wait(self, queue):
        self.value += 1
        queue.Signal(self.fence, self.value)
        if self.fence.GetCompletedValue() < self.value:
            self.fence.SetEventOnCompletion(self.value, self.event)
            kernel32.WaitForSingleObject(self.event, INFINITE)


def transition(resource, before, after):
    barrier = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    barrier.Transition.pResource = resource
    barrier.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES
    barrier.Transition.StateBefore = before
    barrier.Transition.StateAfter = after
    return barrier
