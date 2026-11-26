"""Check every generated ctypes struct against the layout computed by clang (MSVC x64 ABI)."""
import ctypes
import pytest
import pydx12._api as api
from tests.layout_data import LAYOUTS


def test_layouts():
    errors = []
    for name, (size, align, offsets) in LAYOUTS.items():
        cls = getattr(api, name, None)
        if cls is None:
            errors.append('%s missing' % name)
            continue
        if ctypes.sizeof(cls) != size:
            errors.append('%s size %d != %d' % (name, ctypes.sizeof(cls), size))
        if ctypes.alignment(cls) != align:
            errors.append('%s align %d != %d' % (name, ctypes.alignment(cls), align))
        for field, off in offsets.items():
            raw = None
            for klass in cls.__mro__:
                if field in klass.__dict__:
                    raw = klass.__dict__[field]
                    break
            raw = getattr(raw, 'raw', raw)
            if raw is not None and hasattr(raw, 'offset') and raw.offset != off:
                errors.append('%s.%s offset %d != %d' % (name, field, raw.offset, off))
    assert not errors, '\n'.join(errors[:60]) + '\n(%d errors)' % len(errors)
