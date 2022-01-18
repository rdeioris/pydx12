import unittest
import weakref
import sys
from pydx12 import *


class PipelineTests(unittest.TestCase):

    def test_exports_association(self):
        exports_association = D3D12_SUBOBJECT_TO_EXPORTS_ASSOCIATION()
        exports_association.NumExports = 3
        exports_association.pSubobjectToAssociate = D3D12_STATE_SUBOBJECT()
        exports_association.pExports = ['Hello', 'World', 'Test']
        self.assertEqual(exports_association.pExports[0], 'Hello')
        self.assertEqual(exports_association.pExports[1], 'World')
        self.assertEqual(exports_association.pExports[2], 'Test')
        self.assertEqual(len(exports_association.get_chunks()), 5)