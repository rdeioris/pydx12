"""D3D11On12 and D3D9On12: older APIs running on top of a D3D12 device."""
import ctypes

import pydx12 as dx


def readback_pixel(device, queue, texture):
    """Copy the top-left pixel of a 2D texture into a readback buffer and return its 4 bytes."""
    footprints, _, _, total = device.GetCopyableFootprints(texture.GetDesc(), 0, 1, 0)
    desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=total, Height=1,
                                  DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR)
    desc.SampleDesc.Count = 1
    readback = device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_READBACK),
                                              dx.D3D12_HEAP_FLAG_NONE, desc, dx.D3D12_RESOURCE_STATE_COPY_DEST)
    allocator = device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
    cl = device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
    dst = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=readback, Type=dx.D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT)
    dst.PlacedFootprint = footprints[0]
    src = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=texture, Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX)
    cl.CopyTextureRegion(dst, 0, 0, 0, src, None)
    cl.Close()
    queue.ExecuteCommandLists([cl])
    fence = device.CreateFence()
    queue.Signal(fence, 1)
    fence.SetEventOnCompletion(1, None)
    pixel = ctypes.string_at(readback.Map(0), 4)
    readback.Unmap(0)
    return pixel


def test_d3d11on12_renders_into_d3d12_texture(device):
    queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
    device11, context11, level = dx.D3D11On12CreateDevice(device, dx.D3D11_CREATE_DEVICE_BGRA_SUPPORT, None,
                                                          [queue], 0)
    assert isinstance(device11, dx.ID3D11Device) and isinstance(context11, dx.ID3D11DeviceContext)
    assert level >= dx.D3D_FEATURE_LEVEL_11_0
    on12 = dx.ID3D11On12Device(device11)

    desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=16, Height=16,
                                  DepthOrArraySize=1, MipLevels=1, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                  Flags=dx.D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET)
    desc.SampleDesc.Count = 1
    texture = device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                             dx.D3D12_HEAP_FLAG_NONE, desc, dx.D3D12_RESOURCE_STATE_RENDER_TARGET)

    # D3D11 clears the D3D12 texture; releasing it hands it back to D3D12 in COPY_SOURCE state
    wrapped = on12.CreateWrappedResource(texture, dx.D3D11_RESOURCE_FLAGS(BindFlags=dx.D3D11_BIND_RENDER_TARGET),
                                         dx.D3D12_RESOURCE_STATE_RENDER_TARGET, dx.D3D12_RESOURCE_STATE_COPY_SOURCE,
                                         dx.ID3D11Texture2D)
    rtv = device11.CreateRenderTargetView(wrapped, None)
    context11.ClearRenderTargetView(rtv, (1.0, 0.5, 0.0, 1.0))
    on12.ReleaseWrappedResources([wrapped])
    context11.Flush()

    r, g, b, a = readback_pixel(device, queue, texture)
    assert (r, b, a) == (255, 0, 255) and g in (127, 128)  # 0.5 -> UNORM rounds either way


def test_d3d9on12_clear(device):
    queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
    args = dx.D3D9ON12_ARGS(Enable9On12=1, pD3D12Device=device, NumQueues=1)
    args.ppD3D12Queues[0] = queue.value  # fixed array of raw pointers: `queue` stays alive in this scope
    d3d9 = dx.Direct3DCreate9On12(dx.D3D_SDK_VERSION, args, 1)
    assert isinstance(d3d9, dx.IDirect3D9)

    hwnd = ctypes.windll.user32.GetDesktopWindow()
    params = dx.D3DPRESENT_PARAMETERS(BackBufferWidth=16, BackBufferHeight=16, BackBufferFormat=dx.D3DFMT_A8R8G8B8,
                                      BackBufferCount=1, SwapEffect=dx.D3DSWAPEFFECT_DISCARD, hDeviceWindow=hwnd,
                                      Windowed=1)
    device9 = d3d9.CreateDevice(dx.D3DADAPTER_DEFAULT, dx.D3DDEVTYPE_HAL, hwnd,
                                dx.D3DCREATE_HARDWARE_VERTEXPROCESSING, params)
    on12 = dx.IDirect3DDevice9On12(device9)
    assert on12.GetD3D12Device(dx.ID3D12Device) == device

    device9.Clear(0, None, dx.D3DCLEAR_TARGET, 0xFF2040C0, 1.0, 0)  # D3DCOLOR is ARGB
    target = device9.GetRenderTarget(0)
    surface = device9.CreateOffscreenPlainSurface(16, 16, dx.D3DFMT_A8R8G8B8, dx.D3DPOOL_SYSTEMMEM, None)
    device9.GetRenderTargetData(target, surface)
    locked = dx.D3DLOCKED_RECT()
    surface.LockRect(locked, None, dx.D3DLOCK_READONLY)
    assert locked.pBits
    pixel = ctypes.string_at(locked.pBits, 4)
    surface.UnlockRect()
    assert pixel == bytes([0xC0, 0x40, 0x20, 0xFF])  # BGRA in memory
