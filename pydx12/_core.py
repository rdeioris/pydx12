"""
pydx12 runtime core: COM plumbing, GUIDs, HRESULT handling and the smart
ctypes base classes used by the generated bindings in ``pydx12._api``.

Everything here is pure ctypes; nothing is compiled.
"""
import ctypes
import sys
import uuid as _uuid
from typing import Any
from ctypes import (POINTER, Structure, Union, WINFUNCTYPE, Array, byref, c_void_p,
                    c_char_p, c_wchar_p, c_ubyte, c_char, c_long, c_ulong, c_int,
                    cast, sizeof, addressof, string_at, memmove)

__all__ = ['GUID', 'IID', 'CLSID', 'DXError', 'IUnknown', 'ComInterface', 'Struct', 'Union_',
           'S_OK', 'S_FALSE', 'E_NOINTERFACE', 'E_POINTER', 'E_FAIL', 'E_INVALIDARG',
           'E_OUTOFMEMORY', 'E_NOTIMPL', 'FAILED', 'SUCCEEDED', 'implement', 'ComImplementation',
           'as_buffer', 'BlobMixin']

if sys.platform != 'win32':  # pragma: no cover
    raise ImportError('pydx12 requires Windows')

S_OK = 0
S_FALSE = 1
E_NOTIMPL = -2147467263
E_NOINTERFACE = -2147467262
E_POINTER = -2147467261
E_FAIL = -2147467259
E_INVALIDARG = -2147024809
E_OUTOFMEMORY = -2147024882


def FAILED(hr):
    return hr < 0


def SUCCEEDED(hr):
    return hr >= 0


# ---------------------------------------------------------------------------
# GUID
# ---------------------------------------------------------------------------

class GUID(Structure):
    _fields_ = [('Data1', ctypes.c_uint32), ('Data2', ctypes.c_uint16),
                ('Data3', ctypes.c_uint16), ('Data4', ctypes.c_ubyte * 8)]

    def __init__(self, value=None, *args):
        super().__init__()
        if value is None:
            return
        if args:  # GUID(l, w1, w2, b0..b7)
            parts = (value,) + args
            self.Data1, self.Data2, self.Data3 = parts[0] & 0xFFFFFFFF, parts[1], parts[2]
            self.Data4[:] = parts[3:11]
            return
        if isinstance(value, GUID):
            memmove(byref(self), byref(value), 16)
            return
        if isinstance(value, _uuid.UUID):
            u = value
        else:
            u = _uuid.UUID(str(value))
        memmove(byref(self), u.bytes_le, 16)

    @property
    def uuid(self):
        return _uuid.UUID(bytes_le=bytes(memoryview(self).cast('B')))

    def __str__(self):
        return '{%s}' % str(self.uuid).upper()

    def __repr__(self):
        return 'GUID(%r)' % str(self.uuid)

    def __eq__(self, other):
        if isinstance(other, GUID):
            return bytes(memoryview(self).cast('B')) == bytes(memoryview(other).cast('B'))
        try:
            return self == GUID(other)
        except (ValueError, TypeError, AttributeError):
            return NotImplemented

    def __hash__(self):
        return hash(bytes(memoryview(self).cast('B')))


IID = GUID
CLSID = GUID


# ---------------------------------------------------------------------------
# HRESULT -> exception
# ---------------------------------------------------------------------------

_hresult_names: dict = {}  # filled by the generated module


def _register_hresults(names):
    for k, v in names.items():
        _hresult_names.setdefault(v, k)


class DXError(OSError):
    """Raised when a DirectX call returns a failing HRESULT."""

    def __init__(self, hresult, message=None, function=None):
        self.hresult = hresult
        self.function = function
        self.name = _hresult_names.get(hresult)
        text = '0x%08X' % (hresult & 0xFFFFFFFF)
        if self.name:
            text = '%s (%s)' % (self.name, text)
        else:
            try:
                text += ' ' + ctypes.FormatError(hresult & 0xFFFFFFFF).strip()
            except Exception:  # pragma: no cover
                pass
        if function:
            text = '%s failed: %s' % (function, text)
        if message:
            text += '\n' + message
        self.message = message
        super().__init__(text)

    @property
    def winerror(self):  # type: ignore[override]
        return self.hresult


def _check(hr, function=None, error_blob=None):
    if hr is None:
        return 0
    if hr < 0:
        message = None
        if error_blob is not None:
            message = _blob_text(error_blob)
        raise DXError(hr, message, function)
    return hr


def _blob_text(blob):
    if isinstance(blob, c_void_p):
        if not blob.value:
            return None
        blob = _BlobView(blob.value)
    try:
        data = bytes(blob)
    except Exception:
        return None
    return data.rstrip(b'\0').decode('utf-8', 'replace')


# ---------------------------------------------------------------------------
# COM interface wrappers
# ---------------------------------------------------------------------------

_registry: dict = {}  # name -> interface class (for lazily resolved annotations)
_PVOID_P = POINTER(c_void_p)


def _resolve_iface(cls):
    if isinstance(cls, str):
        return _registry[cls]
    return cls


class _ComMeta(type):
    def __new__(mcs, name, bases, ns):
        cls = super().__new__(mcs, name, bases, ns)
        _registry[name] = cls
        return cls

    def __repr__(cls):
        return "<interface '%s'>" % cls.__name__


class ComInterface(metaclass=_ComMeta):
    """Base for every COM-style (vtable based) interface wrapper.

    ``_refcounted_`` is False for interfaces that do not derive from IUnknown
    (e.g. ID3D12ShaderReflectionType or IXAudio2Voice).
    """
    __slots__ = ('_this', '_owned', '_vtbl', '_fns', '__weakref__', '_keep')
    _iid_: 'GUID | None' = None
    _refcounted_ = False

    def __init__(self, this=None, owned=False):
        if isinstance(this, ComInterface):
            src = this
            if self._refcounted_ and src._refcounted_ and type(self)._iid_ is not None:
                ptr = src._query(type(self)._iid_)  # type: ignore[attr-defined]
                self._set(ptr, True)
            else:
                if src._refcounted_:
                    src._addref()
                self._set(src._this, src._refcounted_)
            return
        if this is not None and not isinstance(this, int):
            this = getattr(this, 'value', this)
        self._set(this, owned)

    def _set(self, ptr, owned):
        self._this = ptr or None
        self._owned = bool(owned and ptr)
        self._fns = {}
        self._vtbl = cast(c_void_p(self._this), POINTER(_PVOID_P))[0] if self._this else None

    @classmethod
    def from_address(cls, ptr, addref=True):
        """Wrap a raw interface pointer (taking a new reference by default)."""
        obj = cls.__new__(cls)
        obj._set(ptr, False)
        if ptr and addref and cls._refcounted_:
            obj._addref()
            obj._owned = True
        return obj

    @property
    def value(self):
        """The raw interface pointer as an int."""
        return self._this

    def __bool__(self):
        return bool(self._this)

    def __int__(self):
        return self._this or 0

    @classmethod
    def from_param(cls, obj):
        if obj is None:
            return None
        if isinstance(obj, ComInterface):
            return c_void_p(obj._this)
        if isinstance(obj, int):
            return c_void_p(obj)
        return obj

    def __eq__(self, other):
        return isinstance(other, ComInterface) and other._this == self._this

    def __hash__(self):
        return hash(self._this)

    def __repr__(self):
        return '<%s object at 0x%X>' % (type(self).__name__, self._this or 0)

    def _fn(self, index, proto):
        fn = self._fns.get(index)
        if fn is None:
            if not self._this:
                raise ValueError('NULL %s pointer' % type(self).__name__)
            fn = proto(self._vtbl[index])  # type: ignore[index]
            self._fns[index] = fn
        return fn

    def _addref(self):
        return 0

    def _release(self):
        return 0

    def __del__(self):
        try:
            if self._owned:
                self._owned = False
                self._release()
        except Exception:
            pass

    def detach(self):
        """Give up ownership of the underlying reference and return the pointer."""
        self._owned = False
        return self._this


_QI = WINFUNCTYPE(c_long, c_void_p, POINTER(GUID), POINTER(c_void_p))
_ADDREF = WINFUNCTYPE(c_ulong, c_void_p)


class IUnknown(ComInterface):
    __slots__ = ()
    _iid_ = GUID('00000000-0000-0000-C000-000000000046')
    _refcounted_ = True
    _vtbl_size_ = 3

    def _addref(self):
        return self._fn(1, _ADDREF)(self._this)

    def _release(self):
        return self._fn(2, _ADDREF)(self._this)

    def _query(self, iid):
        out = c_void_p()
        _check(self._fn(0, _QI)(self._this, byref(GUID(iid)), byref(out)), 'QueryInterface')
        return out.value

    def QueryInterface(self, riid):
        """Return this object as interface ``riid`` (an interface class or a GUID)."""
        riid = _resolve_iface(riid)
        if isinstance(riid, type) and issubclass(riid, ComInterface):
            return riid.from_address(self._query(riid._iid_), addref=False)
        return IUnknown.from_address(self._query(riid), addref=False)

    def AddRef(self):
        return self._addref()

    def Release(self):
        """Explicitly release the reference held by this wrapper."""
        if self._owned:
            self._owned = False
            return self._release()
        return self._release()

    def cast(self, iface):
        """Alias of QueryInterface."""
        return self.QueryInterface(iface)


def _owned(iface, ptr):
    """Wrap an out-pointer that already carries a reference."""
    iface = _resolve_iface(iface)
    if isinstance(ptr, c_void_p):
        ptr = ptr.value
    if not ptr:
        return None
    obj = iface.__new__(iface)
    obj._set(ptr, iface._refcounted_)
    return obj


def _borrowed(iface, ptr):
    iface = _resolve_iface(iface)
    if isinstance(ptr, c_void_p):
        ptr = ptr.value
    if not ptr:
        return None
    return iface.from_address(ptr, addref=True)


def _riid(riid):
    """Convert an interface class / GUID / string into (GUID, interface class)."""
    riid = _resolve_iface(riid)
    if isinstance(riid, type) and issubclass(riid, ComInterface):
        if riid._iid_ is None:
            raise TypeError('%s has no IID' % riid.__name__)
        return riid._iid_, riid
    if isinstance(riid, GUID):
        return riid, _iid_lookup.get(riid, IUnknown)
    g = GUID(riid)
    return g, _iid_lookup.get(g, IUnknown)


_iid_lookup: dict = {}


def _register_iids():
    for cls in _registry.values():
        if cls._iid_ is not None:
            _iid_lookup.setdefault(cls._iid_, cls)


# ---------------------------------------------------------------------------
# argument conversion helpers used by generated methods
# ---------------------------------------------------------------------------

def _str(s):
    if isinstance(s, str):
        return s.encode('utf-8')
    return s


def _ptr(o):
    """Interface pointer argument."""
    if o is None:
        return None
    if isinstance(o, ComInterface):
        return o._this
    if isinstance(o, ComImplementation):
        return o.pointer
    if isinstance(o, int):
        return o
    if isinstance(o, c_void_p):
        return o.value
    raise TypeError('expected a COM interface, got %r' % type(o).__name__)


def as_buffer(data):
    """Return (pointer, size, keepalive) for any buffer-like object."""
    if data is None:
        return None, 0, None
    if isinstance(data, ComInterface) and hasattr(data, 'GetBufferPointer'):
        return data.GetBufferPointer(), data.GetBufferSize(), data  # type: ignore[attr-defined]
    if isinstance(data, ctypes._SimpleCData) or isinstance(data, (Structure, Union, Array)):
        return addressof(data), sizeof(data), data
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(data, (bytes, bytearray, memoryview)) or hasattr(data, '__buffer__') or hasattr(data, '__array_interface__'):
        mv = memoryview(data)
        nbytes = mv.nbytes
        if not mv.readonly and mv.c_contiguous:
            arr = (c_ubyte * nbytes).from_buffer(mv.cast('B') if mv.format != 'B' or mv.ndim != 1 else mv)
            return addressof(arr), nbytes, (arr, data)
        arr = (c_ubyte * nbytes).from_buffer_copy(mv.tobytes() if not mv.c_contiguous else mv)
        return addressof(arr), nbytes, arr
    raise TypeError('object of type %r is not a buffer' % type(data).__name__)


def _buf(data):
    ptr, size, keep = as_buffer(data)
    return ptr, size, keep


def _arr(ctype, seq):
    """Build a C array of ``ctype`` from a python sequence (or pass through)."""
    if seq is None:
        return None, 0
    if isinstance(ctype, str):
        ctype = _registry[ctype]
    if isinstance(seq, Array):
        return seq, len(seq)
    if isinstance(seq, (Structure, Union, ctypes._SimpleCData)) and not isinstance(seq, ctypes._Pointer):
        return byref(seq), 1
    if isinstance(seq, ctypes._Pointer) or isinstance(seq, int):
        return seq, None
    if isinstance(ctype, type) and issubclass(ctype, ComInterface):
        seq = list(seq)
        return (c_void_p * len(seq))(*[_ptr(o) for o in seq]), len(seq)
    seq = list(seq) if not isinstance(seq, (list, tuple)) else seq
    n = len(seq)
    arr = (ctype * n)()
    for i, v in enumerate(seq):
        if isinstance(v, dict):
            v = ctype(**v)
        arr[i] = v
    return arr, n


def _seqlen(seq):
    if seq is None:
        return 0
    if isinstance(seq, (Structure, Union)):
        return 1
    return len(seq)


def _out_value(o):
    """Unwrap an out-parameter holder into a Python value."""
    if isinstance(o, ctypes._SimpleCData):
        return o.value
    return o


# ---------------------------------------------------------------------------
# Struct / Union base with smart fields
# ---------------------------------------------------------------------------

class _IFaceRef(Structure):
    """Opaque pointee used to keep python wrappers alive inside structs."""
    _fields_ = []


class _SmartMixin:
    """Mixin for generated Structure/Union classes.

    The generator attaches metadata with ``_smart(cls, ...)`` which replaces
    some raw ctypes field descriptors with properties that accept Python
    objects (lists, strings, buffers, COM objects) and keep them alive.
    """
    _fields_: Any

    def __init__(self, *args, **kwargs):
        super().__init__()
        if args:
            names = [f[0] for f in self._fields_]
            for name, value in zip(names, args):
                setattr(self, name, value)
        for k, v in kwargs.items():
            if not hasattr(type(self), k):
                raise AttributeError('%s has no field %r' % (type(self).__name__, k))
            setattr(self, k, v)

    def __setattr__(self, name, value):
        try:
            super().__setattr__(name, value)
        except TypeError:
            # allow dicts / tuples for nested struct fields and short sequences for arrays
            cur = getattr(self, name, None)
            if isinstance(cur, (Structure, Union)) and isinstance(value, dict):
                for k, v in value.items():
                    setattr(cur, k, v)
                return
            if isinstance(cur, Array) and isinstance(value, (list, tuple)):
                if len(value) > len(cur):
                    raise ValueError('too many items for %s.%s' % (type(self).__name__, name))
                for i, v in enumerate(value):
                    if isinstance(v, dict):
                        for k, vv in v.items():
                            setattr(cur[i], k, vv)
                    else:
                        cur[i] = v
                return
            raise

    def to_dict(self):
        out = {}
        for f in self._fields_:
            name = f[0]
            v = getattr(self, name)
            if isinstance(v, _SmartMixin):
                v = v.to_dict()
            elif isinstance(v, Array):
                v = [x.to_dict() if isinstance(x, _SmartMixin) else x for x in v]
                if v and isinstance(v[0], str):
                    v = ''.join(v)
            out[name] = v
        return out

    def __repr__(self):
        parts = []
        for f in self._fields_[:8]:
            try:
                parts.append('%s=%r' % (f[0], getattr(self, f[0])))
            except Exception:
                parts.append('%s=?' % f[0])
        if len(self._fields_) > 8:
            parts.append('...')
        return '%s(%s)' % (type(self).__name__, ', '.join(parts))

    def copy(self):
        new = type(self)()
        memmove(byref(new), byref(self), sizeof(self))  # type: ignore[arg-type]
        objs = getattr(self, '_objects', None)
        if objs:
            new.__dict__['_pydx12_keep'] = self
        return new


class Struct(_SmartMixin, Structure):
    pass


class Union_(_SmartMixin, Union):
    pass


def _keepalive(target, field_name, raw_field, address, *objects):
    """Store ``address`` into pointer field and keep ``objects`` alive via ctypes' _objects."""
    if not address:
        raw_field.__set__(target, None)
        return
    holder = _IFaceRef.from_address(address)
    holder.__dict__['refs'] = objects
    raw_field.__set__(target, cast(pointer_keep(holder), raw_field_ptrtype(raw_field)))


def pointer_keep(holder):
    return ctypes.pointer(holder)


_raw_types: dict = {}


def raw_field_ptrtype(raw_field):
    return _raw_types[raw_field]


def _smart(cls, iface=None, strings=(), arrays=None, buffers=None, ptrs=()):
    """Install smart properties on a generated struct class.

    iface:   {field: interface name}         COM pointer fields
    strings: [field]                         char* fields (str <-> bytes)
    arrays:  {field: (elemtype, countfield)} pointer + element count
    buffers: {field: sizefield}              void* + size in bytes
    """
    for name, iname in (iface or {}).items():
        raw = cls.__dict__[name]
        setattr(cls, name, _IfaceField(raw, iname))
    for name in strings:
        raw = cls.__dict__[name]
        setattr(cls, name, _StrField(raw))
    for name, (elem, count) in (arrays or {}).items():
        raw = cls.__dict__[name]
        setattr(cls, name, _ArrayField(raw, elem, count, cls, name))
    for name, size in (buffers or {}).items():
        raw = cls.__dict__[name]
        setattr(cls, name, _BufferField(raw, size, cls, name))


class _IfaceField:
    def __init__(self, raw, iname):
        self.raw = raw
        self.iname = iname

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        ptr = cast(self.raw.__get__(obj, owner), c_void_p).value
        return _borrowed(self.iname, ptr) if ptr else None

    def __set__(self, obj, value):
        if value is None:
            self.raw.__set__(obj, None)
            return
        if isinstance(value, ComImplementation):
            addr, keep = value.pointer, value
        else:
            addr, keep = _ptr(value), value
        holder = _IFaceRef.from_address(addr)
        holder.__dict__['ref'] = keep
        self.raw.__set__(obj, cast(ctypes.pointer(holder), type(self.raw.__get__(obj))))


class _StrField:
    def __init__(self, raw):
        self.raw = raw

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        v = self.raw.__get__(obj, owner)
        if isinstance(v, bytes):
            return v.decode('utf-8', 'replace')
        return v

    def __set__(self, obj, value):
        self.raw.__set__(obj, _str(value))


def _find_field_type(cls, name):
    for f in cls._fields_:
        if f[0] == name:
            return f[1]
    for anon in getattr(cls, '_anonymous_', ()):
        sub = dict((f[0], f[1]) for f in cls._fields_)[anon]
        try:
            return _find_field_type(sub, name)
        except KeyError:
            pass
    raise KeyError(name)


def _rawtype(obj, name, raw):
    t = getattr(raw, 'type', None)
    if t is None:
        t = _find_field_type(type(obj), name)
    return t


class _ArrayField:
    """Pointer field with an associated element count field."""

    def __init__(self, raw, elem, count, cls, name):
        self.raw = raw
        self.elem = elem
        self.count = count
        self.cls = cls
        self.name = name

    def __set_name__(self, owner, name):
        self.name = name

    def _elem(self):
        e = self.elem
        if isinstance(e, str):
            e = _registry.get(e) or getattr(sys.modules['pydx12._api'], e)
            self.elem = e
        return e

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        p = self.raw.__get__(obj, owner)
        if not p:
            return None
        n = getattr(obj, self.count) if self.count else None
        elem = self._elem()
        if n is None:
            return p
        if isinstance(elem, type) and issubclass(elem, ComInterface):
            arr = cast(p, POINTER(c_void_p))
            return [_borrowed(elem, arr[i]) for i in range(n)]
        if not isinstance(p, ctypes._Pointer):
            return p
        return [p[i] for i in range(n)]

    def __set__(self, obj, value):
        ptrtype = _rawtype(obj, self.name, self.raw)
        if value is None:
            self.raw.__set__(obj, None)
            if self.count:
                setattr(obj, self.count, 0)
            return
        if isinstance(value, (int, ctypes._Pointer, c_void_p)):
            self.raw.__set__(obj, cast(value, ptrtype) if not isinstance(value, ptrtype) else value)
            return
        elem = self._elem()
        if isinstance(value, Array):
            arr, n = value, len(value)
        else:
            if isinstance(value, (Structure, Union)):
                value = [value]
            arr, n = _arr(elem, value)
        self.raw.__set__(obj, cast(arr, ptrtype))
        # cast() keeps a reference to arr in the result's _objects -> stored by ctypes
        if self.count:
            setattr(obj, self.count, n)



class _BufferField:
    """void* field with an associated byte-size field."""

    def __init__(self, raw, size, cls, name):
        self.raw = raw
        self.size = size
        self.name = name

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        p = self.raw.__get__(obj, owner)
        p = cast(p, c_void_p).value if not isinstance(p, int) else p
        if not p:
            return None
        n = getattr(obj, self.size) if self.size else 0
        if not n:
            return None
        return (c_ubyte * n).from_address(p)

    def __set__(self, obj, value):
        ptrtype = _rawtype(obj, self.name, self.raw)
        if value is None:
            self.raw.__set__(obj, None)
            return
        if isinstance(value, int):
            self.raw.__set__(obj, value if ptrtype is c_void_p else cast(c_void_p(value), ptrtype))
            return
        ptr, size, keep = as_buffer(value)
        holder = _IFaceRef.from_address(ptr)
        holder.__dict__['ref'] = keep
        p = ctypes.pointer(holder)
        if ptrtype is c_void_p or ptrtype is None:
            # c_void_p fields can't hold refs -> store via a casted pointer type
            self.raw.__set__(obj, cast(p, c_void_p))
        else:
            self.raw.__set__(obj, cast(p, ptrtype))
        if self.size and size is not None:
            setattr(obj, self.size, size)


# ---------------------------------------------------------------------------
# implementing COM interfaces in Python (callbacks)
# ---------------------------------------------------------------------------

class ComImplementation:
    """Implement a COM interface in Python.

    Subclass it, set ``_interfaces_`` to the interface classes implemented
    (first one gives the vtable) and define methods with the same names as
    the interface. Pass the instance wherever a pointer to the interface is
    expected. IUnknown methods are implemented automatically.
    """
    _interfaces_: tuple = ()

    def __init__(self):
        iface = _resolve_iface(self._interfaces_[0])
        slots = _vtable_slots(iface)
        self._refcount = 1
        self._callbacks = []
        fns = []
        for (name, proto) in slots:
            impl = self._make_thunk(name, proto)
            cb = proto(impl)
            self._callbacks.append(cb)
            fns.append(cast(cb, c_void_p).value)
        self._vtable = (c_void_p * len(fns))(*fns)
        self._obj = (c_void_p * 1)(addressof(self._vtable))
        _live_impls[self.pointer] = self

    @property
    def pointer(self):
        return addressof(self._obj)

    @property
    def _this(self):
        return self.pointer

    def _make_thunk(self, name, proto):
        refcounted = _resolve_iface(self._interfaces_[0])._refcounted_
        if refcounted and name == 'QueryInterface':
            def qi(this, riid, ppv):
                g = riid.contents if riid else None
                ok = g == IUnknown._iid_ or any(_resolve_iface(i)._iid_ == g for i in self._interfaces_)
                if ok:
                    ppv[0] = self.pointer
                    self._refcount += 1
                    return S_OK
                ppv[0] = None
                return E_NOINTERFACE
            return qi
        if refcounted and name == 'AddRef':
            def addref(this):
                self._refcount += 1
                return self._refcount
            return addref
        if refcounted and name == 'Release':
            def release(this):
                self._refcount -= 1
                return self._refcount
            return release
        method = getattr(self, name, None)
        restype = proto._restype_

        def thunk(this, *args):
            if method is None:
                return E_NOTIMPL if restype is c_long else None
            try:
                r = method(*args)
            except DXError as e:
                return e.hresult
            except Exception:
                import traceback
                traceback.print_exc()
                return E_FAIL if restype is c_long else None
            if restype is c_long and r is None:
                return S_OK
            return r
        return thunk

    def release(self):
        _live_impls.pop(self.pointer, None)


_live_impls: dict = {}


def _vtable_slots(iface):
    """Return [(name, WINFUNCTYPE)] for the complete vtable of ``iface``."""
    out = []
    for c in reversed(iface.__mro__):
        if not isinstance(c, _ComMeta):
            continue
        if '_vslots_' in c.__dict__:
            out.extend(c.__dict__['_vslots_']())
        elif '_vt_' in c.__dict__:
            out.extend((name, _protos[k]) for name, k in c.__dict__['_vt_'])
    return out


_protos: list = []  # set by the generated module


IUnknown._vslots_ = staticmethod(  # type: ignore[attr-defined]
    lambda: [('QueryInterface', _QI), ('AddRef', _ADDREF), ('Release', _ADDREF)])


def implement(*interfaces):
    """Class decorator alternative to setting ``_interfaces_``."""
    def deco(cls):
        cls._interfaces_ = interfaces
        return cls
    return deco


class BlobMixin:
    """Buffer helpers added to ID3DBlob / IDxcBlob."""
    GetBufferPointer: Any  # provided by the interface class
    GetBufferSize: Any

    def __bytes__(self):
        return string_at(self.GetBufferPointer(), self.GetBufferSize())

    def __len__(self):
        return self.GetBufferSize()

    def __getitem__(self, i):
        return bytes(self)[i]

    def to_bytes(self):
        return bytes(self)

    def __buffer__(self, flags):
        return memoryview((c_ubyte * self.GetBufferSize()).from_address(self.GetBufferPointer()))


class _BlobView:
    """Minimal ID3DBlob reader used for error messages before the API is loaded."""

    def __init__(self, ptr):
        self.ptr = ptr

    def __bytes__(self):
        vt = cast(c_void_p(self.ptr), POINTER(_PVOID_P))[0]
        get_ptr = WINFUNCTYPE(c_void_p, c_void_p)(vt[3])
        get_size = WINFUNCTYPE(ctypes.c_size_t, c_void_p)(vt[4])
        return string_at(get_ptr(self.ptr), get_size(self.ptr))


# ---------------------------------------------------------------------------
# DLL loading
# ---------------------------------------------------------------------------

import os as _os

_dll_cache: dict = {}
_pkg_dir = _os.path.dirname(_os.path.abspath(__file__))

# DLLs that load a companion with a plain LoadLibrary (ignoring os.add_dll_directory):
# preload the companion from the directory the main DLL was found in.
_COMPANIONS = {'dstorage.dll': ('dstoragecore.dll',)}


def _module_dir(lib):
    buf = ctypes.create_unicode_buffer(32768)
    ctypes.windll.kernel32.GetModuleFileNameW(ctypes.c_void_p(lib._handle), buf, len(buf))
    return _os.path.dirname(buf.value)


def _dll(name):
    lib = _dll_cache.get(name)
    if lib is None:
        local = _os.path.join(_pkg_dir, name)
        try:
            if _os.path.exists(local):
                lib = ctypes.WinDLL(local)
            else:
                lib = ctypes.WinDLL(name)
        except OSError as e:
            raise OSError('unable to load %s: %s' % (name, e)) from None
        for companion in _COMPANIONS.get(name.lower(), ()):
            path = _os.path.join(_module_dir(lib), companion)
            if _os.path.exists(path):
                _dll_cache[companion] = ctypes.WinDLL(path)
        _dll_cache[name] = lib
    return lib


class _Func:
    """Lazily bound DLL export."""
    __slots__ = ('dll', 'name', 'proto', 'fn')

    def __init__(self, dll, name, proto):
        self.dll = dll
        self.name = name
        self.proto = proto
        self.fn = None

    def __call__(self, *args):
        fn = self.fn
        if fn is None:
            lib = _dll(self.dll)
            try:
                fn = self.proto((self.name, lib))
            except AttributeError:
                raise NotImplementedError('%s is not exported by %s' % (self.name, self.dll)) from None
            self.fn = fn
        return fn(*args)
