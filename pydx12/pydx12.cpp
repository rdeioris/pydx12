#include "pydx12.h"

PYDX12_IMPORT_COM(IDXGIAdapter);
PYDX12_IMPORT_COM(IDXGIFactory);
PYDX12_IMPORT_COM(IDXGIFactory1);
PYDX12_IMPORT_COM(IDXGIFactory2);
PYDX12_IMPORT_COM(IDXGIFactory3);
PYDX12_IMPORT_COM(IDXGIFactory4);
PYDX12_IMPORT_COM(IDXGIFactory5);
PYDX12_IMPORT_COM(IDXGIFactory6);
PYDX12_IMPORT_COM(IDXGIFactory7);
PYDX12_IMPORT_COM(ID3D12Device);
PYDX12_IMPORT_COM(ID3D12Device1);
PYDX12_IMPORT_COM(ID3D12Device2);
PYDX12_IMPORT_COM(ID3D12Device3);
PYDX12_IMPORT_COM(ID3D12Device4);
PYDX12_IMPORT_COM(ID3D12Device5);
PYDX12_IMPORT_COM(ID3D12Device6);
PYDX12_IMPORT_COM(ID3D12Device7);
PYDX12_IMPORT_COM(ID3D12Device8);
PYDX12_IMPORT_COM(ID3DBlob);
PYDX12_IMPORT_COM(IXAudio2);

PYDX12_IMPORT(D3D12_VERSIONED_ROOT_SIGNATURE_DESC);
PYDX12_IMPORT(D3D_SHADER_MACRO);

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
int pydx12_init_audio(PyObject* m);

#include <queue>
#include <tuple>

PYDX12_TYPE_HANDLE(Event, HANDLE);
PYDX12_TYPE_HANDLE(Window, HWND, std::queue<std::tuple<UINT, WPARAM, LPARAM>> messages);

PYDX12_TYPE_COM(IUnknown);
PYDX12_TYPE_COM(IDXGIObject);
PYDX12_TYPE_COM(ID3D12Object);
PYDX12_TYPE_COM(IDXGIDeviceSubObject);
PYDX12_TYPE_COM(ID3D12Debug);


static PyObject* pydx12_CreateDXGIFactory(PyObject* self, PyObject* args)
{
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory7, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory6, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory5, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory4, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory3, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory2, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory1, CreateDXGIFactory);
	PYDX12_INTERFACE_CREATE_NO_ARGS_LAST(IDXGIFactory, CreateDXGIFactory);
}

static PyObject* pydx12_CreateDXGIFactory1(PyObject* self, PyObject* args)
{
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory7, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory6, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory5, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory4, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory3, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory2, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS(IDXGIFactory1, CreateDXGIFactory1);
	PYDX12_INTERFACE_CREATE_NO_ARGS_LAST(IDXGIFactory, CreateDXGIFactory1);
}

static PyObject* pydx12_CreateDXGIFactory2(PyObject* self, PyObject* args)
{
	UINT flags = 0;
	if (!PyArg_ParseTuple(args, "|I", &flags))
		return NULL;

	PYDX12_INTERFACE_CREATE(IDXGIFactory7, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE(IDXGIFactory6, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE(IDXGIFactory5, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE(IDXGIFactory4, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE(IDXGIFactory3, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE(IDXGIFactory2, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE(IDXGIFactory1, CreateDXGIFactory2, flags);
	PYDX12_INTERFACE_CREATE_LAST(IDXGIFactory, CreateDXGIFactory2, flags);
}

static PyObject* pydx12_XAudio2Create(PyObject* self, PyObject* args)
{
	UINT32 flags = 0;
	XAUDIO2_PROCESSOR processor = XAUDIO2_DEFAULT_PROCESSOR;
	if (!PyArg_ParseTuple(args, "|IL", &flags, &processor))
		return NULL;

	IXAudio2* xaudio2;
	PYDX12_CALL_HRESULT(XAudio2Create, &xaudio2, flags, processor);

	return PYDX12_COM_INSTANTIATE(IXAudio2, xaudio2, false);
}

static PyObject* pydx12_D3D12CreateDevice(PyObject* self, PyObject* args)
{
	PyObject* py_adapter = NULL;
	D3D_FEATURE_LEVEL feature_level = D3D_FEATURE_LEVEL_12_0;

	if (!PyArg_ParseTuple(args, "O|L", &py_adapter, &feature_level))
		return nullptr;

	IDXGIAdapter* adapter = pydx12_IDXGIAdapter_check(py_adapter);
	if (!adapter)
		return PyErr_Format(PyExc_TypeError, "first argument must be an IDXGIAdapter");

	PYDX12_INTERFACE_CREATE(ID3D12Device8, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device7, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device6, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device5, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device4, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device3, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device2, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE(ID3D12Device1, D3D12CreateDevice, adapter, feature_level);
	PYDX12_INTERFACE_CREATE_LAST(ID3D12Device, D3D12CreateDevice, adapter, feature_level);
}

static PyObject* pydx12_D3DCompile(PyObject* self, PyObject* args)
{
	PyObject* py_src_data;
	const char* source_name = NULL;
	PyObject* py_defines;
	PyObject* py_include;
	const char* entry_point = NULL;
	const char* target = "xx_x_x"; // shut up the warning ;)
	UINT flags1 = 0;
	UINT flags2 = 0;

	D3D_FEATURE_LEVEL feature_level = D3D_FEATURE_LEVEL_12_0;
	if (!PyArg_ParseTuple(args, "OzOOzs|LL", &py_src_data, &source_name, &py_defines, &py_include, &entry_point, &target, &flags1, &flags2))
		return NULL;

	if (!PyUnicode_Check(py_src_data))
	{
		return PyErr_Format(PyExc_ValueError, "expected a Unicode object");
	}

	PYDX12_ARG_ITER_CHECK_NONE(D3D_SHADER_MACRO, defines, true);

	Py_ssize_t src_data_size = 0;
	LPCVOID* src_data = (LPCVOID*)PyUnicode_AsUTF8AndSize(py_src_data, &src_data_size);

	ID3DBlob* code = NULL;
	ID3DBlob* error_msgs = NULL;
	if (D3DCompile(src_data, src_data_size, source_name, defines, NULL, entry_point, target, flags1, flags2, &code, &error_msgs) != S_OK)
	{
		if (defines)
			PyMem_Free(defines);

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

	if (defines)
		PyMem_Free(defines);

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

static PyObject* pydx12_D3D12GetDebugInterface(PyObject* self)
{
	ID3D12Debug* debug;
	D3D12GetDebugInterface(__uuidof(ID3D12Debug), (void**)&debug);

	return PYDX12_COM_INSTANTIATE(ID3D12Debug, debug, false);
}

static void pydx12_Event_dealloc(pydx12_Event* self)\
{
	if (self->handle)
		CloseHandle(self->handle);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static int pydx12_Event_init(pydx12_Event* self, PyObject* args, PyObject* kwds)
{
	self->handle = CreateEvent(NULL, FALSE, FALSE, NULL);

	return 0;
}

static PyObject* pydx12_Event_wait(pydx12_Event* self, PyObject* args)
{
	DWORD milliseconds = INFINITE;
	if (!PyArg_ParseTuple(args, "|I", &milliseconds))
		return NULL;

	Py_BEGIN_ALLOW_THREADS;

	WaitForSingleObject(self->handle, milliseconds);

	Py_END_ALLOW_THREADS;

	Py_RETURN_NONE;
}

PYDX12_METHODS(Event) = {
	{"wait", (PyCFunction)pydx12_Event_wait, METH_VARARGS, "WaitForSingleObject() wrapper"},
	{NULL}  /* Sentinel */
};

static int pydx12_Window_init(pydx12_Window* self, PyObject* args, PyObject* kwds)
{
	PyObject* py_title;
	int width;
	int height;
	if (!PyArg_ParseTuple(args, "Oii", &py_title, &width, &height))
		return NULL;

	if (!PyUnicode_Check(py_title))
	{
		PyErr_SetString(PyExc_ValueError, "title must be a unicode object");
		return -1;
	}

	wchar_t* title = PyUnicode_AsWideCharString(py_title, NULL);
	if (!title)
	{
		return -1;
	}

	self->handle = CreateWindowExW(
		WS_EX_APPWINDOW,
		L"pydx12",
		title,
		WS_OVERLAPPED | WS_SYSMENU | WS_CAPTION | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_THICKFRAME | WS_BORDER,
		CW_USEDEFAULT, CW_USEDEFAULT,
		width, height,
		NULL,
		NULL, GetModuleHandle(NULL), NULL);

	PyMem_Free(title);

	if (!self->handle)
	{
		PyErr_SetString(PyExc_Exception, "unable to create Window");
		return -1;
	}

	SetWindowLongPtr(self->handle, GWLP_USERDATA, (LONG_PTR)self);

	ShowWindow(self->handle, SW_SHOW);

	return 0;
}

static void pydx12_Window_dealloc(pydx12_Window* self)\
{
	if (self->handle)
		DestroyWindow(self->handle);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* pydx12_Window_show(pydx12_Window* self, PyObject* args)
{
	ShowWindow(self->handle, SW_SHOW);

	Py_RETURN_NONE;
}

static PyObject* pydx12_Window_hide(pydx12_Window* self, PyObject* args)
{
	ShowWindow(self->handle, SW_HIDE);

	Py_RETURN_NONE;
}

static PyObject* pydx12_Window_minimize(pydx12_Window* self, PyObject* args)
{
	ShowWindow(self->handle, SW_MINIMIZE);

	Py_RETURN_NONE;
}

static PyObject* pydx12_Window_maximize(pydx12_Window* self, PyObject* args)
{
	ShowWindow(self->handle, SW_MAXIMIZE);

	Py_RETURN_NONE;
}

static PyObject* pydx12_Window_dequeue(pydx12_Window* self, PyObject* args)
{
	MSG message;
	Py_BEGIN_ALLOW_THREADS;
	while (PeekMessage(&message, NULL, 0, 0, PM_REMOVE))
	{
		TranslateMessage(&message);
		DispatchMessage(&message);
	}
	Py_END_ALLOW_THREADS;

	PyObject* py_list = PyList_New(0);

	while (!self->messages.empty())
	{
		auto& message = self->messages.front();
		PyObject* py_message = Py_BuildValue("(IKL)", std::get<0>(message), (unsigned long long)std::get<1>(message), (long long)std::get<2>(message));
		PyList_Append(py_list, py_message);
		Py_DECREF(py_message);
		self->messages.pop();
	}

	return py_list;
}

static PyObject* pydx12_Window_set_title(pydx12_Window* self, PyObject* args)
{
	PyObject* py_title;
	if (!PyArg_ParseTuple(args, "O", &py_title))
		return NULL;

	if (!PyUnicode_Check(py_title))
	{
		return PyErr_Format(PyExc_ValueError, "title must be a unicode object");
	}

	wchar_t* title = PyUnicode_AsWideCharString(py_title, NULL);
	if (!title)
	{
		return NULL;
	}

	SetWindowTextW(self->handle, title);

	PyMem_Free(title);

	Py_RETURN_NONE;
}

PYDX12_METHODS(Window) = {
	{"show", (PyCFunction)pydx12_Window_show, METH_VARARGS, "Show the Window"},
	{"hide", (PyCFunction)pydx12_Window_hide, METH_VARARGS, "Hide the Window"},
	{"minimize", (PyCFunction)pydx12_Window_minimize, METH_VARARGS, "Minimize the Window"},
	{"maximize", (PyCFunction)pydx12_Window_maximize, METH_VARARGS, "Maximize the Window"},
	{"dequeue", (PyCFunction)pydx12_Window_dequeue, METH_VARARGS, "Dequeue events from the Window"},
	{"set_title", (PyCFunction)pydx12_Window_set_title, METH_VARARGS, "Set the Window title"},
	{NULL}  /* Sentinel */
};

static PyObject* pydx12_QueryPerformanceCounter(PyObject* self, PyObject* args)
{
	LARGE_INTEGER counter;
	QueryPerformanceCounter(&counter);

	return PyLong_FromUnsignedLongLong(counter.QuadPart);
}

static PyObject* pydx12_QueryPerformanceFrequency(PyObject* self, PyObject* args)
{
	LARGE_INTEGER frequency;
	QueryPerformanceFrequency(&frequency);

	return PyLong_FromUnsignedLongLong(frequency.QuadPart);
}

static PyMethodDef pydx12_methods[] =
{
	{"CreateDXGIFactory", pydx12_CreateDXGIFactory, METH_VARARGS, "Creates a DXGI 1.0 factory that you can use to generate other DXGI objects"},
	{"CreateDXGIFactory1", pydx12_CreateDXGIFactory1, METH_VARARGS, "Creates a DXGI 1.1 factory that you can use to generate other DXGI objects"},
	{"CreateDXGIFactory2", pydx12_CreateDXGIFactory2, METH_VARARGS, "Creates a DXGI 1.3 factory that you can use to generate other DXGI objects"},
	{"D3D12CreateDevice", pydx12_D3D12CreateDevice, METH_VARARGS, "Creates a device that represents the display adapter"},
	{"D3DCompile", pydx12_D3DCompile, METH_VARARGS, "Compile HLSL code or an effect file into bytecode for a given target"},
	{"D3D12SerializeVersionedRootSignature", pydx12_D3D12SerializeVersionedRootSignature, METH_VARARGS, "Serializes a root signature of any version that can be passed to ID3D12Device::CreateRootSignature"},
	{"D3D12GetDebugInterface", (PyCFunction)pydx12_D3D12GetDebugInterface, METH_NOARGS, "Gets a debug interface"},
	{"QueryPerformanceCounter", (PyCFunction)pydx12_QueryPerformanceCounter, METH_NOARGS, "Retrieves the current value of the performance counter"},
	{"QueryPerformanceFrequency", (PyCFunction)pydx12_QueryPerformanceFrequency, METH_NOARGS, "Retrieves the frequency of the performance counter"},
	{"XAudio2Create", (PyCFunction)pydx12_XAudio2Create, METH_VARARGS, "Creates a new XAudio2 object and returns a pointer to its IXAudio2 interface"},
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


static PyObject* pydx12_ID3D12Debug_EnableDebugLayer(pydx12_ID3D12Debug* self)
{
	PYDX12_COM_CALL(EnableDebugLayer);
	Py_RETURN_NONE;
}


PYDX12_METHODS(ID3D12Debug) = {
	{"EnableDebugLayer", (PyCFunction)pydx12_ID3D12Debug_EnableDebugLayer, METH_NOARGS, "Enables the debug layer"},
	{NULL}  /* Sentinel */
};

static LRESULT pydx12_DefWindowProcW(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam)
{
	pydx12_Window* self = (pydx12_Window*)GetWindowLongPtr(hWnd, GWLP_USERDATA);
	if (self)
	{
		self->messages.push({ Msg, wParam, lParam });
	}
	return DefWindowProcW(hWnd, Msg, wParam, lParam);
}

static int pydx12_init_base(PyObject* m)
{
	CoInitializeEx(NULL, COINIT_MULTITHREADED);

	WNDCLASSW window_class = {};
	window_class.lpfnWndProc = pydx12_DefWindowProcW;
	window_class.hInstance = GetModuleHandle(NULL);
	window_class.lpszClassName = L"pydx12";

	if (!RegisterClassW(&window_class))
	{
		return -1;
	}

	pydx12_EventType.tp_methods = pydx12_Event_methods;
	PYDX12_REGISTER_HANDLE(Event);

	pydx12_WindowType.tp_methods = pydx12_Window_methods;
	PYDX12_REGISTER_HANDLE(Window);

	PYDX12_REGISTER_COM_BASE(IUnknown);
	PYDX12_REGISTER_COM(IDXGIObject, IUnknown);

	pydx12_ID3D12DebugType.tp_methods = pydx12_ID3D12Debug_methods;
	PYDX12_REGISTER_COM(ID3D12Debug, IUnknown);

	pydx12_ID3D12ObjectType.tp_methods = pydx12_ID3D12Object_methods;
	PYDX12_REGISTER_COM(ID3D12Object, IUnknown);
	PYDX12_REGISTER_COM(IDXGIDeviceSubObject, IDXGIObject);

	PYDX12_ENUM(WM_CLOSE);
	PYDX12_ENUM(WM_QUIT);
	PYDX12_ENUM(WM_KEYUP);
	PYDX12_ENUM(WM_KEYDOWN);

	return 0;
}

PyMODINIT_FUNC
PyInit_api(void)
{
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

	if (pydx12_init_audio(m))
	{
		Py_DECREF(m);
		return NULL;
	}

	return m;
}