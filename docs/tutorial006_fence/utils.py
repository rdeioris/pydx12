from pydx12 import *
import sys
import atexit


def enable_debug():
    D3D12GetDebugInterface().EnableDebugLayer()


def get_best_adapter():
    factory = CreateDXGIFactory2()
    return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[0]


def print_debug(info):
    for index in range(0, info.GetNumStoredMessages()):
        print(info.GetMessage(index).pDescription)


def setup_debug(device):
    info = ID3D12InfoQueue(device)

    def d3d12_debug_hook(*exc):
        print_debug(info)
        print(exc)

    def d3d12_debug_exit_hook():
        print_debug(info)

    sys.excepthook = d3d12_debug_hook
    atexit.register(d3d12_debug_exit_hook)


class UploadBuffer:

    def __init__(self, device, size):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        buffer_desc.Width = size
        buffer_desc.Height = 1
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_UNKNOWN
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_GENERIC_READ, None)

    def upload(self, data):
        self.resource.upload(data)


class Texture:

    def __init__(self, device, width, height):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D
        buffer_desc.Width = width
        buffer_desc.Height = height
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_COMMON, None)


class ReadbackBuffer:

    def __init__(self, device, size):
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        buffer_desc.Width = size
        buffer_desc.Height = 1
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_UNKNOWN
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1

        self.resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_READBACK), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_COPY_DEST, None)
