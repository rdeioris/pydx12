from pydx12 import CreateDXGIFactory2, DXError, DXGI_ERROR_NOT_FOUND


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
