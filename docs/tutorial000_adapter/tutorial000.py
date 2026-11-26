from pydx12 import CreateDXGIFactory2, DXError, DXGI_ERROR_NOT_FOUND

# A DXGI factory is the entry point for enumerating the GPUs (adapters) of the system
factory = CreateDXGIFactory2()


def enum_adapters(factory):
    # EnumAdapters1() fails with DXGI_ERROR_NOT_FOUND when there are no more adapters
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


for adapter in enum_adapters(factory):
    adapter_desc = adapter.GetDesc1()
    print('{} ({} MB)'.format(adapter_desc.Description,
          adapter_desc.DedicatedVideoMemory // 1024 // 1024))


def get_best_adapter():
    # the adapter with the most dedicated video memory is usually the fastest one
    return max(enum_adapters(CreateDXGIFactory2()), key=lambda a: a.GetDesc1().DedicatedVideoMemory)


print('The best adapter is', get_best_adapter().GetDesc1().Description)
