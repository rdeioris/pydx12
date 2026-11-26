"""
pydx12 binding generator.

Parses the DirectX headers of the Windows SDK with libclang and emits
``pydx12/_api.py``: a pure ctypes module with every enum, constant, struct,
union, COM interface and exported function of D3D12 (including DX12
Ultimate: DXR, mesh shaders, VRS, sampler feedback, enhanced barriers,
work graphs), D3D12 video, DXGI 1.0-1.6, D3DCompiler, DXC, DXCore,
DirectML, XAudio2/X3DAudio/XAPO and XInput.

SAL annotations found in the headers are used to make the methods
Pythonic: _Out_ parameters are returned, failed HRESULTs raise DXError,
riid/ppv pairs take an interface class and return a wrapper, arrays with
a count parameter take Python sequences, and so on.

Usage:  python tools/generate.py [--sdk 10.0.26100.0] [--check]
Requires: pip install clang==<libclang version>, LLVM (libclang.dll),
          Windows SDK, MSVC headers.
"""
import argparse
import ctypes
import glob
import keyword
import os
import re
import sys
import time
from collections import OrderedDict

import clang.cindex as ci
from clang.cindex import CursorKind as CK, TypeKind as TK

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'pydx12', '_api.py')
LAYOUT_OUT = os.path.join(ROOT, 'tests', 'layout_data.py')

# (header, dll exporting its functions)
HEADERS = [
    ('dxgiformat.h', None),
    ('dxgitype.h', None),
    ('dxgicommon.h', None),
    ('dxgi.h', 'dxgi.dll'),
    ('dxgi1_2.h', 'dxgi.dll'),
    ('dxgi1_3.h', 'dxgi.dll'),
    ('dxgi1_4.h', 'dxgi.dll'),
    ('dxgi1_5.h', 'dxgi.dll'),
    ('dxgi1_6.h', 'dxgi.dll'),
    ('dxgidebug.h', 'dxgidebug.dll'),
    ('DXGIMessages.h', None),
    ('d3dcommon.h', None),
    ('d3d12.h', 'd3d12.dll'),
    ('d3d12sdklayers.h', 'd3d12.dll'),
    ('d3d12shader.h', None),
    ('d3d12video.h', 'd3d12.dll'),
    ('d3d12compatibility.h', 'd3d12.dll'),
    ('d3d12compiler.h', 'D3D12StateObjectCompiler.dll'),    # Agility SDK only
    ('d3dshadercacheregistration.h', 'd3d12.dll'),          # Agility SDK only
    ('d3dcompiler.h', 'd3dcompiler_47.dll'),
    ('dxcapi.h', 'dxcompiler.dll'),
    ('dxcore_interface.h', 'dxcore.dll'),
    ('dxcore.h', 'dxcore.dll'),
    ('DirectML.h', 'DirectML.dll'),
    ('xaudio2.h', 'xaudio2_9.dll'),
    ('xaudio2fx.h', 'xaudio2_9.dll'),
    ('xapo.h', 'xaudio2_9.dll'),
    ('xapofx.h', 'xaudio2_9.dll'),
    ('x3daudio.h', 'xaudio2_9.dll'),
    ('Xinput.h', 'xinput1_4.dll'),
    # NuGet-only SDKs (headers found under .deps/, see find_packages)
    ('dxcerrors.h', None),                                  # DXC
    ('dstorageerr.h', None),                                # DirectStorage
    ('dstorage.h', 'dstorage.dll'),
    ('GameInput.h', 'GameInputRedist.dll'),                 # GameInput
]

# NuGet packages under .deps/<name>-<version>/pkg: name -> include dir inside the package.
# Earlier entries shadow later ones and the Windows SDK.
PACKAGES = [
    ('agility', os.path.join('build', 'native', 'include')),
    ('dxc', os.path.join('build', 'native', 'include')),
    ('directstorage', os.path.join('native', 'include')),
    ('gameinput', os.path.join('native', 'include')),
]


def _version_key(path):
    v = os.path.basename(os.path.dirname(path) if path.endswith('pkg') else path).split('-', 1)[-1]
    return [int(x) if x.isdigit() else 0 for x in re.split(r'[.-]', v)]


def find_packages(root=None):
    """Return {name: (version, include dir)} for the newest downloaded copy of each package."""
    root = root or os.path.join(ROOT, '.deps')
    found = {}
    for name, inc in PACKAGES:
        cands = [d for d in glob.glob(os.path.join(root, name + '-*')) if os.path.isdir(os.path.join(d, 'pkg', inc))]
        if cands:
            best = max(cands, key=_version_key)
            found[name] = (os.path.basename(best).split('-', 1)[1], os.path.join(best, 'pkg', inc))
    return found
HEADER_DLL = {h.lower(): d for h, d in HEADERS}

# winerror.h macros we want as constants
WINERROR_PREFIXES = ('DXGI_ERROR_', 'DXGI_STATUS_', 'DXGI_DDI_ERR_', 'D3D12_ERROR_', 'D3D10_ERROR_',
                     'D3D11_ERROR_', 'E_', 'S_OK', 'S_FALSE', 'DXCORE_ERROR_', 'PRESENTATION_ERROR_')

# functions exported by a different DLL than the rest of their header
FUNCTION_DLL = {'D3D12SDKLayersGetInterface': 'd3d12SDKLayers.dll'}

# macros from non-DirectX headers that the DirectX APIs need: header -> name prefixes
EXTERNAL_MACROS = {
    'winerror.h': WINERROR_PREFIXES,
    'mmreg.h': ('WAVE_FORMAT_', 'SPEAKER_'),
    'mmeapi.h': ('WAVE_FORMAT_',),
    'ksmedia.h': ('SPEAKER_',),
}

# riid/ppv default interface for well-known factory methods (method or function name -> iface)
RIID_DEFAULTS = {
    'D3D12CreateDevice': 'ID3D12Device',
    'D3D12GetDebugInterface': 'ID3D12Debug',
    'CreateDXGIFactory': 'IDXGIFactory',
    'CreateDXGIFactory1': 'IDXGIFactory1',
    'CreateDXGIFactory2': 'IDXGIFactory6',
    'DXGIGetDebugInterface1': 'IDXGIDebug1',
    'DXGIGetDebugInterface': 'IDXGIDebug',
    'D3D12CreateRootSignatureDeserializer': 'ID3D12RootSignatureDeserializer',
    'D3D12CreateVersionedRootSignatureDeserializer': 'ID3D12VersionedRootSignatureDeserializer',
    'D3D12CreateVersionedRootSignatureDeserializerFromSubobjectInDXILLibrary': 'ID3D12VersionedRootSignatureDeserializer',
    'D3DReflect': 'ID3D12ShaderReflection',
    'D3DReflectLibrary': 'ID3D12LibraryReflection',
    'DMLCreateDevice': 'IDMLDevice',
    'DMLCreateDevice1': 'IDMLDevice',
    'DXCoreCreateAdapterFactory': 'IDXCoreAdapterFactory',
    'DStorageGetFactory': 'IDStorageFactory',
    'GameInputInitialize': 'IGameInput',
    'D3D12GetInterface': None,
    'ID3D12Device.CreateCommandList': 'ID3D12GraphicsCommandList',
    'ID3D12Device4.CreateCommandList1': 'ID3D12GraphicsCommandList',
    'ID3D12Device.CreateCommandQueue': 'ID3D12CommandQueue',
    'ID3D12Device.CreateCommandAllocator': 'ID3D12CommandAllocator',
    'ID3D12Device.CreateGraphicsPipelineState': 'ID3D12PipelineState',
    'ID3D12Device.CreateComputePipelineState': 'ID3D12PipelineState',
    'ID3D12Device2.CreatePipelineState': 'ID3D12PipelineState',
    'ID3D12Device.CreateCommittedResource': 'ID3D12Resource',
    'ID3D12Device4.CreateCommittedResource1': 'ID3D12Resource',
    'ID3D12Device8.CreateCommittedResource2': 'ID3D12Resource',
    'ID3D12Device10.CreateCommittedResource3': 'ID3D12Resource',
    'ID3D12Device.CreatePlacedResource': 'ID3D12Resource',
    'ID3D12Device8.CreatePlacedResource1': 'ID3D12Resource',
    'ID3D12Device10.CreatePlacedResource2': 'ID3D12Resource',
    'ID3D12Device.CreateReservedResource': 'ID3D12Resource',
    'ID3D12Device4.CreateReservedResource1': 'ID3D12Resource',
    'ID3D12Device10.CreateReservedResource2': 'ID3D12Resource',
    'ID3D12Device.CreateHeap': 'ID3D12Heap',
    'ID3D12Device4.CreateHeap1': 'ID3D12Heap',
    'ID3D12Device.CreateFence': 'ID3D12Fence',
    'ID3D12Device.CreateQueryHeap': 'ID3D12QueryHeap',
    'ID3D12Device.CreateCommandSignature': 'ID3D12CommandSignature',
    'ID3D12Device.CreateRootSignature': 'ID3D12RootSignature',
    'ID3D12Device.CreateDescriptorHeap': 'ID3D12DescriptorHeap',
    'ID3D12Device.OpenSharedHandle': 'ID3D12Resource',
    'ID3D12Device5.CreateStateObject': 'ID3D12StateObject',
    'ID3D12Device7.AddToStateObject': 'ID3D12StateObject',
    'ID3D12Device1.CreatePipelineLibrary': 'ID3D12PipelineLibrary',
    'ID3D12Device5.CreateMetaCommand': 'ID3D12MetaCommand',
    'ID3D12Device5.CreateLifetimeTracker': 'ID3D12LifetimeTracker',
    'ID3D12Device4.CreateProtectedResourceSession': 'ID3D12ProtectedResourceSession',
    'ID3D12Device7.CreateProtectedResourceSession1': 'ID3D12ProtectedResourceSession1',
    'ID3D12Device9.CreateShaderCacheSession': 'ID3D12ShaderCacheSession',
    'ID3D12Device9.CreateCommandQueue1': 'ID3D12CommandQueue',
    'ID3D12DeviceChild.GetDevice': 'ID3D12Device',
    'ID3D12PipelineLibrary.LoadGraphicsPipeline': 'ID3D12PipelineState',
    'ID3D12PipelineLibrary.LoadComputePipeline': 'ID3D12PipelineState',
    'ID3D12PipelineLibrary1.LoadPipeline': 'ID3D12PipelineState',
    'ID3D12DeviceFactory.CreateDevice': 'ID3D12Device',
    'ID3D12DeviceFactory.GetConfigurationInterface': 'ID3D12DeviceConfiguration',
    'ID3D12SDKConfiguration1.CreateDeviceFactory': 'ID3D12DeviceFactory',
    'IDXGISwapChain.GetBuffer': 'ID3D12Resource',
    'IDXGIFactory4.EnumAdapterByLuid': 'IDXGIAdapter1',
    'IDXGIFactory4.EnumWarpAdapter': 'IDXGIAdapter1',
    'IDXGIFactory6.EnumAdapterByGpuPreference': 'IDXGIAdapter1',
    'IDxcResult.GetOutput': 'IDxcBlob',
    'IDXCoreAdapterFactory.CreateAdapterList': 'IDXCoreAdapterList',
    'IDXCoreAdapterFactory.GetAdapterByLuid': 'IDXCoreAdapter',
    'IDXCoreAdapterList.GetAdapter': 'IDXCoreAdapter',
    'IDMLDevice.CreateOperator': 'IDMLOperator',
    'IDMLDevice.CompileOperator': 'IDMLCompiledOperator',
    'IDMLDevice.CreateOperatorInitializer': 'IDMLOperatorInitializer',
    'IDMLDevice.CreateCommandRecorder': 'IDMLCommandRecorder',
    'IDMLDevice.CreateBindingTable': 'IDMLBindingTable',
    'IDMLDevice1.CompileGraph': 'IDMLCompiledOperator',
    'IDMLObject.GetParentDevice': 'IDMLDevice',
    'IDMLDeviceChild.GetDevice': 'IDMLDevice',
    'ID3D12VideoDevice.CreateVideoDecoder': 'ID3D12VideoDecoder',
    'ID3D12VideoDevice.CreateVideoDecoderHeap': 'ID3D12VideoDecoderHeap',
    'ID3D12VideoDevice.CreateVideoProcessor': 'ID3D12VideoProcessor',
    'ID3D12VideoDevice1.CreateVideoMotionEstimator': 'ID3D12VideoMotionEstimator',
    'ID3D12VideoDevice1.CreateVideoMotionVectorHeap': 'ID3D12VideoMotionVectorHeap',
    'ID3D12VideoDevice2.CreateVideoDecoder1': 'ID3D12VideoDecoder1',
    'ID3D12VideoDevice2.CreateVideoDecoderHeap1': 'ID3D12VideoDecoderHeap1',
    'ID3D12VideoDevice2.CreateVideoProcessor1': 'ID3D12VideoProcessor1',
    'ID3D12VideoDevice2.CreateVideoExtensionCommand': 'ID3D12VideoExtensionCommand',
    'ID3D12VideoDevice3.CreateVideoEncoder': 'ID3D12VideoEncoder',
    'ID3D12VideoDevice3.CreateVideoEncoderHeap': 'ID3D12VideoEncoderHeap',
}

# Default values for trailing parameters: name -> {param: python expr}
PARAM_DEFAULTS = {
    'D3D12CreateDevice': {'MinimumFeatureLevel': 'D3D_FEATURE_LEVEL_11_0'},
    'CreateDXGIFactory2': {'Flags': '0'},
    'ID3D12Device.CreateFence': {'InitialValue': '0', 'Flags': 'D3D12_FENCE_FLAG_NONE'},
    'ID3D12Device.CreateCommandList': {'pInitialState': 'None'},
    'ID3D12Device.CreateRootSignature': {},
    'IDXGISwapChain.Present': {'SyncInterval': '1', 'Flags': '0'},
    'IDXGISwapChain.ResizeBuffers': {'NewFormat': 'DXGI_FORMAT_UNKNOWN', 'SwapChainFlags': '0'},
    'D3DCompile': {'pSourceName': 'None', 'pDefines': 'None', 'pInclude': 'None', 'Flags1': '0', 'Flags2': '0'},
    'D3DCompile2': {'Flags1': '0', 'Flags2': '0', 'SecondaryDataFlags': '0', 'pSecondaryData': 'None'},
    'D3DCompileFromFile': {'pDefines': 'None', 'pInclude': 'None', 'Flags1': '0', 'Flags2': '0'},
}

INT_KINDS = {
    TK.BOOL: 'c_bool', TK.CHAR_S: 'c_char', TK.SCHAR: 'c_byte', TK.CHAR_U: 'c_ubyte', TK.UCHAR: 'c_ubyte',
    TK.WCHAR: 'c_wchar', TK.CHAR16: 'c_wchar', TK.SHORT: 'c_short', TK.USHORT: 'c_ushort',
    TK.INT: 'c_int', TK.UINT: 'c_uint', TK.LONG: 'c_long', TK.ULONG: 'c_ulong',
    TK.LONGLONG: 'c_int64', TK.ULONGLONG: 'c_uint64', TK.FLOAT: 'c_float', TK.DOUBLE: 'c_double',
    TK.LONGDOUBLE: 'c_double', TK.CHAR32: 'c_uint32', TK.INT128: 'c_byte * 16', TK.UINT128: 'c_ubyte * 16',
}
INTEGER_TYPES = {'c_bool', 'c_byte', 'c_ubyte', 'c_short', 'c_ushort', 'c_int', 'c_uint', 'c_long', 'c_ulong',
                 'c_int64', 'c_uint64', 'c_size_t', 'c_ssize_t', 'c_char', 'c_wchar', 'c_uint32'}

SAL_RE = re.compile(r'\b(_[A-Za-z0-9_]*_)\s*')


def find_sdk(version=None):
    base = r'C:\Program Files (x86)\Windows Kits\10\Include'
    versions = sorted(os.listdir(base), key=lambda v: [int(x) if x.isdigit() else 0 for x in v.split('.')])
    versions = [v for v in versions if v.startswith('10.')]
    v = version or versions[-1]
    return os.path.join(base, v), v


def find_msvc():
    cands = glob.glob(r'C:\Program Files\Microsoft Visual Studio\*\*\VC\Tools\MSVC\*\include')
    cands += glob.glob(r'C:\Program Files (x86)\Microsoft Visual Studio\*\*\VC\Tools\MSVC\*\include')
    if not cands:
        sys.exit('MSVC headers not found')
    return sorted(cands)[-1]


def find_llvm():
    for p in (os.environ.get('LIBCLANG_PATH'), r'C:\Program Files\LLVM\bin\libclang.dll'):
        if p and os.path.exists(p):
            return p
    sys.exit('libclang.dll not found (set LIBCLANG_PATH)')


# ---------------------------------------------------------------------------
# libclang helpers
# ---------------------------------------------------------------------------

class Evaluator:
    def __init__(self):
        lib = ci.conf.lib
        self.lib = lib
        lib.clang_Cursor_Evaluate.argtypes = [ci.Cursor]
        lib.clang_Cursor_Evaluate.restype = ctypes.c_void_p
        lib.clang_EvalResult_getKind.argtypes = [ctypes.c_void_p]
        lib.clang_EvalResult_getKind.restype = ctypes.c_int
        lib.clang_EvalResult_getAsLongLong.argtypes = [ctypes.c_void_p]
        lib.clang_EvalResult_getAsLongLong.restype = ctypes.c_longlong
        lib.clang_EvalResult_isUnsignedInt.argtypes = [ctypes.c_void_p]
        lib.clang_EvalResult_isUnsignedInt.restype = ctypes.c_uint
        lib.clang_EvalResult_getAsUnsigned.argtypes = [ctypes.c_void_p]
        lib.clang_EvalResult_getAsUnsigned.restype = ctypes.c_ulonglong
        lib.clang_EvalResult_getAsDouble.argtypes = [ctypes.c_void_p]
        lib.clang_EvalResult_getAsDouble.restype = ctypes.c_double
        lib.clang_EvalResult_getAsStr.argtypes = [ctypes.c_void_p]
        lib.clang_EvalResult_getAsStr.restype = ctypes.c_char_p
        lib.clang_EvalResult_dispose.argtypes = [ctypes.c_void_p]

    def __call__(self, cursor):
        lib = self.lib
        r = lib.clang_Cursor_Evaluate(cursor)
        if not r:
            return None
        try:
            kind = lib.clang_EvalResult_getKind(r)
            if kind == 1:
                if lib.clang_EvalResult_isUnsignedInt(r):
                    return lib.clang_EvalResult_getAsUnsigned(r)
                return lib.clang_EvalResult_getAsLongLong(r)
            if kind == 2:
                return lib.clang_EvalResult_getAsDouble(r)
            if kind == 4:
                return lib.clang_EvalResult_getAsStr(r).decode('latin-1')
            return None
        finally:
            lib.clang_EvalResult_dispose(r)


_file_cache = {}


def file_text(path):
    t = _file_cache.get(path)
    if t is None:
        with open(path, 'rb') as f:
            t = f.read().decode('latin-1')
        _file_cache[path] = t
    return t


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    s = re.sub(r'//[^\n]*', ' ', s)
    s = '\n'.join(l for l in s.split('\n') if not l.strip().startswith('#'))
    return s


def prefix_text(cursor, stops):
    """Text immediately preceding ``cursor`` back to a stop char at paren depth 0."""
    loc = cursor.extent.start
    if loc.file is None:
        return ''
    text = file_text(loc.file.name)
    i = loc.offset - 1
    depth = 0
    while i >= 0:
        ch = text[i]
        if ch == ')':
            depth += 1
        elif ch == '(':
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and ch in stops:
            break
        elif ch == '/' and i > 0 and text[i - 1] == '*':
            # skip block comment backwards
            j = text.rfind('/*', 0, i)
            if j >= 0:
                i = j
        i -= 1
    return strip_comments(text[i + 1:loc.offset])


def parse_sal(s):
    """Parse SAL annotations from text -> list of (name, arg string or None)."""
    out = []
    pos = 0
    while True:
        m = SAL_RE.search(s, pos)
        if not m:
            break
        name = m.group(1)
        pos = m.end()
        arg = None
        if pos < len(s) and s[pos] == '(':
            depth = 0
            j = pos
            while j < len(s):
                if s[j] == '(':
                    depth += 1
                elif s[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            arg = s[pos + 1:j].strip()
            pos = j + 1
        out.append((name, arg))
    return out


def sal_flatten(sal):
    """Unwrap _Always_(x), _When_(c, x) etc."""
    out = []
    for name, arg in sal:
        if name in ('_Always_', '_Pre_', '_Post_') and arg:
            out.extend(sal_flatten(parse_sal(arg)))
        elif name == '_When_' and arg:
            continue
        else:
            out.append((name, arg))
    return out


# ---------------------------------------------------------------------------
# generator
# ---------------------------------------------------------------------------

class Record:
    def __init__(self, name, cursor, is_union, external=False):
        self.name = name
        self.cursor = cursor
        self.is_union = is_union
        self.external = external
        self.fields = []      # (name, ctype expr, bits or None)
        self.anonymous = []
        self.deps = set()     # by-value record dependencies
        self.smart_iface = {}
        self.smart_strings = []
        self.smart_arrays = {}
        self.smart_buffers = {}
        self.pack = None
        self.size = None
        self.align = None
        self.offsets = {}
        self.done = False


class Interface:
    def __init__(self, name, cursor, base, external=False):
        self.name = name
        self.cursor = cursor
        self.base = base
        self.external = external
        self.methods = []   # list of method cursors (own virtuals, vtable order)
        self.vtbl_start = 0
        self.iid = None


class Generator:
    def __init__(self, sdk_version=None, agility=None, packages=None):
        self.sdk, self.sdk_version = find_sdk(sdk_version)
        self.packages = dict(packages or {})
        if agility:
            self.packages['agility'] = (self.packages.get('agility', ('?', None))[0], agility)
        agility = self.packages.get('agility', (None, None))[1]
        self.package_dirs = [inc for name, _ in PACKAGES for v, inc in [self.packages.get(name, (None, None))] if inc]
        self.agility = agility
        self.agility_version = None
        if agility:
            m = re.search(r'#define\s+D3D12_SDK_VERSION\s+\(\s*(\d+)\s*\)', file_text(os.path.join(agility, 'd3d12.h')))
            self.agility_version = int(m.group(1)) if m else None
        self.msvc = find_msvc()
        ci.Config.set_library_file(find_llvm())
        llvm_root = os.path.dirname(os.path.dirname(find_llvm()))
        res = glob.glob(os.path.join(llvm_root, 'lib', 'clang', '*', 'include'))
        self.args = ['-x', 'c++', '-std=c++17', '--target=x86_64-pc-windows-msvc', '-fms-extensions',
                     '-fms-compatibility', '-fms-compatibility-version=19.44', '-DWIN32_LEAN_AND_MEAN',
                     '-DINITGUID', '-DDML_TARGET_VERSION_USE_LATEST', '-Wno-everything', '-ferror-limit=0',
                     '-I' + os.path.join(self.sdk, 'um'), '-I' + os.path.join(self.sdk, 'shared'),
                     '-I' + os.path.join(self.sdk, 'ucrt'), '-I' + self.msvc]
        if res:
            self.args.insert(0, '-isystem' + res[0])
        # package headers (Agility, DXC, DirectStorage, GameInput) shadow the Windows SDK ones
        for inc in reversed(self.package_dirs):
            self.args.insert(0, '-I' + inc)
        self.evaluate = None
        self.target_files = {h.lower() for h, _ in HEADERS}
        self.records = OrderedDict()     # name -> Record
        self.interfaces = OrderedDict()  # name -> Interface
        self.enums = OrderedDict()       # name -> (underlying ctype, [(name, value)])
        self.aliases = OrderedDict()     # name -> ctype expr
        self.fnptrs = OrderedDict()      # name -> (restype, [argtypes])
        self.functions = OrderedDict()   # name -> (cursor, dll)
        self.constants = OrderedDict()
        self.guids = OrderedDict()
        self.iids = {}
        self.record_by_hash = {}
        self.anon_counter = 0
        self.protos = []
        self.proto_index = {}
        self.warnings = []
        self.external_seen = set()

    # -- parsing --------------------------------------------------------
    def header_path(self, h):
        dirs = self.package_dirs + [os.path.join(self.sdk, 'um'), os.path.join(self.sdk, 'shared')]
        for d in dirs:
            p = os.path.join(d, h)
            if os.path.exists(p):
                return p
        return None

    def parse(self, extra='', strict=True):
        src = '#include <windows.h>\n#include <mmreg.h>\n'
        src += ''.join('#include <%s>\n' % h for h, _ in HEADERS if self.header_path(h))
        src += extra
        tu = ci.Index.create().parse('pydx12_gen.cpp', args=self.args, unsaved_files=[('pydx12_gen.cpp', src)],
                                     options=ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                                     ci.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
        fatal = [d for d in tu.diagnostics if d.severity >= 4]
        if fatal and strict:
            for d in fatal:
                print(d)
            sys.exit('fatal parse errors')
        return tu

    def is_target(self, cursor):
        f = cursor.location.file
        return f is not None and os.path.basename(f.name).lower() in self.target_files

    def header_of(self, cursor):
        f = cursor.location.file
        return os.path.basename(f.name).lower() if f else None

    def walk(self, cursor):
        for c in cursor.get_children():
            if c.kind in (CK.LINKAGE_SPEC, CK.NAMESPACE, CK.UNEXPOSED_DECL):
                yield from self.walk(c)
            else:
                yield c

    def run(self):
        t = time.time()
        tu = self.parse()
        self.evaluate = Evaluator()
        print('parsed in %.1fs' % (time.time() - t))
        self.collect_uuids()
        macro_names = []
        typedef_names = {}
        for c in self.walk(tu.cursor):
            if c.kind == CK.TYPEDEF_DECL:
                under = c.underlying_typedef_type.get_declaration()
                if under.kind in (CK.STRUCT_DECL, CK.UNION_DECL, CK.ENUM_DECL, CK.CLASS_DECL):
                    typedef_names.setdefault(under.hash, c.spelling)
                    d = under.get_definition()
                    if d is not None:
                        typedef_names.setdefault(d.hash, c.spelling)
        self.typedef_names = typedef_names
        for c in self.walk(tu.cursor):
            if c.kind == CK.MACRO_DEFINITION:
                fname = os.path.basename(c.location.file.name).lower() if c.location.file else ''
                if self.is_target(c) or c.spelling.startswith(EXTERNAL_MACROS.get(fname, ())):
                    if not c.spelling.startswith('_') and not self.is_function_like(c):
                        toks = list(c.get_tokens())
                        if len(toks) > 1:
                            macro_names.append(c.spelling)
                continue
            if not self.is_target(c):
                continue
            k = c.kind
            if k in (CK.STRUCT_DECL, CK.UNION_DECL, CK.CLASS_DECL) and c.is_definition():
                if self.is_interface(c):
                    self.add_interface(c)
                else:
                    self.add_record(c)
            elif k == CK.ENUM_DECL and c.is_definition():
                self.add_enum(c)
            elif k == CK.TYPEDEF_DECL:
                self.add_typedef(c)
            elif k == CK.FUNCTION_DECL and not c.is_definition() and not self.is_inline(c):
                if (c.spelling.isidentifier() and not c.spelling.startswith('_') and c.spelling not in self.functions
                        and c.linkage == ci.LinkageKind.EXTERNAL and not c.spelling.startswith('operator')):
                    self.functions[c.spelling] = (c, HEADER_DLL.get(self.header_of(c)))
            elif k == CK.VAR_DECL:
                self.add_guid_var(c)
        # resolve alias expressions early (may pull in external records)
        self.alias_exprs = OrderedDict((n, self.ctype(u)) for n, u in self.aliases.items())
        for name, ft in self.fnptrs.items():
            self.ctype(ft.get_result(), param=True)
            for a in ft.argument_types():
                self.ctype(a, param=True)
        # touch every method / function signature so all referenced records exist
        for iface in list(self.interfaces.values()):
            for m in iface.methods:
                self.ctype(m.result_type, param=True)
                for p in m.get_children():
                    if p.kind == CK.PARM_DECL:
                        self.ctype(p.type, param=True)
        for c, _ in list(self.functions.values()):
            self.ctype(c.result_type, param=True)
            for p in c.get_children():
                if p.kind == CK.PARM_DECL:
                    self.ctype(p.type, param=True)
        # resolve fields of target records (pulls in external records as needed)
        for r in list(self.records.values()):
            self.fill_record(r)
        while True:
            pending = [r for r in self.records.values() if not r.done]
            if not pending:
                break
            for r in pending:
                self.fill_record(r)
        for i in self.interfaces.values():
            self.prepare_interface(i)
        self.eval_macros(macro_names)
        print('records=%d interfaces=%d enums=%d functions=%d constants=%d guids=%d' % (
            len(self.records), len(self.interfaces), len(self.enums), len(self.functions),
            len(self.constants), len(self.guids)))

    def is_inline(self, c):
        """Header-only (inline) functions are not DLL exports."""
        toks = [t.spelling for t in c.get_tokens()][:12]
        if any(t in ('inline', '__inline', '__forceinline', 'FORCEINLINE', 'static') for t in toks):
            return True
        return prefix_text(c, ';}{').strip().split()[-1:] in (['inline'], ['__inline'], ['FORCEINLINE'], ['__forceinline'])

    def is_function_like(self, c):
        try:
            return c.is_macro_function_like()
        except AttributeError:  # pragma: no cover
            toks = list(c.get_tokens())
            return len(toks) > 1 and toks[1].spelling == '(' and toks[1].extent.start.offset == toks[0].extent.end.offset

    def collect_uuids(self):
        pats = [
            r'MIDL_INTERFACE\(\s*"([0-9a-fA-F-]{36})"\s*\)\s*(\w+)',
            r'CROSS_PLATFORM_UUIDOF\(\s*(\w+)\s*,\s*"([0-9a-fA-F-]{36})"\s*\)',
            r'DECLARE_INTERFACE_IID_\(\s*(\w+)\s*,\s*\w+\s*,\s*"([0-9a-fA-F-]{36})"\s*\)',
            r'(?:DX_DECLARE_INTERFACE|DML_DECLARE_INTERFACE|DECLSPEC_UUID|__declspec\(uuid)\(\s*"([0-9a-fA-F-]{36})"\s*\)\)?\s*(?:DECLSPEC_NOVTABLE\s*)?(\w+)',
        ]
        for h, _ in HEADERS:
            for p in [self.header_path(h)]:
                if p:
                    text = file_text(p)
                    for i, pat in enumerate(pats):
                        for m in re.finditer(pat, text):
                            if i in (1, 2):
                                name, u = m.group(1), m.group(2)
                            else:
                                u, name = m.group(1), m.group(2)
                            self.iids.setdefault(name, u)

    def add_guid_var(self, c):
        ct = c.type.get_canonical()
        if ct.kind in INT_KINDS and ct.is_const_qualified() and c.spelling.isidentifier():
            # C++ constants such as `const HRESULT GAMEINPUT_E_READING_NOT_FOUND = ...;`
            v = self.evaluate(c)
            if isinstance(v, int):
                bits = ct.get_size() * 8
                if ct.kind in (TK.INT, TK.LONG, TK.SHORT, TK.LONGLONG) and (1 << (bits - 1)) <= v < (1 << bits):
                    v -= 1 << bits
                self.constants.setdefault(c.spelling, v)
            return
        t = c.type.spelling
        if 'GUID' not in t and 'IID' not in t and 'CLSID' not in t:
            return
        toks = [x.spelling for x in c.get_tokens()]
        if not toks and c.location.file is not None:
            # declared through a macro (DEFINE_GUID): read the invocation from the source
            text = file_text(c.location.file.name)
            m = re.compile(r'\w*GUID\w*\s*\(\s*%s\s*,([^)]*)\)' % re.escape(c.spelling)).search(text, max(0, c.location.offset - 200))
            if not m or m.start() > c.location.offset + 200:
                return
            toks = ['DEFINE_GUID', '(', c.spelling] + [x.strip() for x in m.group(1).split(',')]
        if '=' in toks:
            body = toks[toks.index('=') + 1:]
        elif toks[:1] in (['DEFINE_GUID'], ['DEFINE_GUID_']) or (toks and toks[0].startswith('DEFINE_') and 'GUID' in toks[0]):
            body = toks[3:]
        else:
            return
        nums = []
        for x in body:
            if re.match(r'^(0[xX][0-9a-fA-F]+|\d+)[uUlL]*$', x):
                nums.append(int(re.sub(r'[uUlL]+$', '', x), 0))
        if len(nums) == 11:
            self.guids[c.spelling] = nums
            if c.spelling.startswith('IID_'):
                self.iids.setdefault(c.spelling[4:], '%08x-%04x-%04x-%02x%02x-%s' % (
                    nums[0], nums[1], nums[2], nums[3], nums[4], ''.join('%02x' % b for b in nums[5:])))

    def is_interface(self, c):
        for ch in c.get_children():
            if ch.kind == CK.CXX_BASE_SPECIFIER:
                return True
            if ch.kind == CK.CXX_METHOD and ch.is_virtual_method():
                return True
        return False

    def record_name(self, c):
        name = c.spelling
        if not name or c.is_anonymous() or 'unnamed' in name or 'anonymous' in name:
            name = self.typedef_names.get(c.hash)
        elif c.kind != CK.ENUM_DECL:
            # typedef struct _FOO {...} FOO;  -> expose FOO
            td = self.typedef_names.get(c.hash) or self.typedef_names.get(c.get_definition().hash if c.get_definition() else None)
            if td and td != name and (name.startswith('_') or name.startswith('t')):
                name = td
        return name

    # -- enums / typedefs ---------------------------------------------
    def add_enum(self, c):
        name = self.record_name(c)
        under = INT_KINDS.get(c.enum_type.get_canonical().kind, 'c_int')
        values = [(e.spelling, e.enum_value) for e in c.get_children() if e.kind == CK.ENUM_CONSTANT_DECL]
        if c.is_scoped_enum():
            values = [('%s_%s' % (name, v), x) for v, x in values]
        if not name:
            name = '_anon_enum_%d' % len(self.enums)
        self.enums[name] = (under, values)

    def add_typedef(self, c):
        name = c.spelling
        if name in self.records or name in self.interfaces or name in self.enums:
            return
        u = c.underlying_typedef_type
        decl = u.get_declaration()
        if decl.kind in (CK.STRUCT_DECL, CK.UNION_DECL, CK.CLASS_DECL, CK.ENUM_DECL):
            target = self.record_name(decl) or decl.spelling
            if target == name:
                return
        canon = u.get_canonical()
        if canon.kind == TK.POINTER and canon.get_pointee().get_canonical().kind in (TK.FUNCTIONPROTO, TK.FUNCTIONNOPROTO):
            self.fnptrs[name] = canon.get_pointee().get_canonical()
            return
        if canon.kind in (TK.FUNCTIONPROTO,):
            return
        self.aliases[name] = u

    # -- records --------------------------------------------------------
    def add_record(self, c, name=None, external=False):
        name = name or self.record_name(c)
        if not name:
            return None
        if name in self.records:
            return self.records[name]
        r = Record(name, c, c.kind == CK.UNION_DECL, external)
        self.records[name] = r
        self.record_by_hash[c.hash] = r
        return r

    def anon_name(self, parent, c, field):
        self.anon_counter += 1
        base = parent.name.lstrip('_')
        return '_%s_%s' % (base, field or ('u%d' % self.anon_counter) if c.kind == CK.UNION_DECL else (field or 's%d' % self.anon_counter))

    def fill_record(self, r):
        if r.done:
            return
        r.done = True
        c = r.cursor
        t = c.type
        r.size = t.get_size()
        r.align = t.get_align()
        children = list(c.get_children())
        pending_anon = {}
        idx = 0
        max_align = 1
        for ch in children:
            if ch.kind in (CK.STRUCT_DECL, CK.UNION_DECL) and ch.is_definition():
                if ch.is_anonymous() or not ch.spelling or '(' in ch.type.spelling:
                    # anonymous member (unnamed type); either anonymous union or type of a following field
                    pending_anon[ch.hash] = ch
                    is_field_type = any(f.kind == CK.FIELD_DECL and f.type.get_declaration().hash == ch.hash
                                        for f in children)
                    if not is_field_type:
                        nm = '_%s_%s%d' % (r.name.lstrip('_'), 'u' if ch.kind == CK.UNION_DECL else 's', idx)
                        sub = self.add_record(ch, nm, r.external)
                        self.fill_record(sub)
                        fname = '_%s%d' % ('u' if ch.kind == CK.UNION_DECL else 's', idx)
                        idx += 1
                        r.fields.append((fname, nm, None))
                        r.anonymous.append(fname)
                        r.deps.add(nm)
                        max_align = max(max_align, ch.type.get_align())
                        off = self.anon_offset(c, ch)
                        if off is not None:
                            r.offsets[fname] = off
                else:
                    nested = self.add_record(ch, ch.spelling, r.external)
                    if nested:
                        self.fill_record(nested)
                continue
            if ch.kind != CK.FIELD_DECL:
                continue
            fname = ch.spelling
            ft = ch.type
            decl = ft.get_canonical()
            # find anonymous record for this field
            base_decl = self.strip_arrays(decl).get_declaration()
            if base_decl.hash in pending_anon and self.strip_arrays(decl).kind == TK.RECORD:
                nm = '_%s_%s' % (r.name.lstrip('_'), fname)
                sub = self.add_record(base_decl, nm, r.external)
                self.fill_record(sub)
            expr = self.ctype(ft, owner=r)
            sd = self.strip_arrays(decl)
            if sd.kind == TK.RECORD:
                dep = self.record_by_hash.get(sd.get_declaration().hash)
                if dep is not None:
                    r.deps.add(dep.name)
            bits = ch.get_bitfield_width() if ch.is_bitfield() else None
            r.fields.append((fname, expr, bits))
            off = t.get_offset(fname)
            if off is not None and off >= 0:
                r.offsets[fname] = off // 8 if not bits else off
            max_align = max(max_align, max(1, ft.get_align()))
            self.field_smarts(r, ch, ft, children)
        if r.align and r.align > 0 and r.align < max_align:
            r.pack = r.align

    def anon_offset(self, parent, anon):
        # offset of first field of anonymous member
        for f in anon.get_children():
            if f.kind == CK.FIELD_DECL:
                o = parent.type.get_offset(f.spelling)
                if o is not None and o >= 0:
                    return o // 8
                return None
        return None

    def strip_arrays(self, t):
        while t.kind in (TK.CONSTANTARRAY, TK.INCOMPLETEARRAY):
            t = t.element_type.get_canonical()
        return t

    def size_sibling(self, names):
        """Pick the byte-size field among siblings of an unannotated data pointer."""
        for pat in (r'(Bytes|SizeInBytes|ByteSize|ByteWidth)$', r'Size$', r'Length$'):
            cand = [n for n in names if re.search(pat, n)]
            if len(cand) == 1:
                return cand[0]
            if cand:
                return None
        return None

    def field_smarts(self, r, ch, ft, siblings):
        canon = ft.get_canonical()
        if canon.kind != TK.POINTER:
            return
        pointee = canon.get_pointee()
        pc = pointee.get_canonical()
        sal = sal_flatten(parse_sal(prefix_text(ch, ';{')))
        fname = ch.spelling
        names = {s.spelling for s in siblings if s.kind == CK.FIELD_DECL}
        # interface pointer
        iname = self.interface_of(pointee)
        if iname:
            r.smart_iface[fname] = iname
            return
        if pc.kind in (TK.CHAR_S, TK.SCHAR) and pc.is_const_qualified():
            r.smart_strings.append(fname)
            return
        count = None
        bytes_count = None
        for name, arg in sal:
            if arg is None:
                continue
            a = arg.split(',')[0].strip()
            if (name.startswith('_Field_size_bytes') or name.startswith('_In_reads_bytes')) and a in names:
                bytes_count = a
            elif (name.startswith('_Field_size') or name.startswith('_In_reads')) and a in names:
                count = a
        if pc.kind in (TK.UCHAR, TK.CHAR_U) and not (bytes_count or count):
            cand = self.size_sibling(names)
            if cand:
                r.smart_buffers[fname] = cand
            return
        if pc.kind == TK.VOID:
            if bytes_count or count:
                r.smart_buffers[fname] = bytes_count or count
            else:
                # unannotated void* with a single size-like sibling (D3D12_SHADER_BYTECODE, DxcBuffer, ...)
                cand = self.size_sibling(names)
                if cand and re.search(r'(Data|Bytecode|Blob|Buffer|Ptr|Bytes|Code|Source)$', fname):
                    r.smart_buffers[fname] = cand
            return
        if count or bytes_count:
            elem = self.ctype(pointee, owner=r, byvalue=False)
            if pc.kind == TK.POINTER and self.interface_of(pc.get_pointee()):
                elem = repr(self.interface_of(pc.get_pointee()))
            elif pc.kind == TK.POINTER and pc.get_pointee().get_canonical().kind in (TK.CHAR_S, TK.SCHAR):
                elem = 'c_char_p'
            elif pc.kind == TK.POINTER and pc.get_pointee().get_canonical().kind in (TK.WCHAR, TK.CHAR16):
                elem = 'c_wchar_p'
            elif pc.kind == TK.POINTER:
                return
            if bytes_count and not count:
                if pc.kind in (TK.UCHAR, TK.CHAR_U, TK.CHAR_S, TK.SCHAR) or elem in ('c_ubyte', 'c_byte'):
                    r.smart_buffers[fname] = bytes_count
                return
            r.smart_arrays[fname] = (elem, count)

    def interface_of(self, t):
        """If t (pointee) is an interface type return its name."""
        tc = t.get_canonical()
        if tc.kind != TK.RECORD:
            return None
        d = tc.get_declaration()
        name = self.record_name(d) or d.spelling
        if name in self.interfaces:
            return name
        dd = d.get_definition()
        if dd is not None and self.is_interface(dd):
            if name not in self.interfaces:
                self.add_interface(dd, external=not self.is_target(dd))
            return name
        if name in ('IUnknown',):
            return name
        # forward-declared only interface (e.g. typedef interface X X;)
        if dd is None and name.startswith('I') and name[1:2].isupper():
            self.add_opaque_interface(name)
            return name
        return None

    def add_opaque_interface(self, name):
        if name not in self.interfaces:
            i = Interface(name, None, 'IUnknown', external=True)
            self.interfaces[name] = i

    # -- interfaces -----------------------------------------------------
    def add_interface(self, c, external=False):
        name = c.spelling
        if name in self.interfaces and self.interfaces[name].cursor is not None:
            return
        base = None
        for ch in c.get_children():
            if ch.kind == CK.CXX_BASE_SPECIFIER:
                base = ch.type.get_canonical().get_declaration().spelling
                bdef = ch.type.get_canonical().get_declaration().get_definition()
                if base != 'IUnknown' and base not in self.interfaces and bdef is not None:
                    self.add_interface(bdef, external=not self.is_target(bdef))
        if external:
            # interfaces from outside the DirectX headers are emitted as opaque IUnknown wrappers
            self.add_opaque_interface(name)
            return
        i = Interface(name, c, base, external)
        self.interfaces[name] = i
        inherited = set(self.all_method_names(base))
        virt = [m for m in c.get_children() if m.kind == CK.CXX_METHOD and m.is_virtual_method()
                and m.spelling not in inherited]
        # MSVC: overloaded virtuals are grouped and emitted in reverse declaration order
        groups = OrderedDict()
        for m in virt:
            groups.setdefault(m.spelling, []).append(m)
        ordered = []
        for nm, ms in groups.items():
            if len(ms) > 1:
                self.warnings.append('%s::%s is overloaded (%d), using MSVC reverse order' % (name, nm, len(ms)))
            ordered.extend(reversed(ms))
        i.methods = ordered
        if name == 'IUnknown':
            i.methods = []

    def all_method_names(self, name, seen=None):
        if not name:
            return []
        if name == 'IUnknown':
            return ['QueryInterface', 'AddRef', 'Release']
        i = self.interfaces.get(name)
        seen = seen or set()
        if i is None or name in seen:
            return []
        seen.add(name)
        return self.all_method_names(i.base, seen) + [m.spelling for m in i.methods]

    def vtbl_size(self, name):
        if name in (None, ''):
            return 0
        if name == 'IUnknown':
            return 3
        i = self.interfaces.get(name)
        if i is None:
            return 0
        return self.vtbl_size(i.base) + len(i.methods)

    def prepare_interface(self, i):
        i.vtbl_start = self.vtbl_size(i.base)
        i.iid = self.iids.get(i.name)

    # -- type mapping ---------------------------------------------------
    def ctype(self, t, owner=None, byvalue=True, param=False):
        """Return a Python expression for the ctypes type of clang type t."""
        # keep typedef names declared in target headers
        if t.kind == TK.ELABORATED:
            t = t.get_named_type()
        if t.kind == TK.TYPEDEF:
            decl = t.get_declaration()
            name = decl.spelling
            if name in ('LPCSTR', 'PCSTR', 'LPSTR', 'PSTR'):
                return 'c_char_p'
            if name in ('LPCWSTR', 'PCWSTR', 'LPWSTR', 'PWSTR', 'LPOLESTR', 'LPCOLESTR', 'BSTR'):
                return 'c_wchar_p'
            if name in ('HRESULT',):
                return 'HRESULT'
            if name in ('BOOL', 'WINBOOL'):
                return 'BOOL'
            if name == 'SIZE_T' or name == 'size_t':
                return 'c_size_t'
            if name in ('GUID', 'IID', 'CLSID', 'UUID'):
                return 'GUID'
            if name in ('REFIID', 'REFGUID', 'REFCLSID'):
                return 'POINTER(GUID)'
            if self.is_target(decl) and (name in self.aliases or name in self.enums or name in self.records
                                         or name in self.fnptrs or name in self.interfaces):
                if name in self.records and byvalue and owner is not None:
                    owner.deps.add(name)
                if name in self.fnptrs:
                    return 'c_void_p'
                if name in self.interfaces:
                    return 'c_void_p'
                return name
            return self.ctype(t.get_canonical(), owner, byvalue, param)
        c = t.get_canonical()
        k = c.kind
        if k in INT_KINDS:
            return INT_KINDS[k]
        if k == TK.VOID:
            return 'None'
        if k == TK.ENUM:
            d = c.get_declaration()
            nm = self.record_name(d) or d.spelling
            if nm in self.enums:
                return nm
            return INT_KINDS.get(d.enum_type.get_canonical().kind, 'c_int')
        if k in (TK.POINTER, TK.LVALUEREFERENCE, TK.RVALUEREFERENCE):
            p = c.get_pointee()
            pc = p.get_canonical()
            if pc.kind == TK.VOID:
                return 'c_void_p'
            if pc.kind in (TK.FUNCTIONPROTO, TK.FUNCTIONNOPROTO):
                return 'c_void_p'
            if pc.kind in (TK.CHAR_S, TK.SCHAR):
                return 'c_char_p'
            if pc.kind in (TK.WCHAR, TK.CHAR16):
                return 'c_wchar_p'
            if pc.kind == TK.RECORD:
                d = pc.get_declaration()
                nm = self.record_name(d) or d.spelling
                if nm.endswith('__') or nm.startswith('_') and nm.endswith('_HANDLE') or d.get_definition() is None and not (nm.startswith('I') and nm[1:2].isupper()):
                    return 'c_void_p'
                if self.interface_of(p):
                    return 'c_void_p'
                inner = self.ctype(p, owner, byvalue=False, param=param)
                return 'POINTER(%s)' % inner
            if pc.kind == TK.POINTER:
                if param:
                    return 'c_void_p'
                inner = pc.get_pointee().get_canonical().kind
                if inner in (TK.CHAR_S, TK.SCHAR):
                    return 'POINTER(c_char_p)'
                if inner in (TK.WCHAR, TK.CHAR16):
                    return 'POINTER(c_wchar_p)'
                return 'POINTER(c_void_p)'
            inner = self.ctype(p, owner, byvalue=False, param=param)
            if inner == 'None':
                return 'c_void_p'
            return 'POINTER(%s)' % inner
        if k == TK.CONSTANTARRAY:
            inner = self.ctype(c.element_type, owner, byvalue, param)
            if param:
                return 'POINTER(%s)' % inner
            return '(%s * %d)' % (inner, c.element_count)
        if k == TK.INCOMPLETEARRAY:
            inner = self.ctype(c.element_type, owner, byvalue, param)
            return 'POINTER(%s)' % inner if param else '(%s * 0)' % inner
        if k == TK.RECORD:
            d = c.get_declaration()
            nm = self.record_name(d) or d.spelling
            r = self.record_by_hash.get(d.hash) or self.records.get(nm)
            if r is None:
                dd = d.get_definition()
                if dd is None:
                    return 'c_void_p'
                if self.is_interface(dd):
                    self.interface_of(c)
                    return 'c_void_p'
                if not nm or '(' in nm:
                    return 'c_void_p'
                r = self.add_record(dd, nm, external=not self.is_target(dd))
            if byvalue and owner is not None:
                owner.deps.add(r.name)
            if nm == 'GUID' or r.name in ('_GUID', 'GUID'):
                return 'GUID'
            return r.name
        if k in (TK.FUNCTIONPROTO, TK.FUNCTIONNOPROTO):
            return 'c_void_p'
        if k == TK.MEMBERPOINTER:
            return 'c_void_p'
        self.warnings.append('unmapped type %s (%s)' % (t.spelling, k))
        return 'c_void_p'

    # -- macros ---------------------------------------------------------
    def eval_macros(self, names):
        names = [n for n in OrderedDict.fromkeys(names) if n not in self.enums]
        extra = ''.join('static const auto __pydx12_m%d = (%s);\n' % (i, n) for i, n in enumerate(names))
        tu = self.parse(extra, strict=False)
        idx = {}
        for c in tu.cursor.get_children():
            if c.kind == CK.VAR_DECL and c.spelling.startswith('__pydx12_m'):
                idx[int(c.spelling[10:])] = c
        enum_consts = {v for _, (_, vals) in self.enums.items() for v, _ in vals}
        for i, n in enumerate(names):
            c = idx.get(i)
            if c is None or n in enum_consts:
                continue
            v = self.evaluate(c)
            if v is None:
                continue
            if isinstance(v, int) and c.type.get_canonical().kind in (TK.INT, TK.LONG, TK.SHORT, TK.LONGLONG):
                bits = c.type.get_size() * 8
                if v >= 1 << (bits - 1) and v < 1 << bits:
                    v -= 1 << bits
            self.constants[n] = v

    # -- emission -------------------------------------------------------
    def proto(self, restype, argtypes):
        key = (restype, tuple(argtypes))
        k = self.proto_index.get(key)
        if k is None:
            k = len(self.protos)
            self.protos.append(key)
            self.proto_index[key] = k
        return k

    def topo_records(self):
        order = []
        state = {}

        def visit(n):
            if state.get(n) == 2:
                return
            if state.get(n) == 1:
                return
            state[n] = 1
            r = self.records.get(n)
            if r:
                for d in sorted(r.deps):
                    visit(d)
                order.append(r)
            state[n] = 2
        for n in self.records:
            visit(n)
        return order

    def emit(self):
        out = []
        w = out.append
        w('# Generated by tools/generate.py from Windows SDK %s - DO NOT EDIT' % self.sdk_version)
        w('# flake8: noqa')
        w('from ctypes import (POINTER, WINFUNCTYPE, Structure, Union, byref, cast, sizeof, c_void_p, c_char_p, c_wchar_p,')
        w('                    c_bool, c_char, c_wchar, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint, c_long, c_ulong,')
        w('                    c_int64, c_uint64, c_uint32, c_float, c_double, c_size_t, c_ssize_t)')
        w('from . import _core')
        w('from ._core import (GUID, Struct, Union_, ComInterface, IUnknown, DXError, _check, _owned, _borrowed, _riid,')
        w('                    _str, _ptr, _buf, _arr, _seqlen, _smart, _Func, BlobMixin, _IFaceRef)')
        w('')
        w('HRESULT = c_long')
        w('BOOL = c_int')
        w('WINDOWS_SDK_VERSION = %r' % self.sdk_version)
        w('AGILITY_SDK_VERSION = %r  # D3D12_SDK_VERSION of the headers the bindings were generated from' % self.agility_version)
        w('PACKAGE_VERSIONS = %r  # NuGet packages whose headers were used' % {k: v for k, (v, _) in sorted(self.packages.items())})
        w('')
        # enums
        w('# ---- enums ----')
        for name, (under, values) in self.enums.items():
            if not name.startswith('_anon'):
                w('%s = %s' % (name, under))
            for vn, vv in values:
                w('%s = %d' % (vn, vv))
        w('')
        w('# ---- constants ----')
        for n, v in self.constants.items():
            if n in self.aliases or n in self.records or n in self.interfaces:
                continue
            w('%s = %r' % (n, v))
        w('')
        w('# ---- GUIDs ----')
        for n, nums in self.guids.items():
            w('%s = GUID(%s)' % (n, ', '.join('0x%X' % x for x in nums)))
        w('')
        # aliases: primitive ones first; record/enum aliases later
        w('# ---- record declarations ----')
        records = self.topo_records()
        for r in records:
            if r.name == 'GUID' or r.name == '_GUID':
                continue
            w('class %s(%s): pass' % (r.name, 'Union_' if r.is_union else 'Struct'))
        w('')
        w('# ---- type aliases ----')
        alias_lines = []
        for name, u in self.aliases.items():
            if name in self.records or name in self.enums or name in ('GUID', 'IID', 'CLSID'):
                continue
            if self.interface_of(u):
                continue
            expr = self.alias_exprs[name]
            if expr == name:
                continue
            alias_lines.append((name, expr))
        emitted = set()
        # aliases may reference other aliases; emit in dependency order
        names_alias = dict(alias_lines)
        def emit_alias(n, stack=()):
            if n in emitted or n in stack:
                return
            expr = names_alias[n]
            for tok in re.findall(r'[A-Za-z_]\w*', expr):
                if tok in names_alias and tok != n:
                    emit_alias(tok, stack + (n,))
            w('%s = %s' % (n, expr))
            emitted.add(n)
        for n, _ in alias_lines:
            emit_alias(n)
        w('')
        # interfaces
        w('# ---- interfaces ----')
        for i in self.iface_order():
            self.emit_interface(i, w)
        w('')
        for name, u in self.aliases.items():
            iname = self.interface_of(u)
            if iname and iname != name and name not in self.interfaces:
                w('%s = %s' % (name, iname))
        w('')
        w('# ---- record layouts ----')
        for r in records:
            if r.name in ('GUID', '_GUID'):
                continue
            if r.pack:
                w('%s._pack_ = %d' % (r.name, r.pack))
                w('%s._layout_ = "ms"' % r.name)
            if r.anonymous:
                w('%s._anonymous_ = %r' % (r.name, tuple(r.anonymous)))
            fields = []
            for fname, expr, bits in r.fields:
                if fname in r.smart_iface and expr == 'c_void_p':
                    expr = 'POINTER(_IFaceRef)'
                elif fname in r.smart_buffers and expr == 'c_void_p':
                    expr = 'POINTER(c_ubyte)'
                if bits is not None:
                    fields.append('(%r, %s, %d)' % (fname, expr, bits))
                else:
                    fields.append('(%r, %s)' % (fname, expr))
            w('%s._fields_ = [%s]' % (r.name, ', '.join(fields)))
        # smart properties go last: anonymous members must keep raw descriptors
        # while their parents are laid out, and parents re-expose them
        for r in records:
            if r.name in ('GUID', '_GUID'):
                continue
            self.merge_anonymous_smarts(r)
            if r.smart_iface or r.smart_strings or r.smart_arrays or r.smart_buffers:
                parts = []
                if r.smart_iface:
                    parts.append('iface=%r' % r.smart_iface)
                if r.smart_strings:
                    parts.append('strings=%r' % (r.smart_strings,))
                if r.smart_arrays:
                    parts.append('arrays={%s}' % ', '.join('%r: (%s, %r)' % (k, e, c) for k, (e, c) in r.smart_arrays.items()))
                if r.smart_buffers:
                    parts.append('buffers=%r' % r.smart_buffers)
                w('_smart(%s, %s)' % (r.name, ', '.join(parts)))
        w('')
        # functions
        w('# ---- functions ----')
        for name, (c, dll) in self.functions.items():
            if dll is None:
                continue
            dll = FUNCTION_DLL.get(name, dll)
            self.emit_function(name, c, dll, w)
        w('')
        w('# ---- callback prototypes ----')
        for name, ft in self.fnptrs.items():
            res = self.ctype(ft.get_result(), param=True)
            args = [self.ctype(a, param=True) for a in ft.argument_types()]
            w('%s = WINFUNCTYPE(%s)' % (name, ', '.join([res] + args)))
        w('')
        w('# ---- method prototypes ----')
        w('_P = [')
        for res, args in self.protos:
            w('    WINFUNCTYPE(%s),' % ', '.join([res, 'c_void_p'] + list(args)))
        w(']')
        w('_core._protos = _P')
        w('')
        w('_core._register_hresults({%s})' % ', '.join(
            '%r: %s' % (n, n) for n, v in self.constants.items()
            if isinstance(v, int) and (n.startswith(('DXGI_ERROR_', 'DXGI_STATUS_', 'D3D12_ERROR_', 'E_', 'DXGI_DDI_ERR_', 'D3D10_ERROR', 'D3D11_ERROR', 'XAUDIO2_E_', 'XAPO_E_', 'DXCORE_ERROR_', 'GAMEINPUT_E_', 'E_DSTORAGE_', 'DSTORAGE_E_', 'DXC_E_')) or n in ('S_OK', 'S_FALSE'))))
        w('_core._register_iids()')
        w('')
        src = '\n'.join(out) + '\n'
        with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src)
        print('wrote %s (%d lines, %d protos)' % (OUT, len(out), len(self.protos)))
        self.emit_layout_data(records)

    def merge_anonymous_smarts(self, r):
        for fname, expr, bits in r.fields:
            if fname in r.anonymous:
                sub = self.records.get(expr)
                if sub is None:
                    continue
                self.merge_anonymous_smarts(sub)
                r.smart_iface.update(sub.smart_iface)
                r.smart_strings.extend(x for x in sub.smart_strings if x not in r.smart_strings)
                r.smart_arrays.update(sub.smart_arrays)
                r.smart_buffers.update(sub.smart_buffers)

    def emit_layout_data(self, records):
        lines = ['# Generated by tools/generate.py - expected struct layouts (from clang, MSVC x64 ABI)', 'LAYOUTS = {']
        for r in records:
            if r.name in ('GUID', '_GUID') or r.size is None or r.size < 0:
                continue
            offs = {k: v for k, v in r.offsets.items() if not any(f[0] == k and f[2] is not None for f in r.fields)}
            lines.append('    %r: (%d, %d, %r),' % (r.name, r.size, r.align, offs))
        lines.append('}')
        with open(LAYOUT_OUT, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')

    def iface_order(self):
        order = []
        seen = set()

        def visit(n):
            if n in seen or n == 'IUnknown' or n not in self.interfaces:
                return
            seen.add(n)
            i = self.interfaces[n]
            if i.base:
                visit(i.base)
            order.append(i)
        for n in self.interfaces:
            visit(n)
        return order

    def emit_interface(self, i, w):
        base = i.base or 'ComInterface'
        if base not in self.interfaces and base != 'IUnknown':
            base = 'IUnknown' if i.cursor is None else 'ComInterface'
        mixins = ''
        if i.name in ('ID3D10Blob', 'IDxcBlob'):
            mixins = 'BlobMixin, '
        w('')
        w('class %s(%s%s):' % (i.name, mixins, base))
        if i.cursor is not None and i.cursor.brief_comment:
            pass
        w('    __slots__ = ()')
        if i.iid:
            w("    _iid_ = GUID('%s')" % i.iid)
        if base == 'ComInterface':
            w('    _refcounted_ = False')
        vt = []
        idx = i.vtbl_start
        used = set()
        for m in i.methods:
            name = self.source_name(m)
            pyname = name
            if pyname in used:
                pyname = pyname + '_%d' % sum(1 for u in used if u.startswith(name))
            used.add(pyname)
            k = self.emit_method(i, m, pyname, idx, w)
            vt.append((pyname, k))
            idx += 1
        w('    _vt_ = %r' % (tuple(vt),))
        w('    _vtbl_size_ = %d' % idx)

    def source_name(self, cursor):
        """Name as written in the header: windows.h maps e.g. GetMessage -> GetMessageA."""
        name = cursor.spelling
        loc = cursor.location
        if loc.file is None or name[-1:] not in ('A', 'W'):
            return name
        text = file_text(loc.file.name)
        m = re.match(r'[A-Za-z_]\w*', text[loc.offset:loc.offset + 200])
        if m and m.group(0) != name and name == m.group(0) + name[-1]:
            return m.group(0)
        return name

    # -- parameter analysis ---------------------------------------------
    def analyze_params(self, cursor, qualname, is_method):
        params = [p for p in cursor.get_children() if p.kind == CK.PARM_DECL]
        infos = []
        names = []
        for n, p in enumerate(params):
            pname = p.spelling or 'arg%d' % n
            if keyword.iskeyword(pname) or pname in ('self', 'cls'):
                pname = pname + '_'
            names.append(pname)
            sal = sal_flatten(parse_sal(prefix_text(p, ',(')))
            infos.append({'cursor': p, 'name': pname, 'cname': p.spelling, 'type': p.type, 'sal': sal,
                          'kind': 'in', 'argtype': self.ctype(p.type, param=True), 'aux': None,
                          'cdefault': self.default_arg(p)})
        byname = {i['cname']: i for i in infos if i['cname']}
        for n, info in enumerate(infos):
            t = info['type'].get_canonical()
            sal = info['sal']
            salnames = [s[0] for s in sal]
            is_ptr = t.kind in (TK.POINTER, TK.LVALUEREFERENCE)
            pointee = t.get_pointee().get_canonical() if is_ptr else None
            out_ann = any(re.match(r'^_(COM_)?Out(ptr)?(_opt)?(_result_\w+?)?_$', s) or s.startswith('_Out_range_')
                          or s.startswith('_Outptr_result_') or s.startswith('_Outptr_opt_result_')
                          or s.startswith('_COM_Outptr_') for s in salnames)
            # riid + ppv pair
            tname = info['type'].spelling.replace('const ', '').strip()
            if tname in ('REFIID', 'IID &', 'const IID &', 'REFGUID') or (
                    t.kind == TK.LVALUEREFERENCE and pointee.spelling.endswith('GUID') and info['cname'].lower().startswith('riid')):
                if n + 1 < len(infos):
                    nxt = infos[n + 1]
                    nt = nxt['type'].get_canonical()
                    if nt.kind == TK.POINTER and nt.get_pointee().get_canonical().kind == TK.POINTER and \
                            nt.get_pointee().get_canonical().get_pointee().get_canonical().kind == TK.VOID:
                        info['kind'] = 'riid'
                        nxt['kind'] = 'ppv'
                        nxt['aux'] = n
                        continue
            if info['kind'] == 'ppv':
                continue
            if (is_ptr and not sal and not pointee.is_const_qualified() and pointee.kind == TK.RECORD
                    and n == len(infos) - 1 and cursor.spelling.startswith('Get')
                    and not self.interface_of(t.get_pointee())):
                # unannotated getter (d3d12shader.h): GetDesc(T *pDesc)
                out_ann = True
            if is_ptr and out_ann and not pointee.is_const_qualified():
                if pointee.kind == TK.POINTER:
                    inner = pointee.get_pointee()
                    iname = self.interface_of(inner)
                    if iname:
                        info['kind'] = 'out_iface'
                        info['aux'] = iname
                    elif inner.get_canonical().kind == TK.VOID:
                        info['kind'] = 'out_ptr'
                    else:
                        info['kind'] = 'out_ptr'
                    info['argtype'] = 'c_void_p'
                else:
                    info['kind'] = 'out'
                    info['aux'] = self.ctype(t.get_pointee(), byvalue=False)
                    if info['aux'] in ('None',):
                        info['kind'] = 'in'
                continue
            # output arrays sized by an integer input parameter: allocate and return them
            if is_ptr and pointee is not None and not pointee.is_const_qualified() and pointee.kind not in (TK.VOID, TK.POINTER):
                for name, arg in sal:
                    if arg and re.match(r'^_Out_writes(_opt)?_$', name):
                        cnt = arg.split(',')[0].strip()
                        c = byname.get(cnt)
                        if c is not None and c is not info and c['type'].get_canonical().kind in (
                                TK.UINT, TK.INT, TK.ULONG, TK.LONG, TK.ULONGLONG, TK.USHORT):
                            info['kind'] = 'out_array'
                            info['aux'] = c['name']
                            info['elem'] = self.ctype(t.get_pointee(), byvalue=False)
                        break
                if info['kind'] == 'out_array':
                    continue
            # input arrays
            for name, arg in sal:
                if arg and re.match(r'^_In_(opt_)?(reads|count|bytecount)', name):
                    cnt = arg.split(',')[0].strip()
                    is_bytes = 'bytes' in name or 'bytecount' in name
                    info['kind'] = 'in_bytes' if (is_bytes or (pointee is not None and pointee.kind == TK.VOID)) else 'in_array'
                    if cnt in byname and byname[cnt] is not info:
                        info['aux'] = byname[cnt]['name']
                    break
            if info['kind'] == 'in' and is_ptr and pointee is not None:
                iname = self.interface_of(t.get_pointee())
                if iname:
                    info['kind'] = 'in_iface'
                    info['aux'] = iname
                elif pointee.kind in (TK.CHAR_S, TK.SCHAR) and pointee.is_const_qualified():
                    info['kind'] = 'in_str'
            if info['kind'] in ('in_array', 'in_bytes') and pointee is None:
                info['kind'] = 'in'
                info['aux'] = None
            if info['kind'] == 'in_array':
                # element type
                if pointee.kind == TK.POINTER and self.interface_of(pointee.get_pointee()):
                    info['elem'] = repr(self.interface_of(pointee.get_pointee()))
                    info['argtype'] = 'c_void_p'
                elif pointee.kind == TK.VOID:
                    info['kind'] = 'in_bytes'
                else:
                    info['elem'] = self.ctype(t.get_pointee(), byvalue=False)
                    if info['elem'] in ('c_char_p', 'c_wchar_p'):
                        pass
            if info['kind'] == 'in_bytes':
                info['argtype'] = 'c_void_p'
        # derive counts
        for info in infos:
            if info['kind'] in ('in_array', 'in_bytes') and info['aux']:
                cnt = next(i for i in infos if i['name'] == info['aux'])
                ct = cnt['type'].get_canonical()
                if cnt['kind'] == 'in' and ct.kind in (TK.UINT, TK.INT, TK.ULONG, TK.LONG, TK.ULONGLONG, TK.LONGLONG, TK.USHORT):
                    cnt['kind'] = 'count'
                    cnt.setdefault('arrays', []).append(info['name'])
                    info['count_bytes'] = info['kind'] == 'in_bytes'
                else:
                    info['aux'] = None
        return infos

    def default_arg(self, p):
        toks = [t.spelling for t in p.get_tokens()]
        if '=' in toks:
            expr = ' '.join(toks[toks.index('=') + 1:])
        else:
            # X2DEFAULT(value) style defaults live after the parameter name in the source
            end = p.extent.end
            if end.file is None:
                return None
            text = file_text(end.file.name)
            m = re.match(r'\s*(?:X2DEFAULT\s*\(\s*([^()]*?)\s*\)|=\s*([^,()]+?))\s*[,)]', text[end.offset:end.offset + 200])
            if not m:
                return None
            expr = (m.group(1) or m.group(2)).strip()
        if expr in ('NULL', 'nullptr', '0') and p.type.get_canonical().kind == TK.POINTER:
            return 'None'
        if expr in ('TRUE', 'true'):
            return '1'
        if expr in ('FALSE', 'false'):
            return '0'
        m = re.match(r'^-?(0[xX][0-9a-fA-F]+|\d+(\.\d*)?)[uUlLfF]*$', expr.replace(' ', ''))
        if m:
            return expr.replace(' ', '').rstrip('uUlLfF') if not expr.startswith('0x') else expr.rstrip('uUlL')
        if re.match(r'^\w+$', expr):
            known = expr in self.constants or any(expr == v for _, (_, vals) in self.enums.items() for v, _ in vals)
            if known:
                return expr
            ct = p.type.get_canonical()
            if ct.kind == TK.ENUM:
                for e in ct.get_declaration().get_children():
                    if e.spelling == expr:
                        return str(e.enum_value)
            return None
        return None

    def riid_default(self, qualname, iface_name, method, ppv_name):
        for key in (qualname,):
            if key in RIID_DEFAULTS:
                return RIID_DEFAULTS[key]
        # walk base interfaces for inherited defaults
        if iface_name:
            i = self.interfaces.get(iface_name)
            seen = set()
            while i is not None and i.name not in seen:
                seen.add(i.name)
                k = '%s.%s' % (i.name, method)
                if k in RIID_DEFAULTS:
                    return RIID_DEFAULTS[k]
                i = self.interfaces.get(i.base)
        # heuristic: Create<X> / Get<X> -> I<prefix><X>
        m = re.match(r'^(Create|Get|Open|Load|Enum)(\w+?)\d*$', method)
        if m:
            rest = m.group(2)
            prefixes = []
            if iface_name:
                mm = re.match(r'^(ID3D12Video|ID3D12|IDXGI|IDxc|IDML|IDXCore|IXAudio2|IDStorage|IGameInput|ID3D)', iface_name)
                if mm:
                    prefixes.append(mm.group(1))
            prefixes += ['ID3D12', 'IDXGI']
            for p in prefixes:
                if p + rest in self.interfaces:
                    return p + rest
        return None

    def emit_signature(self, infos, qualname):
        """Return (python params list, preamble lines, call args, post lines, returns)."""
        defaults = PARAM_DEFAULTS.get(qualname, {})
        sig = []
        kwonly = []
        pre = []
        call = []
        outs = []
        post = []
        error_blob = None
        for info in infos:
            k = info['kind']
            n = info['name']
            if k == 'count':
                kwonly.append('%s=None' % n)
                arrs = info['arrays']
                pre.append('if %s is None: %s = %s' % (n, n, ' or '.join(
                    ('_seqlen(%s)' % a) if not next(i for i in infos if i['name'] == a).get('count_bytes') else
                    ('_%s_n' % a) for a in arrs)))
                call.append(n)
            elif k == 'riid':
                ppv = next(i for i in infos if i.get('aux') == infos.index(info) and i['kind'] == 'ppv')
                sig.append([n, repr(info['default']) if info.get('default') else None])
                pre.append('_%s_g, _%s_c = _riid(%s)' % (n, n, n))
                call.append('byref(_%s_g)' % n)
                ppv['riid'] = n
            elif k == 'ppv':
                pre.append('%s = c_void_p()' % n)
                call.append('byref(%s)' % n)
                outs.append('_owned(_%s_c, %s)' % (info['riid'], n))
            elif k == 'out_iface':
                pre.append('%s = c_void_p()' % n)
                call.append('byref(%s)' % n)
                if re.search(r'error', info['cname'], re.I) and len([i for i in infos if i['kind'] in ('out_iface', 'ppv', 'out', 'out_ptr')]) > 1:
                    error_blob = n
                    continue
                outs.append('_owned(%r, %s)' % (info['aux'], n))
            elif k == 'out_array':
                pre.append('%s = (%s * %s)()' % (n, info['elem'], info['aux']))
                call.append(n)
                outs.append(n)
            elif k == 'out_ptr':
                pre.append('%s = c_void_p()' % n)
                call.append('byref(%s)' % n)
                outs.append('%s.value' % n)
            elif k == 'out':
                aux = info['aux']
                pre.append('%s = %s()' % (n, aux))
                call.append('byref(%s)' % n)
                if aux in INTEGER_TYPES or aux in ('c_float', 'c_double', 'BOOL', 'HRESULT', 'c_void_p', 'c_char_p', 'c_wchar_p') \
                        or aux in self.enums or (aux in self.aliases and self.alias_is_simple(aux)):
                    outs.append('%s.value' % n)
                else:
                    outs.append(n)
            elif k == 'in_array':
                sig.append([n, None])
                pre.append('%s, _%s_n = _arr(%s, %s)' % (n, n, info.get('elem', 'c_void_p'), n))
                call.append(n)
            elif k == 'in_bytes':
                sig.append([n, None])
                pre.append('%s, _%s_n, _%s_k = _buf(%s)' % (n, n, n, n))
                call.append(n)
            elif k == 'in_iface':
                sig.append([n, None])
                call.append('_ptr(%s)' % n)
            elif k == 'in_str':
                sig.append([n, None])
                call.append('_str(%s)' % n)
            else:
                sig.append([n, None])
                if info['argtype'].startswith('POINTER(') and info['argtype'] not in ('POINTER(GUID)',):
                    elem = info['argtype'][8:-1]
                    pre.append('if %s.__class__ in (list, tuple): %s = _arr(%s, %s)[0]' % (n, n, elem, n))
                call.append(n)
        # defaults: C++ default arguments, then overrides
        for s in sig:
            info = next(i for i in infos if i['name'] == s[0])
            if info.get('cdefault') is not None:
                s[1] = info['cdefault']
            if s[0] in defaults:
                s[1] = defaults[s[0]]
        for info in infos:
            if info['kind'] == 'riid':
                for s in sig:
                    if s[0] == info['name'] and s[1] is None and info.get('default'):
                        s[1] = repr(info['default'])
        # trailing optional pointer params -> None
        for s in reversed(sig):
            info = next(i for i in infos if i['name'] == s[0])
            if s[1] is not None:
                continue
            opt = any('_opt_' in x[0] for x in info['sal'])
            if info['kind'] in ('in_array', 'in_bytes') and info.get('aux'):
                opt = True  # count is derived from the sequence, so None -> 0 elements
            if opt and info['kind'] in ('in', 'in_iface', 'in_array', 'in_bytes', 'in_str'):
                s[1] = 'None'
            else:
                break
        # only trailing defaults are allowed
        seen_required = False
        for s in reversed(sig):
            pass
        ok = True
        params = []
        has_default = False
        for s in sig:
            if s[1] is None and has_default:
                ok = False
            if s[1] is not None:
                has_default = True
        if not ok:
            # drop defaults that precede required params
            last_req = max(i for i, s in enumerate(sig) if s[1] is None)
            for i in range(last_req):
                sig[i][1] = None
        for s in sig:
            params.append(s[0] if s[1] is None else '%s=%s' % (s[0], s[1]))
        if kwonly:
            params.append('*')
            params.extend(kwonly)
        return params, pre, call, outs, error_blob

    def alias_is_simple(self, name):
        u = self.aliases.get(name)
        if u is None:
            return False
        e = self.ctype(u)
        return e in INTEGER_TYPES or e in ('c_float', 'c_double', 'c_void_p', 'BOOL', 'HRESULT') or e in self.enums

    def c_signature(self, cursor):
        params = [p for p in cursor.get_children() if p.kind == CK.PARM_DECL]
        return '%s %s(%s)' % (cursor.result_type.spelling, cursor.spelling,
                              ', '.join('%s %s' % (p.type.spelling, p.spelling) for p in params))

    def return_info(self, cursor):
        rt = cursor.result_type
        rc = rt.get_canonical()
        if rt.spelling == 'HRESULT' or (rt.kind == TK.TYPEDEF and rt.get_declaration().spelling == 'HRESULT'):
            return 'hresult', 'HRESULT'
        if rc.kind == TK.VOID:
            return 'void', 'None'
        if rc.kind == TK.RECORD:
            return 'struct', self.ctype(rt)
        if rc.kind == TK.POINTER and self.interface_of(rc.get_pointee()):
            return 'iface', 'c_void_p'
        ct = self.ctype(rt, param=True)
        if ct == 'c_char_p':
            return 'cstr', 'c_char_p'
        return 'value', ct

    def emit_method(self, iface, m, pyname, vindex, w):
        qualname = '%s.%s' % (iface.name, pyname)
        infos = self.analyze_params(m, qualname, True)
        for info in infos:
            if info['kind'] == 'riid':
                info['default'] = self.riid_default(qualname, iface.name, m.spelling,
                                                    infos[infos.index(info) + 1]['name'])
        rkind, rtype = self.return_info(m)
        argtypes = [i['argtype'] for i in infos]
        if rkind == 'struct':
            # MSVC member functions return aggregates through a hidden pointer after `this`
            k = self.proto('c_void_p', ['POINTER(%s)' % rtype] + argtypes)
        else:
            k = self.proto(rtype, argtypes)
        params, pre, call, outs, error_blob = self.emit_signature(infos, qualname)
        w('    def %s(%s):' % (pyname, ', '.join(['self'] + params)))
        w('        %r' % self.c_signature(m).replace(' %s(' % m.spelling, ' %s(' % pyname, 1))
        for line in pre:
            w('        ' + line)
        fn = 'self._fn(%d, _P[%d])' % (vindex, k)
        args = ', '.join(['self._this'] + call)
        self.emit_call_and_return(w, '        ', fn, args, rkind, rtype, outs, error_blob, qualname, m)
        return k

    def emit_call_and_return(self, w, ind, fn, args, rkind, rtype, outs, error_blob, qualname, cursor):
        if rkind == 'hresult' and not outs and cursor.spelling.startswith('Get') and not any(
                p.type.get_canonical().kind in (TK.POINTER, TK.LVALUEREFERENCE)
                for p in cursor.get_children() if p.kind == CK.PARM_DECL):
            # e.g. GetDeviceRemovedReason(), IDStorageStatusArray.GetHResult(i): the HRESULT is the data
            rkind = 'value'
        if rkind == 'struct':
            w(ind + '_ret = %s()' % rtype)
            args = args.replace('self._this', 'self._this, byref(_ret)', 1) if args.startswith('self._this') else 'byref(_ret), ' + args
            w(ind + '%s(%s)' % (fn, args))
            outs = ['_ret'] + outs
        elif rkind == 'hresult':
            if error_blob:
                w(ind + '_hr = _check(%s(%s), %r, %s)' % (fn, args, qualname, error_blob))
            else:
                w(ind + '_hr = _check(%s(%s), %r)' % (fn, args, qualname))
            if not outs:
                w(ind + 'return _hr or None')
                return
        elif rkind == 'void':
            w(ind + '%s(%s)' % (fn, args))
        else:
            w(ind + '_r = %s(%s)' % (fn, args))
            if rkind == 'iface':
                iname = self.interface_of(cursor.result_type.get_canonical().get_pointee())
                w(ind + '_r = _borrowed(%r, _r)' % iname)
            elif rkind == 'cstr':
                w(ind + "_r = _r.decode('utf-8', 'replace') if _r is not None else None")
            outs = ['_r'] + outs
        if not outs:
            return
        if len(outs) == 1:
            w(ind + 'return ' + outs[0])
        else:
            w(ind + 'return (%s)' % ', '.join(outs))

    def emit_function(self, name, c, dll, w):
        infos = self.analyze_params(c, name, False)
        for info in infos:
            if info['kind'] == 'riid':
                info['default'] = self.riid_default(name, None, name, infos[infos.index(info) + 1]['name'])
        rkind, rtype = self.return_info(c)
        argtypes = [i['argtype'] for i in infos]
        params, pre, call, outs, error_blob = self.emit_signature(infos, name)
        w('_f_%s = _Func(%r, %r, WINFUNCTYPE(%s))' % (name, dll, name, ', '.join([rtype] + argtypes)))
        w('def %s(%s):' % (name, ', '.join(params)))
        w('    %r' % self.c_signature(c))
        for line in pre:
            w('    ' + line)
        if rkind == 'struct':
            rkind = 'value'  # free functions return small structs in registers; ctypes handles it
        self.emit_call_and_return(w, '    ', '_f_%s' % name, ', '.join(call), rkind, rtype, outs, error_blob, name, c)
        w('')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sdk', default=None, help='Windows SDK version (default: latest installed)')
    ap.add_argument('--agility', default=None,
                    help='Agility SDK include dir (default: newest .deps/agility-*/pkg/build/native/include)')
    ap.add_argument('--no-agility', action='store_true')
    args = ap.parse_args()
    packages = find_packages()
    if args.no_agility:
        packages.pop('agility', None)
    print('Windows SDK:', find_sdk(args.sdk)[1])
    for name, (ver, inc) in packages.items():
        print('  %-14s %-14s %s' % (name, ver, inc))
    g = Generator(args.sdk, args.agility, packages)
    g.run()
    g.emit()
    for wmsg in g.warnings[:50]:
        print('warning:', wmsg)
    if len(g.warnings) > 50:
        print('... %d more warnings' % (len(g.warnings) - 50))


if __name__ == '__main__':
    main()
