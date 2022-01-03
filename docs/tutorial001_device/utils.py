from pydx12 import CreateDXGIFactory2


def get_best_adapter():
    factory = CreateDXGIFactory2()
    return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[0]
