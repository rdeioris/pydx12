import ctypes
import gc

import pytest

import pydx12 as dx


def buffer_desc(size, flags=dx.D3D12_RESOURCE_FLAG_NONE):
    desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                                  DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR,
                                  Flags=flags)
    desc.SampleDesc.Count = 1
    return desc


def heap(type_):
    return dx.D3D12_HEAP_PROPERTIES(Type=type_)


def test_enum_adapters(factory):
    adapters = []
    i = 0
    while True:
        try:
            adapters.append(factory.EnumAdapters1(i))
        except dx.DXError as e:
            assert e.hresult == dx.DXGI_ERROR_NOT_FOUND
            break
        i += 1
    assert adapters
    assert isinstance(adapters[0].GetDesc1().Description, str)


def test_device_and_query_interface(device):
    assert isinstance(device, dx.ID3D12Device)
    assert isinstance(device.QueryInterface(dx.ID3D12Device5), dx.ID3D12Device5)
    assert isinstance(dx.ID3D12Device1(device), dx.ID3D12Device1)
    assert device.GetNodeCount() >= 1


def test_refcount_release():
    dev = dx.D3D12CreateDevice()
    dev2 = dx.ID3D12Device(dev)
    assert dev2.AddRef() >= 3
    dev2.Release()
    del dev, dev2
    gc.collect()


def test_struct_return(device):
    h = device.CreateHeap(dx.D3D12_HEAP_DESC(SizeInBytes=64 * 1024, Properties=heap(dx.D3D12_HEAP_TYPE_READBACK)))
    assert isinstance(h, dx.ID3D12Heap)
    assert h.GetDesc().SizeInBytes == 64 * 1024
    assert isinstance(device.GetAdapterLuid(), dx.LUID)


def test_placed_resources_alias(device):
    h = device.CreateHeap(dx.D3D12_HEAP_DESC(SizeInBytes=128 * 1024, Properties=heap(dx.D3D12_HEAP_TYPE_UPLOAD)))
    a = device.CreatePlacedResource(h, 64 * 1024, buffer_desc(64), dx.D3D12_RESOURCE_STATE_GENERIC_READ)
    b = device.CreatePlacedResource(h, 64 * 1024, buffer_desc(64), dx.D3D12_RESOURCE_STATE_GENERIC_READ)
    ctypes.memmove(a.Map(0), b'Hello', 5)
    a.Unmap(0)
    assert ctypes.string_at(b.Map(0, dx.D3D12_RANGE(0, 5)), 5) == b'Hello'
    b.Unmap(0)


def test_interface_field_keeps_reference(device):
    res = device.CreateCommittedResource(heap(dx.D3D12_HEAP_TYPE_DEFAULT), dx.D3D12_HEAP_FLAG_NONE,
                                         buffer_desc(256, dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS),
                                         dx.D3D12_RESOURCE_STATE_COMMON)
    barrier = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_UAV)
    barrier.UAV.pResource = res
    ptr = res.value
    del res
    gc.collect()
    assert barrier.UAV.pResource.value == ptr
    assert isinstance(barrier.UAV.pResource, dx.ID3D12Resource)


def test_error_raises(device):
    with pytest.raises(dx.DXError) as e:
        device.CreateCommittedResource(heap(dx.D3D12_HEAP_TYPE_UPLOAD), dx.D3D12_HEAP_FLAG_NONE,
                                       buffer_desc(0), dx.D3D12_RESOURCE_STATE_GENERIC_READ)
    assert e.value.hresult == dx.E_INVALIDARG


def test_compute_roundtrip(device):
    n = 1024
    src = ('RWStructuredBuffer<uint> b : register(u0);'
           '[numthreads(64,1,1)] void main(uint3 id : SV_DispatchThreadID) { b[id.x] = b[id.x] * 3 + 1; }')
    cs = dx.D3DCompile(src, None, None, None, 'main', 'cs_5_0')
    rs = dx.D3D12SerializeRootSignature(dx.D3D12_ROOT_SIGNATURE_DESC(pParameters=[
        dx.D3D12_ROOT_PARAMETER(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_UAV)]), dx.D3D_ROOT_SIGNATURE_VERSION_1)
    root = device.CreateRootSignature(0, rs)
    pso = device.CreateComputePipelineState(dx.D3D12_COMPUTE_PIPELINE_STATE_DESC(
        pRootSignature=root, CS=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=cs)))
    size = n * 4
    upload = device.CreateCommittedResource(heap(dx.D3D12_HEAP_TYPE_UPLOAD), 0, buffer_desc(size),
                                            dx.D3D12_RESOURCE_STATE_GENERIC_READ)
    gpu = device.CreateCommittedResource(heap(dx.D3D12_HEAP_TYPE_DEFAULT), 0,
                                         buffer_desc(size, dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS),
                                         dx.D3D12_RESOURCE_STATE_COMMON)
    readback = device.CreateCommittedResource(heap(dx.D3D12_HEAP_TYPE_READBACK), 0, buffer_desc(size),
                                              dx.D3D12_RESOURCE_STATE_COPY_DEST)
    ctypes.memmove(upload.Map(0), (ctypes.c_uint * n)(*range(n)), size)
    upload.Unmap(0)
    queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
    allocator = device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
    cl = device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, allocator, pso)

    def transition(res, before, after):
        b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
        b.Transition = dx.D3D12_RESOURCE_TRANSITION_BARRIER(pResource=res, StateBefore=before, StateAfter=after,
                                                            Subresource=dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
        return b

    cl.CopyResource(gpu, upload)
    cl.ResourceBarrier([transition(gpu, dx.D3D12_RESOURCE_STATE_COPY_DEST, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
    cl.SetComputeRootSignature(root)
    cl.SetComputeRootUnorderedAccessView(0, gpu.GetGPUVirtualAddress())
    cl.Dispatch(n // 64, 1, 1)
    cl.ResourceBarrier([transition(gpu, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS, dx.D3D12_RESOURCE_STATE_COPY_SOURCE)])
    cl.CopyResource(readback, gpu)
    cl.Close()
    queue.ExecuteCommandLists([cl])
    fence = device.CreateFence()
    queue.Signal(fence, 1)
    fence.SetEventOnCompletion(1, None)  # NULL event: blocks until the GPU is done
    out = (ctypes.c_uint * n).from_address(readback.Map(0))
    assert list(out) == [i * 3 + 1 for i in range(n)]
    readback.Unmap(0)


def test_feature_support(device):
    o = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS()
    device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS, ctypes.byref(o), ctypes.sizeof(o))
    assert o.ResourceBindingTier >= dx.D3D12_RESOURCE_BINDING_TIER_1


def test_agility_device_factory(agility_path):
    cfg = dx.D3D12GetInterface(dx.CLSID_D3D12SDKConfiguration, dx.ID3D12SDKConfiguration1)
    factory = cfg.CreateDeviceFactory(dx.AGILITY_SDK_VERSION, agility_path)
    device = factory.CreateDevice(None, dx.D3D_FEATURE_LEVEL_12_0, dx.ID3D12Device)
    assert dx.ID3D12DeviceConfiguration(device).GetDesc().SDKVersion == dx.AGILITY_SDK_VERSION
