"""Tests for the NuGet-only SDKs: DXC (bundled), DirectStorage and GameInput (DLLs from .deps/)."""
import ctypes
import glob
import os

import pytest

import pydx12 as dx
from pydx12 import _api, _core

from .conftest import ROOT


def package_bin(name, *parts):
    cands = sorted(glob.glob(os.path.join(ROOT, '.deps', name + '-*', 'pkg', *parts)))
    if not cands:
        pytest.skip('%s not downloaded in .deps/' % name)
    return cands[-1]


@pytest.fixture(scope='module')
def directstorage():
    os.add_dll_directory(package_bin('directstorage', 'native', 'bin', 'x64'))


@pytest.fixture(scope='module')
def gameinput():
    os.add_dll_directory(package_bin('gameinput', 'native', 'bin', 'x64'))


# declared by the Agility SDK headers but only exported by newer runtimes than the in-box ones
NEWER_THAN_OS = {'D3D12CreateVersionedRootSignatureDeserializerFromSubobjectInLibrary',
                 'D3D12SDKLayersGetInterface'}  # Agility's d3d12SDKLayers.dll only


def test_all_functions_are_exported(directstorage, gameinput):
    """Every generated function must be a real export of its DLL (when the DLL is available)."""
    missing = []
    for name, f in vars(_api).items():
        if not isinstance(f, _core._Func):
            continue
        try:
            lib = _core._dll(f.dll)
        except OSError:
            continue  # e.g. DirectML.dll / D3D12StateObjectCompiler.dll not installed
        if not hasattr(lib, f.name) and f.name not in NEWER_THAN_OS:
            missing.append('%s!%s' % (f.dll, f.name))
    assert not missing, missing


def test_dxc_shader_model_6_8_work_graph():
    src = b'''
    struct Rec { uint v; };
    [Shader("node")] [NodeLaunch("broadcasting")] [NodeDispatchGrid(1, 1, 1)] [NumThreads(1, 1, 1)]
    void entry(DispatchNodeInputRecord<Rec> r) {}
    '''
    compiler = dx.DxcCreateInstance(dx.CLSID_DxcCompiler, dx.IDxcCompiler3)
    result = compiler.Compile(dx.DxcBuffer(Ptr=src), ['-T', 'lib_6_8'], None, dx.IDxcResult)
    errors = result.GetOutput(dx.DXC_OUT_ERRORS, dx.IDxcBlobUtf8)[0]
    assert result.GetStatus() == 0, bytes(errors)
    obj = result.GetOutput(dx.DXC_OUT_OBJECT, dx.IDxcBlob)[0]
    assert bytes(obj)[:4] == b'DXBC'


def test_directstorage_read_file_to_memory(directstorage):
    factory = dx.DStorageGetFactory()
    f = factory.OpenFile(os.path.abspath(__file__))
    size = os.path.getsize(__file__)
    queue = factory.CreateQueue(dx.DSTORAGE_QUEUE_DESC(
        SourceType=dx.DSTORAGE_REQUEST_SOURCE_FILE, Capacity=dx.DSTORAGE_MIN_QUEUE_CAPACITY,
        Priority=dx.DSTORAGE_PRIORITY_NORMAL, Name='pydx12 test'))
    dest = (ctypes.c_ubyte * size)()
    req = dx.DSTORAGE_REQUEST()
    req.Options.SourceType = dx.DSTORAGE_REQUEST_SOURCE_FILE
    req.Options.DestinationType = dx.DSTORAGE_REQUEST_DESTINATION_MEMORY
    req.Source.File = dx.DSTORAGE_SOURCE_FILE(Source=f, Offset=0, Size=size)
    req.Destination.Memory = dx.DSTORAGE_DESTINATION_MEMORY(Buffer=dest)
    req.UncompressedSize = size
    queue.EnqueueRequest(req)
    status = factory.CreateStatusArray(1)
    queue.EnqueueStatus(status, 0)
    queue.Submit()
    import time
    deadline = time.time() + 5
    while not status.IsComplete(0) and time.time() < deadline:
        time.sleep(0.01)
    assert status.IsComplete(0)
    assert status.GetHResult(0) == 0
    with open(__file__, 'rb') as fp:
        assert bytes(dest) == fp.read()
    f.Close()


def test_gameinput(gameinput):
    gi = dx.GameInputInitialize()
    assert isinstance(gi, dx.IGameInput)
    assert gi.GetCurrentTimestamp() > 0
    try:
        reading = gi.GetCurrentReading(dx.GameInputKindGamepad)
    except dx.DXError as e:
        assert e.hresult == dx.GAMEINPUT_E_READING_NOT_FOUND  # no gamepad connected
    else:
        state = reading.GetGamepadState()
        assert isinstance(state, dx.GameInputGamepadState)
