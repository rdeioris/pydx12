#include "pydx12.h"

PYDX12_TYPE(D3D_SHADER_MACRO);
PYDX12_STRING_GETTER_SETTER(D3D_SHADER_MACRO, Name);
PYDX12_STRING_GETTER_SETTER(D3D_SHADER_MACRO, Definition);
PYDX12_GETSETTERS(D3D_SHADER_MACRO) = {
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(D3D_SHADER_MACRO, Name),
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(D3D_SHADER_MACRO, Definition),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_SHADER_BYTECODE);
PYDX12_BUFFER_GETTER_SETTER(D3D12_SHADER_BYTECODE, pShaderBytecode, BytecodeLength);
PYDX12_GETTER_SETTER(D3D12_SHADER_BYTECODE, BytecodeLength, UnsignedLongLong, SIZE_T);
PYDX12_GETSETTERS(D3D12_SHADER_BYTECODE) = {
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(D3D12_SHADER_BYTECODE, pShaderBytecode),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SHADER_BYTECODE, BytecodeLength),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_COM(ID3DBlob);

static PyObject* pydx12_ID3DBlob_GetBufferPointer(pydx12_ID3DBlob* self)
{
	return PyLong_FromUnsignedLongLong((unsigned long long)self->com_ptr->GetBufferPointer());
}

static PyObject* pydx12_ID3DBlob_GetBufferSize(pydx12_ID3DBlob* self)
{
	return PyLong_FromUnsignedLongLong(self->com_ptr->GetBufferSize());
}

static PyObject* pydx12_ID3DBlob_to_bytes(pydx12_ID3DBlob* self)
{
	return PyBytes_FromStringAndSize((const char*)self->com_ptr->GetBufferPointer(), self->com_ptr->GetBufferSize());
}

static PyObject* pydx12_ID3DBlob_to_bytearray(pydx12_ID3DBlob* self)
{
	return PyByteArray_FromStringAndSize((const char*)self->com_ptr->GetBufferPointer(), self->com_ptr->GetBufferSize());
}

static int pydx12_ID3DBlob_get_buffer(pydx12_ID3DBlob* exporter, Py_buffer* view, int flags)
{
	LPVOID buffer_ptr = exporter->com_ptr->GetBufferPointer();
	if (!buffer_ptr)
	{
		PyErr_SetString(PyExc_ValueError, "invalid buffer");
		return -1;
	}

	PyBuffer_FillInfo(view, (PyObject*)exporter, buffer_ptr, exporter->com_ptr->GetBufferSize(), 0, flags);
	return 0;
}

static void pydx12_ID3DBlob_release_buffer(pydx12_ID3DBlob* exporter, Py_buffer* view)
{
}

static PyBufferProcs pydx12_ID3DBlob_as_buffer = {
#if PY_MAJOR_VERSION < 3
	nullptr, nullptr, nullptr, nullptr,
#endif
	(getbufferproc)pydx12_ID3DBlob_get_buffer,
	(releasebufferproc)pydx12_ID3DBlob_release_buffer
};

PYDX12_METHODS(ID3DBlob) = {
	{"GetBufferPointer", (PyCFunction)pydx12_ID3DBlob_GetBufferPointer, METH_NOARGS, "Retrieves a pointer to the blob's data"},
	{"GetBufferSize", (PyCFunction)pydx12_ID3DBlob_GetBufferSize, METH_NOARGS, "Retrieves the size, in bytes, of the blob's data"},
	{"to_bytes", (PyCFunction)pydx12_ID3DBlob_to_bytes, METH_NOARGS, "returns blob's data as bytes object"},
	{"to_bytearray", (PyCFunction)pydx12_ID3DBlob_to_bytearray, METH_NOARGS, "returns blob's data as bytearray object"},
	{NULL} /* Sentinel */
};

int pydx12_init_shader(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D_SHADER_MACRO);

	PYDX12_REGISTER_STRUCT(D3D12_SHADER_BYTECODE);

	pydx12_ID3DBlobType.tp_methods = pydx12_ID3DBlob_methods;
	pydx12_ID3DBlobType.tp_as_buffer = &pydx12_ID3DBlob_as_buffer;
	PYDX12_REGISTER_COM(ID3DBlob, IUnknown);

	PYDX12_ENUM(D3DCOMPILE_DEBUG);
	PYDX12_ENUM(D3DCOMPILE_SKIP_VALIDATION);
	PYDX12_ENUM(D3DCOMPILE_SKIP_OPTIMIZATION);
	PYDX12_ENUM(D3DCOMPILE_PACK_MATRIX_ROW_MAJOR);
	PYDX12_ENUM(D3DCOMPILE_PACK_MATRIX_COLUMN_MAJOR);
	PYDX12_ENUM(D3DCOMPILE_PARTIAL_PRECISION);
	PYDX12_ENUM(D3DCOMPILE_FORCE_VS_SOFTWARE_NO_OPT);
	PYDX12_ENUM(D3DCOMPILE_FORCE_PS_SOFTWARE_NO_OPT);
	PYDX12_ENUM(D3DCOMPILE_NO_PRESHADER);
	PYDX12_ENUM(D3DCOMPILE_AVOID_FLOW_CONTROL);
	PYDX12_ENUM(D3DCOMPILE_PREFER_FLOW_CONTROL);
	PYDX12_ENUM(D3DCOMPILE_ENABLE_STRICTNESS);
	PYDX12_ENUM(D3DCOMPILE_ENABLE_BACKWARDS_COMPATIBILITY);
	PYDX12_ENUM(D3DCOMPILE_IEEE_STRICTNESS);
	PYDX12_ENUM(D3DCOMPILE_OPTIMIZATION_LEVEL0);
	PYDX12_ENUM(D3DCOMPILE_OPTIMIZATION_LEVEL1);
	PYDX12_ENUM(D3DCOMPILE_OPTIMIZATION_LEVEL2);
	PYDX12_ENUM(D3DCOMPILE_OPTIMIZATION_LEVEL3);
	PYDX12_ENUM(D3DCOMPILE_RESERVED16);
	PYDX12_ENUM(D3DCOMPILE_RESERVED17);
	PYDX12_ENUM(D3DCOMPILE_WARNINGS_ARE_ERRORS);
	PYDX12_ENUM(D3DCOMPILE_RESOURCES_MAY_ALIAS);
	PYDX12_ENUM(D3DCOMPILE_ENABLE_UNBOUNDED_DESCRIPTOR_TABLES);
	PYDX12_ENUM(D3DCOMPILE_ALL_RESOURCES_BOUND);
	PYDX12_ENUM(D3DCOMPILE_DEBUG_NAME_FOR_SOURCE);
	PYDX12_ENUM(D3DCOMPILE_DEBUG_NAME_FOR_BINARY);

	PYDX12_ENUM(D3DCOMPILE_EFFECT_CHILD_EFFECT);
	PYDX12_ENUM(D3DCOMPILE_EFFECT_ALLOW_SLOW_OPS);
	return 0;
}