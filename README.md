# pydx12

DirectX 12 for Python, in pure `ctypes`.

pydx12 exposes the whole DirectX 12 family as plain Python: every enum, constant, struct, COM interface and
exported function, generated from Microsoft's own headers. Nothing is compiled — the package is Python
source plus the DirectX Shader Compiler DLLs.

DirectX is Windows only, so this is the only supported platform. Python 3.9+ on x64.

| Area | APIs |
|---|---|
| Direct3D 12 | Core API and DirectX 12 Ultimate (DXR raytracing, mesh/amplification shaders, variable rate shading, sampler feedback), enhanced barriers, work graphs, D3D12 video, debug layer / DRED, shader reflection, Agility SDK device factory |
| DXGI / DXCore | DXGI 1.0–1.6 (adapters, outputs, swapchains, debug), DXCore adapter enumeration |
| Shader compilers | DXC (`dxcompiler.dll`, bundled, SM 6.0–6.9), FXC (`d3dcompiler_47.dll`) |
| Compute / ML | DirectML |
| I/O and input | DirectStorage, GameInput, XInput |
| Audio | XAudio2, X3DAudio, XAPO |

## Install

From a checkout:

```
pip install .
```

DirectStorage and GameInput ship their runtimes as NuGet packages, and so does the newest D3D12 runtime (the Agility SDK);
see [Runtimes that are not in Windows](#runtimes-that-are-not-in-windows).

## Quickstart

```py
import pydx12 as dx

factory = dx.CreateDXGIFactory2()
i = 0
while True:
    try:
        adapter = factory.EnumAdapters1(i)
    except dx.DXError as e:
        if e.hresult == dx.DXGI_ERROR_NOT_FOUND:
            break
        raise
    desc = adapter.GetDesc1()
    print('%s (%d MB)' % (desc.Description, desc.DedicatedVideoMemory // 2**20))
    i += 1

device = dx.D3D12CreateDevice(factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE))
queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
```

Complete programs: [examples/triangle.py](examples/triangle.py) (a swapchain on a tkinter window) and the
tutorials in [docs/](docs), from enumerating adapters to DXR raytracing.

## How the C API maps to Python

Names and parameter order are the ones in Microsoft's documentation, so the C++ docs apply directly. The
generator reads the headers' SAL annotations and applies these rules:

- **Errors raise.** A failing `HRESULT` raises `pydx12.DXError` (`.hresult`, `.name`); compiler error blobs
  are included in the message. Successful calls return their out-parameters, or `None`.
- **Out-parameters are returned.** `adapter.GetDesc1()` returns a `DXGI_ADAPTER_DESC1`;
  several out-parameters come back as a tuple.
- **`riid` / `ppv` pairs take an interface class** and return that interface. Common factory methods have
  a default: `device.CreateCommandList(0, type, allocator)` returns an `ID3D12GraphicsCommandList`, and
  `factory.CreateDeviceFactory(...)`, `D3D12CreateDevice(...)` and the like pick the obvious interface.
  Pass another class to get a newer version: `D3D12CreateDevice(adapter, D3D_FEATURE_LEVEL_12_2, dx.ID3D12Device10)`.
- **Arrays take sequences** and their count parameter is filled in for you:
  `cl.ResourceBarrier([barrier])`, `queue.ExecuteCommandLists([cl])`. The count is still available as a
  keyword-only argument for partial arrays.
- **Buffers take bytes-like objects**: `bytes`, `bytearray`, `memoryview`, numpy arrays, ctypes arrays, or a
  blob (`ID3DBlob`, `IDxcBlob`). Strings take `str`.
- **Methods that return a struct** (`GetDesc()`, `GetCPUDescriptorHandleForHeapStart()`, …) return it.
- **Pointers you get back are integers.** `resource.Map(0)` returns the address; use `ctypes.memmove`,
  `ctypes.string_at` or `(ctypes.c_float * n).from_address(addr)` to read and write it.
- **C++ default arguments are kept** (`xaudio2.CreateMasteringVoice()` needs none), and trailing optional
  pointers default to `None`.

Every method's docstring holds its C signature.

### Structs

Structs are `ctypes.Structure` subclasses with keyword constructors, and struct fields accept Python values:

```py
desc = dx.D3D12_GRAPHICS_PIPELINE_STATE_DESC(
    pRootSignature=root_signature,                       # COM object: kept alive by the struct
    VS=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=blob),   # BytecodeLength is filled in
    RTVFormats=(dx.DXGI_FORMAT_R8G8B8A8_UNORM,),         # fixed arrays take short sequences
    NumRenderTargets=1)
desc.InputLayout.pInputElementDescs = [                  # NumElements is filled in
    dx.D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=dx.DXGI_FORMAT_R32G32B32_FLOAT)]
```

Pointer and count fields, string fields, buffer fields and interface fields keep what you assign to them alive
for as long as the struct (or any struct it is copied into) lives. Anonymous unions are flattened as in C
(`barrier.Transition`, `clear_value.Color`).

### COM objects

Interface wrappers release their reference when garbage collected. `Interface(obj)` and
`obj.QueryInterface(Interface)` both call `QueryInterface`, for example `dx.ID3D12InfoQueue(device)`.
`obj.value` is the raw pointer.

To implement an interface in Python (XAudio2 callbacks, include handlers, and so on), subclass `ComImplementation`:

```py
class EngineCallback(dx.ComImplementation):
    _interfaces_ = (dx.IXAudio2EngineCallback,)

    def OnCriticalError(self, error):
        print('XAudio2 error', hex(error))

xaudio2.RegisterForCallbacks(EngineCallback())
```

Keep a reference to the object for as long as the API may call it.

## Runtimes that are not in Windows

The bindings are generated from these SDK versions (`dx.PACKAGE_VERSIONS`):

| Package (NuGet) | Version | DLLs |
|---|---|---|
| `Microsoft.Direct3D.D3D12` (Agility SDK) | 1.620.2 | `D3D12Core.dll`, `d3d12SDKLayers.dll` |
| `Microsoft.Direct3D.DXC` | 1.9.2609.5 | `dxcompiler.dll`, `dxil.dll` (bundled in pydx12) |
| `Microsoft.Direct3D.DirectStorage` | 1.4.0 | `dstorage.dll`, `dstoragecore.dll` |
| `Microsoft.GameInput` | 4.1.315 | `GameInputRedist.dll` |

**Agility SDK.** The in-box D3D12 runtime works for the core API. For the newest features, load the Agility
SDK runtime through the device factory. This works from `python.exe` and does not need developer mode:

```py
config = dx.D3D12GetInterface(dx.CLSID_D3D12SDKConfiguration, dx.ID3D12SDKConfiguration1)
factory = config.CreateDeviceFactory(dx.AGILITY_SDK_VERSION, 'C:\\path\\to\\agility\\bin\\x64\\')
device = factory.CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_0, dx.ID3D12Device)
```

**DirectStorage, GameInput.** Put the DLLs next to your program, or add their folder:

```py
os.add_dll_directory(r'C:\path\to\directstorage\bin\x64')
storage = dx.DStorageGetFactory()
```

XAudio2 needs COM initialized on the calling thread (`ctypes.windll.ole32.CoInitializeEx(None, 0)`).

## Regenerating the bindings

`pydx12/_api.py` is generated by [tools/generate.py](tools/generate.py) from the Windows SDK headers plus any
NuGet packages extracted under `.deps/<name>-<version>/pkg` (agility, dxc, directstorage, gameinput):

```
pip install clang==<your libclang version>      # LLVM must be installed (libclang.dll)
python tools/generate.py
```

It needs the Windows SDK, the MSVC headers and LLVM. `tests/layout_data.py` is generated along with it,
and `tests/test_layout.py` checks every struct's size, alignment and field offsets against clang's
MSVC x64 layout.

## Tests

```
pip install pytest numpy
python -m pytest tests
```

The tests need a D3D12-capable GPU. The Agility SDK, DirectStorage and GameInput tests are skipped
unless those packages are under `.deps/`.
