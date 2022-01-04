#include "pydx12.h"

PYDX12_IMPORT(DXGI_SAMPLE_DESC);
PYDX12_IMPORT(D3D12_DEPTH_STENCIL_VALUE);

PYDX12_IMPORT_COM(ID3D12Pageable);

PYDX12_TYPE(D3D12_CLEAR_VALUE);
PYDX12_GETTER_SETTER(D3D12_CLEAR_VALUE, Format, LongLong, DXGI_FORMAT);
PYDX12_STRUCT_GETTER_SETTER(D3D12_CLEAR_VALUE, DepthStencil, D3D12_DEPTH_STENCIL_VALUE);
PYDX12_ARRAY_GETTER_SETTER(D3D12_CLEAR_VALUE, Color, FLOAT, 4, PyFloat_FromDouble, PyFloat_AsDouble);
PYDX12_GETSETTERS(D3D12_CLEAR_VALUE) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_CLEAR_VALUE, Format),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_CLEAR_VALUE, DepthStencil),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_CLEAR_VALUE, Color),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE(D3D12_RANGE);
PYDX12_GETTER_SETTER(D3D12_RANGE, Begin, UnsignedLongLong, SIZE_T);
PYDX12_GETTER_SETTER(D3D12_RANGE, End, UnsignedLongLong, SIZE_T);
PYDX12_GETSETTERS(D3D12_RANGE) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RANGE, Begin),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RANGE, End),
	{NULL}  /* Sentinel */
};


PYDX12_TYPE(D3D12_HEAP_PROPERTIES);
PYDX12_GETTER_SETTER(D3D12_HEAP_PROPERTIES, Type, LongLong, D3D12_HEAP_TYPE);
PYDX12_GETTER_SETTER(D3D12_HEAP_PROPERTIES, CPUPageProperty, LongLong, D3D12_CPU_PAGE_PROPERTY);
PYDX12_GETTER_SETTER(D3D12_HEAP_PROPERTIES, MemoryPoolPreference, LongLong, D3D12_MEMORY_POOL);
PYDX12_GETTER_SETTER(D3D12_HEAP_PROPERTIES, CreationNodeMask, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_HEAP_PROPERTIES, VisibleNodeMask, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_HEAP_PROPERTIES) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_HEAP_PROPERTIES, Type),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_HEAP_PROPERTIES, CPUPageProperty),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_HEAP_PROPERTIES, MemoryPoolPreference),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_HEAP_PROPERTIES, CreationNodeMask),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_HEAP_PROPERTIES, VisibleNodeMask),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE(D3D12_RESOURCE_DESC);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Dimension, LongLong, D3D12_RESOURCE_DIMENSION);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Alignment, UnsignedLongLong, UINT64);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Width, UnsignedLongLong, UINT64);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Height, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, DepthOrArraySize, UnsignedLong, UINT16);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, MipLevels, UnsignedLong, UINT16);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Format, LongLong, DXGI_FORMAT);
PYDX12_STRUCT_GETTER_SETTER(D3D12_RESOURCE_DESC, SampleDesc, DXGI_SAMPLE_DESC);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Layout, LongLong, D3D12_TEXTURE_LAYOUT);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_DESC, Flags, LongLong, D3D12_RESOURCE_FLAGS);
PYDX12_GETSETTERS(D3D12_RESOURCE_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Dimension),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Alignment),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Width),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Height),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, DepthOrArraySize),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, MipLevels),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Format),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, SampleDesc),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Layout),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_DESC, Flags),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE_COM(ID3D12Resource, PyObject* memory_view_list);

PYDX12_TYPE(D3D12_SUBRESOURCE_FOOTPRINT);
PYDX12_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Format, LongLong, DXGI_FORMAT);
PYDX12_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Width, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Height, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Depth, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, RowPitch, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_SUBRESOURCE_FOOTPRINT) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Format),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Width),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Height),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, Depth),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SUBRESOURCE_FOOTPRINT, RowPitch),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE(D3D12_PLACED_SUBRESOURCE_FOOTPRINT);
PYDX12_GETTER_SETTER(D3D12_PLACED_SUBRESOURCE_FOOTPRINT, Offset, UnsignedLongLong, UINT64);
PYDX12_STRUCT_GETTER_SETTER(D3D12_PLACED_SUBRESOURCE_FOOTPRINT, Footprint, D3D12_SUBRESOURCE_FOOTPRINT);
PYDX12_GETSETTERS(D3D12_PLACED_SUBRESOURCE_FOOTPRINT) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_PLACED_SUBRESOURCE_FOOTPRINT, Offset),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_PLACED_SUBRESOURCE_FOOTPRINT, Footprint),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE_WITH_REFS(D3D12_TEXTURE_COPY_LOCATION);
PYDX12_ADD_REFS(D3D12_TEXTURE_COPY_LOCATION) { PYDX12_COM_ADD(pResource); }
PYDX12_RELEASE_REFS(D3D12_TEXTURE_COPY_LOCATION) { PYDX12_COM_RELEASE(pResource); }
PYDX12_COM_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, ID3D12Resource, pResource);
PYDX12_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, Type, LongLong, D3D12_TEXTURE_COPY_TYPE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, PlacedFootprint, D3D12_PLACED_SUBRESOURCE_FOOTPRINT);
PYDX12_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, SubresourceIndex, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_TEXTURE_COPY_LOCATION) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, pResource),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, Type),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, PlacedFootprint),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_TEXTURE_COPY_LOCATION, SubresourceIndex),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE_WITH_REFS(D3D12_RESOURCE_UAV_BARRIER);
PYDX12_ADD_REFS(D3D12_RESOURCE_UAV_BARRIER) { PYDX12_COM_ADD(pResource); }
PYDX12_RELEASE_REFS(D3D12_RESOURCE_UAV_BARRIER) { PYDX12_COM_RELEASE(pResource); }
PYDX12_COM_GETTER_SETTER(D3D12_RESOURCE_UAV_BARRIER, ID3D12Resource, pResource);
PYDX12_GETSETTERS(D3D12_RESOURCE_UAV_BARRIER) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_UAV_BARRIER, pResource),
	{NULL}  /* Sentinel */
};


PYDX12_TYPE_WITH_REFS(D3D12_RESOURCE_ALIASING_BARRIER);
PYDX12_ADD_REFS(D3D12_RESOURCE_ALIASING_BARRIER) { PYDX12_COM_ADD(pResourceBefore); PYDX12_COM_ADD(pResourceAfter); }
PYDX12_RELEASE_REFS(D3D12_RESOURCE_ALIASING_BARRIER) { PYDX12_COM_RELEASE(pResourceBefore); PYDX12_COM_RELEASE(pResourceAfter); }
PYDX12_COM_GETTER_SETTER(D3D12_RESOURCE_ALIASING_BARRIER, ID3D12Resource, pResourceBefore);
PYDX12_COM_GETTER_SETTER(D3D12_RESOURCE_ALIASING_BARRIER, ID3D12Resource, pResourceAfter);
PYDX12_GETSETTERS(D3D12_RESOURCE_ALIASING_BARRIER) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_ALIASING_BARRIER, pResourceBefore),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_ALIASING_BARRIER, pResourceAfter),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE_WITH_REFS(D3D12_RESOURCE_TRANSITION_BARRIER);
PYDX12_ADD_REFS(D3D12_RESOURCE_TRANSITION_BARRIER) { PYDX12_COM_ADD(pResource); }
PYDX12_RELEASE_REFS(D3D12_RESOURCE_TRANSITION_BARRIER) { PYDX12_COM_RELEASE(pResource); }
PYDX12_COM_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, ID3D12Resource, pResource);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, Subresource, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, StateBefore, LongLong, D3D12_RESOURCE_STATES);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, StateAfter, LongLong, D3D12_RESOURCE_STATES);
PYDX12_GETSETTERS(D3D12_RESOURCE_TRANSITION_BARRIER) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, pResource),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, Subresource),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, StateBefore),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_TRANSITION_BARRIER, StateAfter),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE(D3D12_RESOURCE_BARRIER);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Type, LongLong, D3D12_RESOURCE_BARRIER_TYPE);
PYDX12_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Flags, LongLong, D3D12_RESOURCE_BARRIER_FLAGS);
PYDX12_STRUCT_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Transition, D3D12_RESOURCE_TRANSITION_BARRIER);
PYDX12_STRUCT_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Aliasing, D3D12_RESOURCE_ALIASING_BARRIER);
PYDX12_STRUCT_GETTER_SETTER(D3D12_RESOURCE_BARRIER, UAV, D3D12_RESOURCE_UAV_BARRIER);
PYDX12_GETSETTERS(D3D12_RESOURCE_BARRIER) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Type),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Flags),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Transition),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_BARRIER, Aliasing),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RESOURCE_BARRIER, UAV),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE(D3D12_VERTEX_BUFFER_VIEW);
PYDX12_GETTER_SETTER(D3D12_VERTEX_BUFFER_VIEW, BufferLocation, UnsignedLongLong, D3D12_GPU_VIRTUAL_ADDRESS);
PYDX12_GETTER_SETTER(D3D12_VERTEX_BUFFER_VIEW, SizeInBytes, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_VERTEX_BUFFER_VIEW, StrideInBytes, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_VERTEX_BUFFER_VIEW) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VERTEX_BUFFER_VIEW, BufferLocation),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VERTEX_BUFFER_VIEW, SizeInBytes),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VERTEX_BUFFER_VIEW, StrideInBytes),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE(D3D12_INDEX_BUFFER_VIEW);
PYDX12_GETTER_SETTER(D3D12_INDEX_BUFFER_VIEW, BufferLocation, UnsignedLongLong, D3D12_GPU_VIRTUAL_ADDRESS);
PYDX12_GETTER_SETTER(D3D12_INDEX_BUFFER_VIEW, SizeInBytes, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_INDEX_BUFFER_VIEW, Format, LongLong, DXGI_FORMAT);
PYDX12_GETSETTERS(D3D12_INDEX_BUFFER_VIEW) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INDEX_BUFFER_VIEW , BufferLocation),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INDEX_BUFFER_VIEW , SizeInBytes),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INDEX_BUFFER_VIEW , Format),
	{NULL}  /* Sentinel */
};

static PyObject* pydx12_ID3D12Resource_Map(pydx12_ID3D12Resource* self, PyObject* args)
{
	UINT sub_resource = 0;
	PyObject* py_read_range = NULL;
	if (!PyArg_ParseTuple(args, "|IO", &sub_resource, &py_read_range))
		return NULL;

	PYDX12_ARG_CHECK_NONE(D3D12_RANGE, read_range);

	ID3D12Device* device = NULL;
	PYDX12_COM_CALL_HRESULT(ID3D12Resource, GetDevice, __uuidof(ID3D12Device), (void**)&device);

	D3D12_RESOURCE_DESC resource_desc = PYDX12_COM_CALL(GetDesc);
	UINT64 base_offset = 0;
	if (read_range && read_range->Begin < read_range->End)
		base_offset = read_range->Begin;

	UINT64 mem_size = 0;
	device->GetCopyableFootprints(&resource_desc, sub_resource, 1, base_offset, NULL, NULL, NULL, &mem_size);
	if (!mem_size)
	{
		return PyErr_Format(PyExc_Exception, "unable to retrieve ID3D12Resource size");
	}

	if (read_range && read_range->Begin < read_range->End)
	{
		UINT64 delta = read_range->End - read_range->Begin;
		if (delta < mem_size)
		{
			mem_size = delta;
		}
	}

	if (!self->memory_view_list)
	{
		self->memory_view_list = PyList_New(0);
	}

	char* mem = NULL;

	PYDX12_COM_CALL_HRESULT(ID3D12Resource, Map, sub_resource, read_range, (void**)&mem);

	PyObject* py_memory_view = PyMemoryView_FromMemory(mem, (Py_ssize_t)mem_size, PyBUF_WRITE);
	if (!py_memory_view)
	{
		return PyErr_Format(PyExc_Exception, "unable to create the Python memoryview");
	}

	PyList_Append(self->memory_view_list, py_memory_view);
	Py_DECREF(py_memory_view);

	return PyWeakref_NewProxy(py_memory_view, NULL);
}

static PyObject* pydx12_ID3D12Resource_Unmap(pydx12_ID3D12Resource* self, PyObject* args)
{
	UINT sub_resource = 0;
	PyObject* py_written_range;
	if (!PyArg_ParseTuple(args, "|IO", &sub_resource, &py_written_range))
		return NULL;

	PYDX12_ARG_CHECK_NONE(D3D12_RANGE, written_range);

	if (!self->memory_view_list || PyList_Size(self->memory_view_list) == 0)
	{
		return PyErr_Format(PyExc_Exception, "nothing to Unmap");
	}

	PySequence_DelItem(self->memory_view_list, PyList_Size(self->memory_view_list) - 1);

	Py_RETURN_NONE;
}

static void pydx12_ID3D12Resource_dealloc_wrapper(pydx12_ID3D12Resource* self)
{
	Py_XDECREF(self->memory_view_list);
	pydx12_ID3D12Resource_dealloc(self);
}

static PyObject* pydx12_ID3D12Resource_upload(pydx12_ID3D12Resource* self, PyObject* args)
{
	Py_buffer view;
	UINT sub_resource = 0;
	if (!PyArg_ParseTuple(args, "y*|I", &view, &sub_resource))
		return NULL;

	ID3D12Device* device = NULL;
	PYDX12_COM_CALL_HRESULT(ID3D12Resource, GetDevice, __uuidof(ID3D12Device), (void**)&device);

	D3D12_RESOURCE_DESC resource_desc = PYDX12_COM_CALL(GetDesc);

	UINT64 mem_size = 0;
	device->GetCopyableFootprints(&resource_desc, sub_resource, 1, 0, NULL, NULL, NULL, &mem_size);
	if (!mem_size)
	{
		PyBuffer_Release(&view);
		return PyErr_Format(PyExc_Exception, "unable to retrieve ID3D12Resource size");
	}

	if ((UINT64)view.len > mem_size)
	{
		PyBuffer_Release(&view);
		return PyErr_Format(PyExc_ValueError, "supplied buffer is too big: %llu bytes available in the subresource", mem_size);
	}

	char* mem;
	if (self->com_ptr->Map(sub_resource, NULL, (void**)&mem) != S_OK)
	{
		PyBuffer_Release(&view);
		return PyErr_Format(PyExc_Exception, "ID3D12Resource::Map");
	}

	memcpy(mem, view.buf, view.len);

	PYDX12_COM_CALL(Unmap, sub_resource, NULL);

	PyBuffer_Release(&view);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Resource_download(pydx12_ID3D12Resource* self, PyObject* args)
{
	UINT sub_resource = 0;
	if (!PyArg_ParseTuple(args, "|I", &sub_resource))
		return NULL;

	ID3D12Device* device = NULL;
	PYDX12_COM_CALL_HRESULT(ID3D12Resource, GetDevice, __uuidof(ID3D12Device), (void**)&device);

	D3D12_RESOURCE_DESC resource_desc = PYDX12_COM_CALL(GetDesc);

	UINT64 mem_size = 0;
	device->GetCopyableFootprints(&resource_desc, sub_resource, 1, 0, NULL, NULL, NULL, &mem_size);
	if (!mem_size)
	{
		return PyErr_Format(PyExc_Exception, "unable to retrieve ID3D12Resource size");
	}

	char* mem;
	PYDX12_COM_CALL_HRESULT(ID3D12Resource, Map, sub_resource, NULL, (void**)&mem);

	PyObject* py_bytes = PyBytes_FromStringAndSize(mem, mem_size);

	PYDX12_COM_CALL(Unmap, sub_resource, NULL);

	return py_bytes;
}

static PyObject* pydx12_ID3D12Resource_GetGPUVirtualAddress(pydx12_ID3D12Resource* self, PyObject* args)
{
	return PyLong_FromUnsignedLongLong(self->com_ptr->GetGPUVirtualAddress());
}

static PyObject* pydx12_ID3D12Resource_GetDesc(pydx12_ID3D12Resource* self)
{
	D3D12_RESOURCE_DESC desc = self->com_ptr->GetDesc();
	return pydx12_D3D12_RESOURCE_DESC_instantiate(&desc, NULL, NULL);
}

PYDX12_METHODS(ID3D12Resource) = {
	{"Map", (PyCFunction)pydx12_ID3D12Resource_Map, METH_VARARGS, "Gets a CPU pointer to the specified subresource in the resource"},
	{"Unmap", (PyCFunction)pydx12_ID3D12Resource_Unmap, METH_VARARGS, "Invalidates the CPU pointer to the specified subresource in the resource"},
	{"GetGPUVirtualAddress", (PyCFunction)pydx12_ID3D12Resource_GetGPUVirtualAddress, METH_VARARGS, "This method returns the GPU virtual address of a buffer resource"},
	{"GetDesc", (PyCFunction)pydx12_ID3D12Resource_GetDesc, METH_NOARGS, "Gets the resource description"},
	{"upload", (PyCFunction)pydx12_ID3D12Resource_upload, METH_VARARGS, "upload a python buffer to the specified subresource"},
	{"download", (PyCFunction)pydx12_ID3D12Resource_download, METH_VARARGS, "download a python bytes object from the specified subresource"},
	{NULL} /* Sentinel */
};

int pydx12_init_resource(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D12_RANGE);

	PYDX12_REGISTER_STRUCT(D3D12_RESOURCE_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_HEAP_PROPERTIES);
	PYDX12_REGISTER_STRUCT(D3D12_CLEAR_VALUE);
	PYDX12_REGISTER_STRUCT(D3D12_VERTEX_BUFFER_VIEW);
	PYDX12_REGISTER_STRUCT(D3D12_INDEX_BUFFER_VIEW);

	PYDX12_REGISTER_STRUCT(D3D12_SUBRESOURCE_FOOTPRINT);
	PYDX12_REGISTER_STRUCT(D3D12_PLACED_SUBRESOURCE_FOOTPRINT);

	PYDX12_REGISTER_STRUCT(D3D12_TEXTURE_COPY_LOCATION);

	PYDX12_REGISTER_STRUCT(D3D12_RESOURCE_UAV_BARRIER);
	PYDX12_REGISTER_STRUCT(D3D12_RESOURCE_ALIASING_BARRIER);
	PYDX12_REGISTER_STRUCT(D3D12_RESOURCE_TRANSITION_BARRIER);

	PYDX12_REGISTER_STRUCT(D3D12_RESOURCE_BARRIER);

	pydx12_ID3D12ResourceType.tp_methods = pydx12_ID3D12Resource_methods;
	pydx12_ID3D12ResourceType.tp_dealloc = (destructor)pydx12_ID3D12Resource_dealloc_wrapper;
	PYDX12_REGISTER_COM(ID3D12Resource, ID3D12Pageable);

	PYDX12_ENUM(D3D12_RESOURCE_DIMENSION_UNKNOWN);
	PYDX12_ENUM(D3D12_RESOURCE_DIMENSION_BUFFER);
	PYDX12_ENUM(D3D12_RESOURCE_DIMENSION_TEXTURE1D);
	PYDX12_ENUM(D3D12_RESOURCE_DIMENSION_TEXTURE2D);
	PYDX12_ENUM(D3D12_RESOURCE_DIMENSION_TEXTURE3D);

	PYDX12_ENUM(D3D12_TEXTURE_LAYOUT_UNKNOWN);
	PYDX12_ENUM(D3D12_TEXTURE_LAYOUT_ROW_MAJOR);
	PYDX12_ENUM(D3D12_TEXTURE_LAYOUT_64KB_UNDEFINED_SWIZZLE);
	PYDX12_ENUM(D3D12_TEXTURE_LAYOUT_64KB_STANDARD_SWIZZLE);

	PYDX12_ENUM(D3D12_RESOURCE_FLAG_NONE);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_DENY_SHADER_RESOURCE);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_ALLOW_CROSS_ADAPTER);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_ALLOW_SIMULTANEOUS_ACCESS);
	PYDX12_ENUM(D3D12_RESOURCE_FLAG_VIDEO_DECODE_REFERENCE_ONLY);

	PYDX12_ENUM(D3D12_HEAP_TYPE_DEFAULT);
	PYDX12_ENUM(D3D12_HEAP_TYPE_UPLOAD);
	PYDX12_ENUM(D3D12_HEAP_TYPE_READBACK);
	PYDX12_ENUM(D3D12_HEAP_TYPE_CUSTOM);

	PYDX12_ENUM(D3D12_CPU_PAGE_PROPERTY_UNKNOWN);
	PYDX12_ENUM(D3D12_CPU_PAGE_PROPERTY_NOT_AVAILABLE);
	PYDX12_ENUM(D3D12_CPU_PAGE_PROPERTY_WRITE_COMBINE);
	PYDX12_ENUM(D3D12_CPU_PAGE_PROPERTY_WRITE_BACK);

	PYDX12_ENUM(D3D12_MEMORY_POOL_UNKNOWN);
	PYDX12_ENUM(D3D12_MEMORY_POOL_L0);
	PYDX12_ENUM(D3D12_MEMORY_POOL_L1);

	PYDX12_ENUM(D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX);
	PYDX12_ENUM(D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT);

	PYDX12_ENUM(D3D12_RESOURCE_BARRIER_TYPE_TRANSITION);
	PYDX12_ENUM(D3D12_RESOURCE_BARRIER_TYPE_ALIASING);
	PYDX12_ENUM(D3D12_RESOURCE_BARRIER_TYPE_UAV);

	PYDX12_ENUM(D3D12_RESOURCE_BARRIER_FLAG_NONE);
	PYDX12_ENUM(D3D12_RESOURCE_BARRIER_FLAG_BEGIN_ONLY);
	PYDX12_ENUM(D3D12_RESOURCE_BARRIER_FLAG_END_ONLY);

	return 0;
}