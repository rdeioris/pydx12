import unittest
import weakref
import sys
from pydx12 import *


class ShaderTests(unittest.TestCase):

    def test_vertex_shader(self):
        code = 'float4 main() : SV_Position { return float4(1, 1, 1, 1);}'
        blob = D3DCompile(code, None, None, None, 'main', 'vs_5_0', 0, 0)
        self.assertIsNotNone(blob)

    def test_vertex_shader_define(self):
        code = 'float4 main() : SV_Position { return float4(ONE, TWO, THREE, FOUR);}'
        macro_ONE = D3D_SHADER_MACRO(Name='ONE', Definition='1')
        macro_TWO = D3D_SHADER_MACRO(Name='TWO', Definition='2')
        macro_THREE = D3D_SHADER_MACRO(Name='THREE', Definition='3')
        macro_FOUR = D3D_SHADER_MACRO(Name='FOUR', Definition='4')
        blob = D3DCompile(code, None, (macro_ONE, macro_TWO, macro_THREE, macro_FOUR), None, 'main', 'vs_5_0', 0, 0)
        self.assertIsNotNone(blob)
        print(blob)
