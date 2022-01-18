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
PYDX12_BUFFER_GETTER_SETTER(D3D12_SHADER_BYTECODE, pShaderBytecode, void);
PYDX12_GETTER_SETTER(D3D12_SHADER_BYTECODE, BytecodeLength, UnsignedLongLong, SIZE_T);
PYDX12_GETSETTERS(D3D12_SHADER_BYTECODE) = {
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(D3D12_SHADER_BYTECODE, pShaderBytecode),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_SHADER_BYTECODE, BytecodeLength),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(DxcDefine);
PYDX12_WSTRING_GETTER_SETTER(DxcDefine, Name);
PYDX12_WSTRING_GETTER_SETTER(DxcDefine, Value);
PYDX12_GETSETTERS(DxcDefine) = {
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(DxcDefine, Name),
	PYDX12_DECLARE_GETTER_SETTER_CHUNK(DxcDefine, Value),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_COM(ID3DBlob);
PYDX12_TYPE_COM(IDxcLibrary);
PYDX12_TYPE_COM(IDxcCompiler);
PYDX12_TYPE_COM(IDxcBlob);
PYDX12_TYPE_COM(IDxcBlobEncoding);
PYDX12_TYPE_COM(IDxcOperationResult);

extern DxcCreateInstanceProc DxcCreateInstanceLazy;
extern DxcCreateInstanceProc DxcCreateInstanceDXIL;



static PyObject* pydx12_ID3DBlob_GetBufferPointer(pydx12_COM<ID3DBlob>* self)
{
	return PyLong_FromUnsignedLongLong((unsigned long long)self->com_ptr->GetBufferPointer());
}

static PyObject* pydx12_ID3DBlob_GetBufferSize(pydx12_COM<ID3DBlob>* self)
{
	return PyLong_FromUnsignedLongLong(self->com_ptr->GetBufferSize());
}

static PyObject* pydx12_ID3DBlob_to_bytes(pydx12_COM<ID3DBlob>* self)
{
	return PyBytes_FromStringAndSize((const char*)self->com_ptr->GetBufferPointer(), self->com_ptr->GetBufferSize());
}

static PyObject* pydx12_ID3DBlob_to_bytearray(pydx12_COM<ID3DBlob>* self)
{
	return PyByteArray_FromStringAndSize((const char*)self->com_ptr->GetBufferPointer(), self->com_ptr->GetBufferSize());
}

static int pydx12_ID3DBlob_get_buffer(pydx12_COM<ID3DBlob>* exporter, Py_buffer* view, int flags)
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

static void pydx12_ID3DBlob_release_buffer(pydx12_COM<ID3DBlob>* exporter, Py_buffer* view)
{
}

static PyBufferProcs pydx12_ID3DBlob_as_buffer = {
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

static PyObject* pydx12_IDxcBlob_GetBufferPointer(pydx12_COM<IDxcBlob>* self)
{
	return PyLong_FromUnsignedLongLong((unsigned long long)self->com_ptr->GetBufferPointer());
}

static PyObject* pydx12_IDxcBlob_GetBufferSize(pydx12_COM<IDxcBlob>* self)
{
	printf("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^IDxcBlob buffer size: %llu\n", self->com_ptr->GetBufferSize());
	return PyLong_FromUnsignedLongLong(self->com_ptr->GetBufferSize());
}

PYDX12_METHODS(IDxcBlob) = {
	{"GetBufferPointer", (PyCFunction)pydx12_IDxcBlob_GetBufferPointer, METH_NOARGS, "Retrieves a pointer to the blob's data"},
	{"GetBufferSize", (PyCFunction)pydx12_IDxcBlob_GetBufferSize, METH_NOARGS, "Retrieves the size, in bytes, of the blob's data"},
	{NULL} /* Sentinel */
};

static PyObject* pydx12_IDxcLibrary_CreateBlobWithEncodingOnHeapCopy(pydx12_COM<IDxcLibrary>* self, PyObject* args)
{
	Py_buffer view;
	UINT32 code_page = CP_UTF8;
	if (!PyArg_ParseTuple(args, "y*|I", &view, &code_page))
		return NULL;

	IDxcBlobEncoding* blob_encoding;
	PYDX12_COM_CALL_HRESULT_AND_BUFFER_RELEASE(view, IDxcLibrary, CreateBlobWithEncodingOnHeapCopy, view.buf, (UINT32)view.len, code_page, &blob_encoding);

	return pydx12_com_instantiate<IDxcBlobEncoding>(blob_encoding, false);
}

PYDX12_METHODS(IDxcLibrary) = {
	{"CreateBlobWithEncodingOnHeapCopy", (PyCFunction)pydx12_IDxcLibrary_CreateBlobWithEncodingOnHeapCopy, METH_VARARGS, "IDxcLibrary::CreateBlobWithEncodingOnHeapCopy()"},
	{NULL} /* Sentinel */
};

static PyObject* pydx12_IDxcCompiler_Compile(pydx12_COM<IDxcCompiler>* self, PyObject* args)
{
	PyObject* py_blob;
	PyObject* py_source_name;
	PyObject* py_entry_point;
	PyObject* py_target;
	if (!PyArg_ParseTuple(args, "OOOO", &py_blob, &py_source_name, &py_entry_point, &py_target))
		return NULL;

	PYDX12_ARG_CHECK(IDxcBlob, blob);
	PYDX12_UNICODE_CHECK_NONE(source_name);
	PYDX12_UNICODE_CHECK(entry_point);
	PYDX12_UNICODE_CHECK(target);

	IDxcOperationResult* result;
	HRESULT ret = self->com_ptr->Compile(blob, source_name, entry_point, target, NULL, 0, NULL, 0, NULL, &result);
	if (FAILED(ret))
	{
		PYDX12_EXCEPTION(IDxcCompiler, Compile);
	}

	result->GetStatus(&ret);
	if (FAILED(ret))
	{
		IDxcBlobEncoding* errors_blob;
		ret = result->GetErrorBuffer(&errors_blob);
		result->Release();
		if (FAILED(ret) || !errors_blob)
		{
			PYDX12_EXCEPTION(IDxcOperationResult, GetErrorBuffer);
		}
		BOOL known = FALSE;
		UINT32 codepage;
		errors_blob->GetEncoding(&known, &codepage);
		PyObject* py_error_msg = PyUnicode_FromString("unable to compile shader");
		if (known)
		{
			if (codepage == CP_UTF8)
			{
				py_error_msg = PyUnicode_FromString((const char*)errors_blob->GetBufferPointer());
			}
			else if (codepage == CP_WINUNICODE)
			{
				py_error_msg = PyUnicode_FromWideChar((const wchar_t*)errors_blob->GetBufferPointer(), -1);
			}
		}
		errors_blob->Release();
		if (!py_error_msg)
		{
			return NULL;
		}
		PyErr_Format(PyExc_Exception, "%U", py_error_msg);
		Py_DECREF(py_error_msg);
		return NULL;
	}

	IDxcBlob* compiled_blob;
	PYDX12_CALL_HRESULT(result->GetResult, &compiled_blob);

	IDxcValidator* validator;
	DxcCreateInstanceDXIL(CLSID_DxcValidator, __uuidof(IDxcValidator), (void**)&validator);
	validator->Validate(compiled_blob, DxcValidatorFlags_InPlaceEdit, &result);

	return pydx12_com_instantiate<IDxcBlob>(compiled_blob, false);
}

static int pydx12_IDxcBlob_get_buffer(pydx12_COM<IDxcBlob>* exporter, Py_buffer* view, int flags)
{
	LPVOID buffer_ptr = exporter->com_ptr->GetBufferPointer();
	if (!buffer_ptr)
	{
		PyErr_SetString(PyExc_ValueError, "invalid buffer");
		return -1;
	}

	uint8_t* data = (uint8_t*)exporter->com_ptr->GetBufferPointer();
	uint64_t total = 0;
	for (size_t i = 0; i < exporter->com_ptr->GetBufferSize(); i++)
	{
		total += data[i];
	}
	printf("################################################################################################# TOTAL: %llu\n", total);

	PyBuffer_FillInfo(view, (PyObject*)exporter, buffer_ptr, exporter->com_ptr->GetBufferSize(), 0, flags);
	return 0;
}

static void pydx12_IDxcBlob_release_buffer(pydx12_COM<IDxcBlob>* exporter, Py_buffer* view)
{
}

static PyBufferProcs pydx12_IDxcBlob_as_buffer = {
	(getbufferproc)pydx12_IDxcBlob_get_buffer,
	(releasebufferproc)pydx12_IDxcBlob_release_buffer
};

PYDX12_METHODS(IDxcCompiler) = {
	{"Compile", (PyCFunction)pydx12_IDxcCompiler_Compile, METH_VARARGS, "IDxcCompiler::Compile()"},
	{NULL} /* Sentinel */
};

int pydx12_init_shader(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D_SHADER_MACRO);

	PYDX12_REGISTER_STRUCT(D3D12_SHADER_BYTECODE);

	pydx12_ID3DBlob_Type.tp_methods = pydx12_ID3DBlob_methods;
	pydx12_ID3DBlob_Type.tp_as_buffer = &pydx12_ID3DBlob_as_buffer;
	PYDX12_REGISTER_COM(ID3DBlob, IUnknown);

	pydx12_IDxcLibrary_Type.tp_methods = pydx12_IDxcLibrary_methods;
	PYDX12_REGISTER_COM(IDxcLibrary, IUnknown);

	pydx12_IDxcCompiler_Type.tp_methods = pydx12_IDxcCompiler_methods;
	PYDX12_REGISTER_COM(IDxcCompiler, IUnknown);

	pydx12_IDxcBlob_Type.tp_methods = pydx12_IDxcBlob_methods;
	pydx12_IDxcBlob_Type.tp_as_buffer = &pydx12_IDxcBlob_as_buffer;
	PYDX12_REGISTER_COM(IDxcBlob, IUnknown);

	PYDX12_REGISTER_COM(IDxcBlobEncoding, IDxcBlob);

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

	PYDX12_ENUM(CP_UTF8);
	PYDX12_ENUM(CP_WINUNICODE);

	return 0;
}