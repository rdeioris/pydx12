import pytest

import pydx12 as dx

VS = 'float4 main() : SV_Position { return float4(ONE, 1, 1, 1); }'


def test_d3dcompile():
    blob = dx.D3DCompile(VS.replace('ONE', '1'), None, None, None, 'main', 'vs_5_0')
    assert isinstance(blob, dx.ID3DBlob)
    assert bytes(blob)[:4] == b'DXBC'
    assert bytearray(blob)[:4] == b'DXBC'


def test_d3dcompile_defines():
    # pDefines is a NULL-terminated array
    defines = [dx.D3D_SHADER_MACRO(Name='ONE', Definition='1'), dx.D3D_SHADER_MACRO()]
    blob = dx.D3DCompile(VS, None, defines, None, 'main', 'vs_5_0')
    assert len(blob) > 0


def test_d3dcompile_error_message():
    with pytest.raises(dx.DXError) as e:
        dx.D3DCompile('this is not hlsl', None, None, None, 'main', 'vs_5_0')
    assert 'error' in e.value.message


def test_reflection():
    blob = dx.D3DCompile('cbuffer C : register(b0) { float4 x; }; float4 main() : SV_Position { return x; }',
                         None, None, None, 'main', 'vs_5_0')
    refl = dx.D3DReflect(blob)
    assert refl.GetDesc().ConstantBuffers == 1
    assert refl.GetConstantBufferByIndex(0).GetDesc().Name == 'C'


def test_dxc_compile3():
    compiler = dx.DxcCreateInstance(dx.CLSID_DxcCompiler, dx.IDxcCompiler3)
    src = b'[numthreads(1,1,1)] void main() {}'
    buf = dx.DxcBuffer(Ptr=src, Size=len(src))
    result = compiler.Compile(buf, ['-T', 'cs_6_0', '-E', 'main'], None, dx.IDxcResult)
    assert result.GetStatus() == 0
    obj = result.GetOutput(dx.DXC_OUT_OBJECT, dx.IDxcBlob)[0]
    assert obj is not None and bytes(obj)[:4] == b'DXBC'
