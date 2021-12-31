#include "pydx12.h"

PYDX12_IMPORT_COM(IDXGIAdapter);
PYDX12_IMPORT_COM(IDXGIFactory);
PYDX12_IMPORT_COM(IDXGIFactory1);
PYDX12_IMPORT_COM(IDXGIFactory2);
PYDX12_IMPORT_COM(ID3D12Device);
PYDX12_IMPORT_COM(ID3DBlob);

PYDX12_IMPORT(D3D12_VERSIONED_ROOT_SIGNATURE_DESC);

int pydx12_init_dxgi(PyObject* m);
int pydx12_init_adapter(PyObject* m);
int pydx12_init_luid(PyObject* m);
int pydx12_init_device(PyObject* m);
int pydx12_init_resource(PyObject* m);
int pydx12_init_signature(PyObject* m);
int pydx12_init_queue(PyObject* m);
int pydx12_init_message(PyObject* m);
int pydx12_init_swapchain(PyObject* m);
int pydx12_init_fence(PyObject* m);
int pydx12_init_descriptor(PyObject* m);
int pydx12_init_shader(PyObject* m);
int pydx12_init_pipeline(PyObject* m);

PYDX12_TYPE_COM(IUnknown);
PYDX12_TYPE_COM(IDXGIObject);
PYDX12_TYPE_COM(ID3D12Object);
PYDX12_TYPE_COM(IDXGIDeviceSubObject);

static PyObject* pydx12_CreateDXGIFactory(PyObject* self, PyObject* args)
{
	IDXGIFactory* factory;
	if (CreateDXGIFactory(__uuidof(IDXGIFactory), (void**)&factory) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create IDXGIFactory");
	}

	return pydx12_IDXGIFactory_instantiate(factory, false);
}

static PyObject* pydx12_CreateDXGIFactory1(PyObject* self, PyObject* args)
{
	IDXGIFactory1* factory;
	if (CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)&factory) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create IDXGIFactory1");
	}

	return pydx12_IDXGIFactory1_instantiate(factory, false);
}

static PyObject* pydx12_CreateDXGIFactory2(PyObject* self, PyObject* args)
{
	UINT flags;
	if (!PyArg_ParseTuple(args, "I", &flags))
		return NULL;

	IDXGIFactory2* factory;
	if (CreateDXGIFactory2(flags, __uuidof(IDXGIFactory2), (void**)&factory) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create IDXGIFactory2");
	}

	return pydx12_IDXGIFactory2_instantiate(factory, false);
}

static PyObject* pydx12_D3D12CreateDevice(PyObject* self, PyObject* args)
{
	PyObject* py_adapter = NULL;
	D3D_FEATURE_LEVEL feature_level = D3D_FEATURE_LEVEL_12_0;
	if (!PyArg_ParseTuple(args, "O|L", &py_adapter, &feature_level))
		return NULL;

	IDXGIAdapter* adapter = pydx12_IDXGIAdapter_check(py_adapter);
	if (!adapter)
		return PyErr_Format(PyExc_TypeError, "first argument must be an IDXGIAdapter");

	ID3D12Device* device;
	if (D3D12CreateDevice(adapter, feature_level, __uuidof(ID3D12Device), (void**)&device) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create ID3D12Device");
	}

	return pydx12_ID3D12Device_instantiate(device, false);
}

static PyObject* pydx12_D3DCompile(PyObject* self, PyObject* args)
{
	PyObject* py_src_data;
	const char* source_name = NULL;
	PyObject* py_defines;
	PyObject* py_include;
	const char* entry_point = NULL;
	const char* target = "xx_x_x"; // shut up the warning ;)
	UINT flags1;
	UINT flags2;

	D3D_FEATURE_LEVEL feature_level = D3D_FEATURE_LEVEL_12_0;
	if (!PyArg_ParseTuple(args, "OzOOzsLL", &py_src_data, &source_name, &py_defines, &py_include, &entry_point, &target, &flags1, &flags2))
		return NULL;

	if (!PyUnicode_Check(py_src_data))
	{
		return PyErr_Format(PyExc_ValueError, "expcted a Unicode object");
	}

	Py_ssize_t src_data_size = 0;
	LPCVOID* src_data = (LPCVOID*)PyUnicode_AsUTF8AndSize(py_src_data, &src_data_size);

	ID3DBlob* code = NULL;
	ID3DBlob* error_msgs = NULL;
	if (D3DCompile(src_data, src_data_size, source_name, NULL, NULL, entry_point, target, flags1, flags2, &code, &error_msgs) != S_OK)
	{
		if (error_msgs)
		{
			PyObject* py_error_msgs = PyUnicode_FromStringAndSize((const char*)error_msgs->GetBufferPointer(), error_msgs->GetBufferSize());
			error_msgs->Release();
			PyErr_Format(PyExc_ValueError, "%U", py_error_msgs);
			Py_DECREF(py_error_msgs);
			return NULL;
		}
		return PyErr_Format(PyExc_ValueError, "unable to compile shader");
	}

	return PYDX12_COM_INSTANTIATE(ID3DBlob, code, false);
}

static PyObject* pydx12_D3D12SerializeVersionedRootSignature(PyObject* self, PyObject* args)
{
	PyObject* py_root_signature;
	if (!PyArg_ParseTuple(args, "O", &py_root_signature))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_VERSIONED_ROOT_SIGNATURE_DESC, root_signature);

	ID3DBlob* blob = NULL;
	ID3DBlob* error_blob = NULL;
	if (D3D12SerializeVersionedRootSignature(root_signature, &blob, &error_blob) != S_OK)
	{
		if (error_blob)
		{
			PyObject* py_error_msgs = PyUnicode_FromStringAndSize((const char*)error_blob->GetBufferPointer(), error_blob->GetBufferSize());
			error_blob->Release();
			PyErr_Format(PyExc_ValueError, "%U", py_error_msgs);
			Py_DECREF(py_error_msgs);
			return NULL;
		}
		return PyErr_Format(PyExc_ValueError, "unable to create the root signature");
	}

	return PYDX12_COM_INSTANTIATE(ID3DBlob, blob, false);
}

static PyMethodDef pydx12_methods[] =
{
	{"CreateDXGIFactory", pydx12_CreateDXGIFactory, METH_VARARGS, "Creates a DXGI 1.0 factory that you can use to generate other DXGI objects"},
	{"CreateDXGIFactory1", pydx12_CreateDXGIFactory1, METH_VARARGS, "Creates a DXGI 1.1 factory that you can use to generate other DXGI objects"},
	{"CreateDXGIFactory2", pydx12_CreateDXGIFactory2, METH_VARARGS, "Creates a DXGI 1.3 factory that you can use to generate other DXGI objects"},
	{"D3D12CreateDevice", pydx12_D3D12CreateDevice, METH_VARARGS, "Creates a device that represents the display adapter"},
	{"D3DCompile", pydx12_D3DCompile, METH_VARARGS, "Compile HLSL code or an effect file into bytecode for a given target"},
	{"D3D12SerializeVersionedRootSignature", pydx12_D3D12SerializeVersionedRootSignature, METH_VARARGS, "Serializes a root signature of any version that can be passed to ID3D12Device::CreateRootSignature"},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef pydx12_module =
{
	PyModuleDef_HEAD_INIT,
	"api",
	NULL,
	-1,
	pydx12_methods
};

static PyObject* pydx12_ID3D12Object_SetName(pydx12_ID3D12Object* self, PyObject* args)
{
	PyObject* py_name;
	if (!PyArg_ParseTuple(args, "O", &py_name))
		return NULL;

	PYDX12_UNICODE_CHECK(name, py_name);

	PYDX12_COM_CALL_HRESULT_AND_FREE(name, ID3D12Object, SetName, name);

	Py_RETURN_NONE;
}


PYDX12_METHODS(ID3D12Object) = {
	{"SetName", (PyCFunction)pydx12_ID3D12Object_SetName, METH_VARARGS, "Associates a name with the device object. This name is for use in debug diagnostics and tools"},
	{NULL}  /* Sentinel */
};

static int pydx12_init_base(PyObject* m)
{
	PYDX12_REGISTER_COM_BASE(IUnknown);
	PYDX12_REGISTER_COM(IDXGIObject, IUnknown);

	pydx12_ID3D12ObjectType.tp_methods = pydx12_ID3D12Object_methods;
	PYDX12_REGISTER_COM(ID3D12Object, IUnknown);
	PYDX12_REGISTER_COM(IDXGIDeviceSubObject, IDXGIObject);
	return 0;
}

PyMODINIT_FUNC
PyInit_api(void)
{
	ID3D12Debug* debug;
	D3D12GetDebugInterface(__uuidof(ID3D12Debug), (void**)&debug);
	debug->EnableDebugLayer();

	PyObject* m = PyModule_Create(&pydx12_module);
	if (m == NULL)
		return NULL;

	if (pydx12_init_base(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_dxgi(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_adapter(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_luid(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_device(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_resource(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_signature(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_queue(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_message(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_swapchain(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_fence(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_descriptor(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_shader(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	if (pydx12_init_pipeline(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	return m;
}