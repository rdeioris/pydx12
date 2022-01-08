import unittest
import weakref
import sys
from pydx12 import *


class FieldTests(unittest.TestCase):

    def test_d3d12_range_fields(self):
        d3d12_range = D3D12_RANGE(Begin=100, End=200)
        self.assertEqual(d3d12_range.Begin, 100)
        self.assertEqual(d3d12_range.End, 200)

    def test_d3d12_clear_value(self):
        d3d12_clear_value = D3D12_CLEAR_VALUE()
        stencil = d3d12_clear_value.DepthStencil
        stencil.Stencil = 100
        self.assertEqual(d3d12_clear_value.DepthStencil.Stencil, 100)

    def test_carray(self):
        d3d12_blend_desc = D3D12_BLEND_DESC()
        rt0 = d3d12_blend_desc.RenderTarget[0]
        rt0.BlendEnable = True
        rt5 = d3d12_blend_desc.RenderTarget[5]
        rt5.RenderTargetWriteMask = 0x80
        self.assertTrue(d3d12_blend_desc.RenderTarget[0].BlendEnable)
        self.assertEqual(
            d3d12_blend_desc.RenderTarget[5].RenderTargetWriteMask, 0x80)

    def test_buffer_size(self):
        d3d12_shader_bytecode = D3D12_SHADER_BYTECODE()
        self.assertIsNone(d3d12_shader_bytecode.pShaderBytecode)
        data = b'\xde\xad\xbe\xef'
        d3d12_shader_bytecode.pShaderBytecode = data
        self.assertIsNone(d3d12_shader_bytecode.pShaderBytecode)
        d3d12_shader_bytecode.BytecodeLength = 4
        self.assertEqual(d3d12_shader_bytecode.pShaderBytecode[0], 0xDE)

    def test_string_reuse(self):
        hello = 'HELLO'
        d3d12_input_element_desc = D3D12_INPUT_ELEMENT_DESC()
        d3d12_input_element_desc.SemanticName = hello
        d3d12_input_element_desc2 = D3D12_INPUT_ELEMENT_DESC(
            SemanticName=hello)
        self.assertEqual(d3d12_input_element_desc.SemanticName,
                         d3d12_input_element_desc2.SemanticName)


class RefCountTests(unittest.TestCase):

    def test_d3d12_range_kwargs(self):
        d3d12_range = D3D12_RANGE(Begin=100, End=200)
        ref = weakref.ref(d3d12_range)
        d3d12_range = None
        self.assertIsNone(ref())

    def test_d3d12_clear_value_double_ref(self):
        d3d12_clear_value = D3D12_CLEAR_VALUE()
        ref = weakref.ref(d3d12_clear_value)
        depth_stencil = d3d12_clear_value.DepthStencil
        stencil_ref = weakref.ref(depth_stencil)
        stencil_ref().Stencil = 100
        self.assertEqual(d3d12_clear_value.DepthStencil.Stencil, 100)
        d3d12_clear_value = None
        self.assertIsNotNone(ref())
        depth_stencil = None
        self.assertIsNone(ref())

    def test_carray_refs(self):
        d3d12_blend_desc = D3D12_BLEND_DESC()
        ref = weakref.ref(d3d12_blend_desc)
        rt0 = d3d12_blend_desc.RenderTarget[0]
        rt0.BlendEnable = True
        rt5 = d3d12_blend_desc.RenderTarget[5]
        rt5.RenderTargetWriteMask = 0xA0
        d3d12_blend_desc = None
        self.assertIsNotNone(ref())
        rt0 = None
        rt5 = None
        self.assertIsNone(ref())

    def test_buffer(self):
        d3d12_shader_bytecode = D3D12_SHADER_BYTECODE()
        self.assertIsNone(d3d12_shader_bytecode.pShaderBytecode)
        ref = weakref.ref(d3d12_shader_bytecode)
        data = b'\xde\xad\xbe\xef'
        d3d12_shader_bytecode.pShaderBytecode = data
        self.assertEqual(len(d3d12_shader_bytecode.pShaderBytecode), 4)
        data = None
        self.assertEqual(ref().pShaderBytecode[0], 0xDE)
        d3d12_shader_bytecode = None
        self.assertIsNone(ref())

    def test_string_tracking(self):
        d3d12_input_element_desc = D3D12_INPUT_ELEMENT_DESC(
            SemanticName='HELLO'.lower())
        self.assertEqual(len(d3d12_input_element_desc.get_chunks()), 1)
        print(d3d12_input_element_desc.SemanticName, d3d12_input_element_desc.get_chunks())
        foo = d3d12_input_element_desc.SemanticName
        print(d3d12_input_element_desc.SemanticName, d3d12_input_element_desc.get_chunks())
        d3d12_input_element_desc.SemanticName = foo
        print(d3d12_input_element_desc.SemanticName, d3d12_input_element_desc.get_chunks())
        self.assertEqual(d3d12_input_element_desc.SemanticName, 'hello')

    def test_string_untracking(self):
        d3d12_input_element_desc = D3D12_INPUT_ELEMENT_DESC(
            SemanticName='HELLO'.lower())
        self.assertEqual(len(d3d12_input_element_desc.get_chunks()), 1)
        d3d12_input_element_desc.SemanticName = None
        self.assertEqual(len(d3d12_input_element_desc.get_chunks()), 0)

    def test_string_copy(self):
        d3d12_input_element_desc = D3D12_INPUT_ELEMENT_DESC(
            SemanticName='HELLO'.lower())
        foo = d3d12_input_element_desc.SemanticName
        d3d12_input_element_desc.SemanticName = foo + '__'
        d3d12_input_element_desc2 = d3d12_input_element_desc
        print(d3d12_input_element_desc2.to_dict())
        self.assertEqual(d3d12_input_element_desc2.SemanticName, 'hello__')

    def test_struct_array_copy(self):
        layout = D3D12_INPUT_LAYOUT_DESC()
        self.assertEqual(len(layout.get_chunks()), 0)
        layout.pInputElementDescs = [
            D3D12_INPUT_ELEMENT_DESC(SemanticName='TEST')]
        self.assertEqual(len(layout.get_chunks()), 2)
        self.assertEqual(layout.pInputElementDescs[0].SemanticName, 'TEST')
        layout2 = D3D12_INPUT_LAYOUT_DESC()
        self.assertEqual(len(layout2.get_chunks()), 0)
        layout2.pInputElementDescs = layout.pInputElementDescs
        self.assertEqual(len(layout2.get_chunks()), 2)

    def test_struct_array_simple(self):
        pipeline_state_desc = D3D12_GRAPHICS_PIPELINE_STATE_DESC()
        pipeline_state_desc.InputLayout.NumElements = 3
        descs = [
            D3D12_INPUT_ELEMENT_DESC(
                SemanticName='POSITION', Format=DXGI_FORMAT_R32G32_FLOAT),
            D3D12_INPUT_ELEMENT_DESC(),
            D3D12_INPUT_ELEMENT_DESC(SemanticName='NORMAL')]
        pipeline_state_desc.InputLayout.pInputElementDescs = descs
        print('D3D12_GRAPHICS_PIPELINE_STATE_DESC',
              D3D12_GRAPHICS_PIPELINE_STATE_DESC.get_tracked_refs())
        print('D3D12_INPUT_LAYOUT_DESC',
              D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print('D3D12_INPUT_ELEMENT_DESC',
              D3D12_INPUT_ELEMENT_DESC.get_tracked_refs())

    def test_struct_array(self):
        pipeline_state_desc = D3D12_GRAPHICS_PIPELINE_STATE_DESC()
        print('START0', sys.getrefcount(pipeline_state_desc))
        pipeline_state_desc.InputLayout.NumElements = 3
        descs = [
            D3D12_INPUT_ELEMENT_DESC(
                SemanticName='POSITION', Format=DXGI_FORMAT_R32G32_FLOAT),
            D3D12_INPUT_ELEMENT_DESC(),
            D3D12_INPUT_ELEMENT_DESC(SemanticName='NORMAL')]
        pipeline_state_desc.InputLayout.pInputElementDescs = descs
        print('START1', sys.getrefcount(pipeline_state_desc))
        print(D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print('adding refs...')
        pipeline_state_desc2 = pipeline_state_desc
        print(sys.getrefcount(pipeline_state_desc),
              D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print('CREATING items')
        items = pipeline_state_desc.InputLayout.pInputElementDescs
        print('ITEMS', [item.to_dict() for item in items])
        self.assertTrue(len(items) == 3)
        print(D3D12_GRAPHICS_PIPELINE_STATE_DESC.get_tracked_refs())
        print(D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print(D3D12_INPUT_ELEMENT_DESC.get_tracked_refs())
        print('END OF PIPELINE')
        pipeline_state_desc = None
        pipeline_state_desc2 = None
        print('PIPELINE CLEARED')
        print(D3D12_GRAPHICS_PIPELINE_STATE_DESC.get_tracked_refs())
        print(D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print(D3D12_INPUT_ELEMENT_DESC.get_tracked_refs())
        print('releasing items...')
        items = None
        print(D3D12_GRAPHICS_PIPELINE_STATE_DESC.get_tracked_refs())
        print(D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print(D3D12_INPUT_ELEMENT_DESC.get_tracked_refs())
        descs = None
        print(D3D12_GRAPHICS_PIPELINE_STATE_DESC.get_tracked_refs())
        print(D3D12_INPUT_LAYOUT_DESC.get_tracked_refs())
        print(D3D12_INPUT_ELEMENT_DESC.get_tracked_refs())
        self.assertTrue(
            len(D3D12_GRAPHICS_PIPELINE_STATE_DESC.get_tracked_refs()) == 0)
        self.assertTrue(len(D3D12_INPUT_LAYOUT_DESC.get_tracked_refs()) == 0)
        self.assertTrue(len(D3D12_INPUT_ELEMENT_DESC.get_tracked_refs()) == 0)
        print("END OF TEST")
