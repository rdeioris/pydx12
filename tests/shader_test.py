import unittest
import weakref
import sys
from pydx12 import *


class ShaderTests(unittest.TestCase):

    def test_vertex_shader(self):
        code = 'float4 main() : SV_Position { return float4(1, 1, 1, 1);}'
        blob = D3DCompile(code, None, None, None, 'main', 'vs_5_0', 0, 0)
        self.assertIsInstance(blob, ID3DBlob)

    def test_vertex_shader_no_optional(self):
        code = 'float4 main() : SV_Position { return float4(1, 1, 1, 1);}'
        blob = D3DCompile(code, None, None, None, 'main', 'vs_5_0')
        self.assertIsInstance(blob, ID3DBlob)

    def test_vertex_shader_define(self):
        code = 'float4 main() : SV_Position { return float4(ONE, TWO, THREE, FOUR);}'
        macro_ONE = D3D_SHADER_MACRO(Name='ONE', Definition='1')
        macro_TWO = D3D_SHADER_MACRO(Name='TWO', Definition='2')
        macro_THREE = D3D_SHADER_MACRO(Name='THREE', Definition='3')
        macro_FOUR = D3D_SHADER_MACRO(Name='FOUR', Definition='4')
        blob = D3DCompile(code, None, (macro_ONE, macro_TWO,
                          macro_THREE, macro_FOUR), None, 'main', 'vs_5_0', 0, 0)
        self.assertIsInstance(blob, ID3DBlob)

    def test_vertex_shader_buffer_protocol(self):
        code = 'float4 main() : SV_Position { return float4(1, 1, 1, 1);}'
        blob = D3DCompile(code, None, None, None, 'main', 'vs_5_0')
        buffer_blob = bytearray(blob)
        self.assertIsInstance(buffer_blob, bytearray)

    def test_vertex_shader_com(self):
        code = 'float4 main() : SV_Position { return float4(1, 1, 1, 1);}'
        blob = D3DCompile(code, None, None, None, 'main', 'vs_5_0', 0, 0)
        desc = D3D12_GRAPHICS_PIPELINE_STATE_DESC(VS=D3D12_SHADER_BYTECODE(
            pShaderBytecode=blob, BytecodeLength=blob.GetBufferSize()))
        self.assertEqual(desc.VS.BytecodeLength, blob.GetBufferSize())

    def test_dxcompiler_library(self):
        self.assertIsInstance(DxcCreateInstance(IDxcLibrary), IDxcLibrary)

    def test_dxcompiler_compiler(self):
        self.assertIsInstance(DxcCreateInstance(IDxcCompiler), IDxcCompiler)

    def test_dxcompiler_blob(self):
        blob = DxcCreateInstance(IDxcLibrary).CreateBlobWithEncodingOnHeapCopy(
            'Hello World'.encode('utf8'))
        self.assertIsInstance(blob, IDxcBlobEncoding)
        self.assertIsInstance(blob, IDxcBlob)

    def test_dxcompiler_shader(self):
        blob = DxcCreateInstance(IDxcLibrary).CreateBlobWithEncodingOnHeapCopy(
            'void main() {}'.encode('utf8'))
        compiled_blob = DxcCreateInstance(IDxcCompiler).Compile(blob, None, 'main', 'lib_6_3')
        self.assertIsInstance(compiled_blob, IDxcBlob)

    def test_dxcompiler_blob_buffer(self):
        blob = DxcCreateInstance(IDxcLibrary).CreateBlobWithEncodingOnHeapCopy(
            'void main() {}'.encode('utf8'))
        compiled_blob = DxcCreateInstance(IDxcCompiler).Compile(blob, None, 'main', 'lib_6_3')
        self.assertEqual(bytearray(compiled_blob)[0:4], b'DXBC')
