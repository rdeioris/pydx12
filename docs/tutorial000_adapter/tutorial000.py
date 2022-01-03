from pydx12 import CreateDXGIFactory2

factory = CreateDXGIFactory2()
for adapter in factory.EnumAdapters():
    adapter_desc = adapter.GetDesc()
    print('{} ({} MB)'.format(adapter_desc.Description,
          adapter_desc.DedicatedVideoMemory / 1024 / 1024))


def get_best_adapter():
    factory = CreateDXGIFactory2()
    return sorted(factory.EnumAdapters(), key=lambda a: a.GetDesc().DedicatedVideoMemory)[0]


print('The best adapter is', get_best_adapter())
