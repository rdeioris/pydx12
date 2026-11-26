import ctypes
import gc

import pydx12 as dx


def test_fields_and_kwargs():
    r = dx.D3D12_RANGE(Begin=100, End=200)
    assert (r.Begin, r.End) == (100, 200)


def test_anonymous_union():
    v = dx.D3D12_CLEAR_VALUE()
    v.DepthStencil.Stencil = 100
    assert v.DepthStencil.Stencil == 100
    v.Color = (1.0, 0.5)
    assert list(v.Color)[:2] == [1.0, 0.5]


def test_fixed_arrays_accept_short_sequences():
    desc = dx.D3D12_GRAPHICS_PIPELINE_STATE_DESC()
    desc.RTVFormats = (dx.DXGI_FORMAT_R8G8B8A8_UNORM,)
    assert desc.RTVFormats[0] == dx.DXGI_FORMAT_R8G8B8A8_UNORM
    desc.BlendState.RenderTarget[5].RenderTargetWriteMask = 0x80
    assert desc.BlendState.RenderTarget[5].RenderTargetWriteMask == 0x80


def test_string_fields():
    e = dx.D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=dx.DXGI_FORMAT_R32G32_FLOAT)
    assert e.SemanticName == 'POSITION'


def test_array_field_sets_count_and_survives_copies():
    desc = dx.D3D12_GRAPHICS_PIPELINE_STATE_DESC()
    desc.InputLayout = dx.D3D12_INPUT_LAYOUT_DESC(pInputElementDescs=[
        dx.D3D12_INPUT_ELEMENT_DESC(SemanticName='POS' + 'ITION'),
        dx.D3D12_INPUT_ELEMENT_DESC(SemanticName='NORMAL', SemanticIndex=1)])
    gc.collect()
    assert desc.InputLayout.NumElements == 2
    elems = desc.InputLayout.pInputElementDescs
    assert [e.SemanticName for e in elems] == ['POSITION', 'NORMAL']
    assert elems[1].SemanticIndex == 1


def test_string_array_field():
    a = dx.D3D12_SUBOBJECT_TO_EXPORTS_ASSOCIATION(pExports=['Hello', 'World', 'Test'])
    assert a.NumExports == 3
    assert a.pExports == ['Hello', 'World', 'Test']


def test_buffer_field_sets_size():
    data = b'\xde\xad\xbe\xef'
    bc = dx.D3D12_SHADER_BYTECODE(pShaderBytecode=data)
    assert bc.BytecodeLength == 4
    assert bytes(bc.pShaderBytecode) == data


def test_bitfields():
    inst = dx.D3D12_RAYTRACING_INSTANCE_DESC(InstanceID=0x123456, InstanceMask=0xFF)
    assert inst.InstanceID == 0x123456 and inst.InstanceMask == 0xFF
    assert ctypes.sizeof(inst) == 64


def test_guid():
    assert str(dx.ID3D12Device._iid_) == '{189819F1-1DB6-4B57-BE54-1821339B85F7}'
    assert dx.GUID('189819f1-1db6-4b57-be54-1821339b85f7') == dx.ID3D12Device._iid_


def test_constants():
    assert dx.D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING == 5768
    assert dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES == 0xFFFFFFFF
    assert dx.DXGI_ERROR_DEVICE_REMOVED == -2005270523
