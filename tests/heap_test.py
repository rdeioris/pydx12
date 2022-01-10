import unittest
import weakref
import sys
from pydx12 import *


class HeapTests(unittest.TestCase):

    def get_best_adapter(self):
        factory = CreateDXGIFactory2()
        return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[0]

    def test_heap_64k(self):
        device = D3D12CreateDevice(self.get_best_adapter())
        heap_desc = D3D12_HEAP_DESC(SizeInBytes=64 * 1024)
        heap_desc.Properties.Type = D3D12_HEAP_TYPE_READBACK
        heap = device.CreateHeap(heap_desc)
        self.assertIsInstance(heap, ID3D12Heap)

    def test_heap_128k(self):
        device = D3D12CreateDevice(self.get_best_adapter())
        heap_desc = D3D12_HEAP_DESC(SizeInBytes=128 * 1024)
        heap_desc.Properties.Type = D3D12_HEAP_TYPE_READBACK
        heap = device.CreateHeap(heap_desc)
        self.assertIsInstance(heap, ID3D12Heap)

    def test_placed_resource(self):
        device = D3D12CreateDevice(self.get_best_adapter())
        heap_desc = D3D12_HEAP_DESC(SizeInBytes=128)
        heap_desc.Properties.Type = D3D12_HEAP_TYPE_READBACK
        heap = device.CreateHeap(heap_desc)
        self.assertIsInstance(heap, ID3D12Heap)
        resource_desc = D3D12_RESOURCE_DESC()
        resource_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        resource_desc.Format = DXGI_FORMAT_UNKNOWN
        resource_desc.Width = 64
        resource_desc.Height = 1
        resource_desc.MipLevels = 1
        resource_desc.SampleDesc.Count = 1
        resource_desc.DepthOrArraySize = 1
        resource_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        resource = device.CreatePlacedResource(
            heap, 0, resource_desc, D3D12_RESOURCE_STATE_COPY_DEST)
        self.assertIsInstance(resource, ID3D12Resource)
        resource.upload(b'Hello')
        self.assertEqual(resource.download()[0:5], b'Hello')

    def test_placed_resource_overlap(self):
        device = D3D12CreateDevice(self.get_best_adapter())
        heap_desc = D3D12_HEAP_DESC(SizeInBytes=128)
        heap_desc.Properties.Type = D3D12_HEAP_TYPE_READBACK
        heap = device.CreateHeap(heap_desc)
        self.assertIsInstance(heap, ID3D12Heap)
        resource_desc = D3D12_RESOURCE_DESC()
        resource_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        resource_desc.Format = DXGI_FORMAT_UNKNOWN
        resource_desc.Width = 64
        resource_desc.Height = 1
        resource_desc.MipLevels = 1
        resource_desc.SampleDesc.Count = 1
        resource_desc.DepthOrArraySize = 1
        resource_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        resource = device.CreatePlacedResource(
            heap, 0, resource_desc, D3D12_RESOURCE_STATE_COPY_DEST)
        self.assertIsInstance(resource, ID3D12Resource)
        resource2 = device.CreatePlacedResource(
            heap, 0, resource_desc, D3D12_RESOURCE_STATE_COPY_DEST)
        self.assertIsInstance(resource2, ID3D12Resource)
        resource2.upload(b'Hello')
        self.assertEqual(resource.download()[0:5], b'Hello')

    def test_placed_resource_overlap_offset(self):
        device = D3D12CreateDevice(self.get_best_adapter())
        heap_desc = D3D12_HEAP_DESC(SizeInBytes=128 * 1024)
        heap_desc.Properties.Type = D3D12_HEAP_TYPE_READBACK
        heap = device.CreateHeap(heap_desc)
        self.assertIsInstance(heap, ID3D12Heap)
        resource_desc = D3D12_RESOURCE_DESC()
        resource_desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER
        resource_desc.Format = DXGI_FORMAT_UNKNOWN
        resource_desc.Width = 64
        resource_desc.Height = 1
        resource_desc.MipLevels = 1
        resource_desc.SampleDesc.Count = 1
        resource_desc.DepthOrArraySize = 1
        resource_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
        resource = device.CreatePlacedResource(
            heap, 64 * 1024, resource_desc, D3D12_RESOURCE_STATE_COPY_DEST)
        self.assertIsInstance(resource, ID3D12Resource)
        resource2 = device.CreatePlacedResource(
            heap, 64 * 1024, resource_desc, D3D12_RESOURCE_STATE_COPY_DEST)
        self.assertIsInstance(resource2, ID3D12Resource)
        resource2.upload(b'Hello')
        self.assertEqual(resource.download()[0:5], b'Hello')
