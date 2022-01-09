import unittest
import weakref
import sys
from pydx12 import *


class AdapterTests(unittest.TestCase):

    def test_enum(self):
        self.assertIsInstance(CreateDXGIFactory().EnumAdapters(), list)
