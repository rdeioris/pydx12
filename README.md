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
| Tools | PIX events, markers, counters and programmatic captures |
| Interop | D3D11On12 and D3D9On12, with the Direct3D 11 and Direct3D 9 APIs they return |
| I/O and input | DirectStorage, GameInput, XInput |
| Audio | XAudio2, X3DAudio, XAPO |

The package ships type information (`.pyi` stubs), so editors and type checkers know the parameters,
fields and return types.

## Install

```
pip install pydx12
```

DirectStorage, GameInput and PIX ship their runtimes as NuGet packages, and so does the newest D3D12 runtime
(the Agility SDK); see [Runtimes that are not in Windows](#runtimes-that-are-not-in-windows).

The examples and tutorials also use numpy and Pillow (`pip install numpy pillow`), and tutorials 012-017
use pyrr.

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

adapter = factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)
device = dx.D3D12CreateDevice(adapter)
queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
```

Complete programs, in [examples/](https://github.com/rdeioris/pydx12/tree/main/examples):

- `triangle.py`: a swapchain on a tkinter window
- `directml_life.py`: Conway's Game of Life as a DirectML operator graph (wrap padding, a 3×3
  convolution and two element-wise operators)
- `xaudio2_orbit.py`: a synthesized sound orbiting around you, with X3DAudio panning, Doppler and
  distance-driven reverb, and a volume meter showing the left/right levels
- `gamepad.py`: a live gamepad view with rumble, plus keyboard and mouse, through GameInput (or XInput)

The tutorials in [docs/](https://github.com/rdeioris/pydx12/tree/main/docs) go from enumerating adapters
to DXR raytracing.

## How the C API maps to Python

Names and parameter order are the ones in Microsoft's documentation, so the C++ docs apply directly. The
generator reads the headers' SAL annotations and applies these rules:

- **Errors raise.** A failing `HRESULT` raises `pydx12.DXError` (`.hresult`, `.name`); compiler error blobs
  are included in the message. Successful calls return their out-parameters, or `None` (other success
  codes, such as `DXGI_STATUS_OCCLUDED` from `Present`, are returned as an int).
- **Out-parameters are returned.** `adapter.GetDesc1()` returns a `DXGI_ADAPTER_DESC1`;
  several out-parameters come back as a tuple.
- **`riid` / `ppv` pairs take an interface class** and return that interface. Common factory methods have
  a default: `device.CreateCommandList(0, type, allocator)` returns an `ID3D12GraphicsCommandList`, and
  `D3D12CreateDevice(...)`, `CreateDXGIFactory2()` and the like pick the obvious interface. Pass another
  class to get a newer version: `dx.D3D12CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_2, dx.ID3D12Device10)`.
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

callback = EngineCallback()
xaudio2.RegisterForCallbacks(callback)
```

Keep a reference to the object (here `callback`) for as long as the API may call it.

## Runtimes that are not in Windows

The bindings are generated from these SDK versions (`dx.PACKAGE_VERSIONS`):

| Package (NuGet) | Version | DLLs |
|---|---|---|
| `Microsoft.Direct3D.D3D12` (Agility SDK) | 1.620.2 | `D3D12Core.dll`, `d3d12SDKLayers.dll` |
| `Microsoft.Direct3D.DXC` | 1.9.2609.5 | `dxcompiler.dll`, `dxil.dll` (bundled in pydx12) |
| `Microsoft.Direct3D.DirectStorage` | 1.4.0 | `dstorage.dll`, `dstoragecore.dll` |
| `Microsoft.GameInput` | 4.1.315 | `GameInputRedist.dll` |
| `WinPixEventRuntime` | 1.0.240308001 | `WinPixEventRuntime.dll` |

**Agility SDK.** The in-box D3D12 runtime works for the core API. For the newest features, load the Agility
SDK runtime through the device factory. This works from `python.exe` and does not need developer mode:

```py
config = dx.D3D12GetInterface(dx.CLSID_D3D12SDKConfiguration, dx.ID3D12SDKConfiguration1)
device_factory = config.CreateDeviceFactory(dx.AGILITY_SDK_VERSION, 'C:\\path\\to\\agility\\bin\\x64\\')
device = device_factory.CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_0, dx.ID3D12Device)
```

**DirectStorage, GameInput, PIX.** Put the DLLs next to your program, or add their folder:

```py
os.add_dll_directory(r'C:\path\to\directstorage\bin\x64')
storage = dx.DStorageGetFactory()
```

**XAudio2** is in Windows, but needs COM initialized on the calling thread
(`ctypes.windll.ole32.CoInitializeEx(None, 0)`).

**PIX.** Events and markers show up in PIX captures; they take a color (`0xAARRGGBB`) and a plain string:

```py
dx.PIXBeginEventOnCommandList(command_list, 0xFF00FF00, 'shadows')
...
dx.PIXEndEventOnCommandList(command_list)
```

Programmatic GPU captures (`PIXGpuCaptureNextFrames`, `PIXBeginCapture2`, `PIXSetTargetWindow`, ...) need
`WinPixGpuCapturer.dll` from the PIX installation folder to be loaded before the D3D12 device is created, for
example with `ctypes.WinDLL(r'C:\Program Files\Microsoft PIX\<version>\WinPixGpuCapturer.dll')`.

**D3D11On12, D3D9On12.** Run Direct3D 11 or 9 code on a D3D12 device, sharing its resources:

```py
device11, context11, level = dx.D3D11On12CreateDevice(device12, 0, None, [queue], 0)
on12 = dx.ID3D11On12Device(device11)
texture11 = on12.CreateWrappedResource(texture12, dx.D3D11_RESOURCE_FLAGS(BindFlags=dx.D3D11_BIND_RENDER_TARGET),
                                       dx.D3D12_RESOURCE_STATE_RENDER_TARGET, dx.D3D12_RESOURCE_STATE_PRESENT,
                                       dx.ID3D11Texture2D)
```

## Regenerating the bindings

`pydx12/_api.py` is generated by [tools/generate.py](https://github.com/rdeioris/pydx12/blob/main/tools/generate.py) from the Windows SDK headers plus any
NuGet packages extracted under `.deps/<name>-<version>/pkg` (agility, dxc, directstorage, gameinput,
winpixeventruntime). It writes `pydx12/_api.pyi` (the type stubs) at the same time:

```
pip install clang==<your libclang version>      # LLVM must be installed (libclang.dll)
python tools/generate.py
```

A `.nupkg` is a zip file: download it from nuget.org and extract it, for example into
`.deps/agility-1.620.2/pkg`. The newest version of each package found there is used.

It needs the Windows SDK, the MSVC headers and LLVM. `tests/layout_data.py` is generated along with it,
and `tests/test_layout.py` checks every struct's size, alignment and field offsets against clang's
MSVC x64 layout.

## Tests

```
pip install pytest numpy
python -m pytest tests
```

The tests need a D3D12-capable GPU. The Agility SDK, DirectStorage, GameInput and PIX tests are skipped
unless those packages are under `.deps/`. To check the type stubs against the examples and tests:

```
pip install mypy
python -m mypy --ignore-missing-imports --check-untyped-defs examples tests
```
