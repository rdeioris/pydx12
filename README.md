# pydx12
High performance DirectX12 wrapper for Python

The project exposes access to various DirectX-related APIs, included D3D12 (rasterization, compute, raytracing), DXGI, XAudio2 and XInput.

If you are already familiar with these APIs in C/C++, you will find this wrapper super-straightforward, otherwise it can be a good way for learning state-of-the-art game libraries
starting from the supplied tutorials (they cover basically everything you need to start working with DirectX12)

Remember that DirectX is a Windows only environment, so this is the only supported platform :(

## Quickstart

If you already have experience with DirectX you will find this snippet for enumerating adapters (GPUs) pretty simple:

```py
from pydx12 import CreateDXGIFactory2

factory = CreateDXGIFactory2()
for adapter in factory.EnumAdapters():
    adapter_desc = adapter.GetDesc()
    print('{} ({} MB)'.format(adapter_desc.Description,
          adapter_desc.DedicatedVideoMemory / 1024 / 1024))
```

It basically creates a 'DXGI Factory' and call the EnumAdapters() method on it, returning a list of the adapters in the system. The GetDesc() method returns adapter's information in a DXGI_ADAPTER_DESC object (that wraps the DXGI_ADAPTER_DESC C struct: https://docs.microsoft.com/en-us/windows/win32/api/dxgi/ns-dxgi-dxgi_adapter_desc)


## DXGI

This is the library for accessing the adapters available in your system as well as the displays. It exposes the features for mapping SwapChains to windows (If you do not know what a SwapChain is, consider it as a double buffered framebuffer that will be shown on a desktop window)

## D3D12

## XAudio2

## XInput

## Status
