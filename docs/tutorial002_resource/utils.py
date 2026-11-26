import ctypes

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
        # Map() returns the CPU address of the (write-combined) upload memory
        address = self.resource.Map(0, D3D12_RANGE(0, 0))  # we are not going to read it
        ctypes.memmove(address, data, min(len(data), self.size))
        self.resource.Unmap(0)
