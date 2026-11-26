import glob
import os

import pytest

import pydx12 as dx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope='session')
def factory():
    return dx.CreateDXGIFactory2()


@pytest.fixture(scope='session')
def adapter(factory):
    return factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)


@pytest.fixture(scope='session')
def device(adapter):
    return dx.D3D12CreateDevice(adapter)


@pytest.fixture(scope='session')
def agility_path():
    cands = sorted(glob.glob(os.path.join(ROOT, '.deps', 'agility-*', 'pkg', 'build', 'native', 'bin', 'x64')))
    if not cands:
        pytest.skip('Agility SDK not downloaded in .deps/')
    return os.path.join(cands[-1], '')
