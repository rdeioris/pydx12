import unittest
import weakref
import sys
from pydx12 import *


class BarrierTests(unittest.TestCase):

    def get_best_adapter(self):
        factory = CreateDXGIFactory2()
        return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[0]

    def test_uav_barrier_com(self):
        device = D3D12CreateDevice(self.get_best_adapter())
        buffer_desc = D3D12_RESOURCE_DESC()
        buffer_desc.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D
        buffer_desc.Width = 64
        buffer_desc.Height = 64
        buffer_desc.DepthOrArraySize = 1
        buffer_desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM
        buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN
        buffer_desc.MipLevels = 1
        buffer_desc.SampleDesc.Count = 1
        buffer_desc.Flags = D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS
        resource = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
            Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_COMMON, None)
        uav_barrier = D3D12_RESOURCE_UAV_BARRIER(pResource=resource)
        self.assertEqual(uav_barrier.pResource, resource)
