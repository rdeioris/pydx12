#include "pydx12.h"

PYDX12_IMPORT(DXGI_SAMPLE_DESC);
PYDX12_IMPORT_COM(IDXGIDeviceSubObject);
PYDX12_IMPORT_COM(ID3D12Resource);

PYDX12_TYPE(DXGI_SWAP_CHAIN_DESC1);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Width, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Height, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Format, LongLong, DXGI_FORMAT);
PYDX12_BOOL_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Stereo);
PYDX12_STRUCT_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, SampleDesc, DXGI_SAMPLE_DESC);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, BufferUsage, LongLong, DXGI_USAGE);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, BufferCount, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Scaling, LongLong, DXGI_SCALING);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, SwapEffect, LongLong, DXGI_SWAP_EFFECT);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, AlphaMode, LongLong, DXGI_ALPHA_MODE);
PYDX12_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Flags, UnsignedLong, UINT);
PYDX12_GETSETTERS(DXGI_SWAP_CHAIN_DESC1) = {
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Width),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Height),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Format),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Stereo),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, SampleDesc),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, BufferUsage),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, BufferCount),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Scaling),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, SwapEffect),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, AlphaMode),
	PYDX12_DECLARE_GETTER_SETTER(DXGI_SWAP_CHAIN_DESC1, Flags),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_COM(IDXGISwapChain);
PYDX12_TYPE_COM(IDXGISwapChain1);
PYDX12_TYPE_COM(IDXGISwapChain2);
PYDX12_TYPE_COM(IDXGISwapChain3);
PYDX12_TYPE_COM(IDXGISwapChain4);

static PyObject* pydx12_IDXGISwapChain_GetBuffer(pydx12_IDXGISwapChain* self, PyObject* args)
{
	UINT buffer_index;
	if (!PyArg_ParseTuple(args, "I", &buffer_index))
		return NULL;

	ID3D12Resource* resource;
	if (self->com_ptr->GetBuffer(buffer_index, __uuidof(ID3D12Resource), (void**)&resource) != S_OK)
	{
		return PyErr_Format(PyExc_Exception, "unable to retrieve SwapChain buffer %u", buffer_index);
	}

	return pydx12_ID3D12Resource_instantiate(resource, false);
}

static PyObject* pydx12_IDXGISwapChain_Present(pydx12_IDXGISwapChain* self, PyObject* args)
{
	UINT sync_interval;
	UINT flags = 0;
	if (!PyArg_ParseTuple(args, "I|I", &sync_interval, &flags))
		return NULL;

	if (self->com_ptr->Present(sync_interval, flags) != S_OK)
	{
		return PyErr_Format(PyExc_Exception, "unable to Present() SwapChain buffer");
	}

	Py_RETURN_NONE;
}

static PyObject* pydx12_IDXGISwapChain_ResizeBuffers(pydx12_IDXGISwapChain* self, PyObject* args)
{
	UINT buffer_count;
	UINT width;
	UINT height;
	DXGI_FORMAT new_format = DXGI_FORMAT_UNKNOWN;
	UINT flags = 0;
	if (!PyArg_ParseTuple(args, "III|LI", &buffer_count, &width, &height, &new_format, &flags))
		return NULL;

	PYDX12_COM_CALL_HRESULT(IDXGISwapChain, ResizeBuffers, buffer_count, width, height, new_format, flags);

	Py_RETURN_NONE;
}

static PyObject* pydx12_IDXGISwapChain3_GetCurrentBackBufferIndex(pydx12_IDXGISwapChain3* self)
{
	return PyLong_FromUnsignedLong(self->com_ptr->GetCurrentBackBufferIndex());
}

PYDX12_METHODS(IDXGISwapChain) = {
	{"GetBuffer", (PyCFunction)pydx12_IDXGISwapChain_GetBuffer, METH_VARARGS, "Accesses one of the swap-chain's back buffers."},
	{"Present", (PyCFunction)pydx12_IDXGISwapChain_Present, METH_VARARGS, "Presents a rendered image to the user"},
	{"ResizeBuffers", (PyCFunction)pydx12_IDXGISwapChain_ResizeBuffers, METH_VARARGS, "Changes the swap chain's back buffer size, format, and number of buffers"},
	{NULL}  /* Sentinel */
};

PYDX12_METHODS(IDXGISwapChain3) = {
	{"GetCurrentBackBufferIndex", (PyCFunction)pydx12_IDXGISwapChain3_GetCurrentBackBufferIndex, METH_NOARGS, "Gets the index of the swap chain's current back buffer"},
	{NULL}  /* Sentinel */
};

int pydx12_init_swapchain(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(DXGI_SWAP_CHAIN_DESC1);

	pydx12_IDXGISwapChainType.tp_methods = pydx12_IDXGISwapChain_methods;
	PYDX12_REGISTER_COM(IDXGISwapChain, IDXGIDeviceSubObject);

	PYDX12_REGISTER_COM(IDXGISwapChain1, IDXGISwapChain);
	PYDX12_REGISTER_COM(IDXGISwapChain2, IDXGISwapChain1);

	pydx12_IDXGISwapChain3Type.tp_methods = pydx12_IDXGISwapChain3_methods;
	PYDX12_REGISTER_COM(IDXGISwapChain3, IDXGISwapChain2);

	PYDX12_REGISTER_COM(IDXGISwapChain4, IDXGISwapChain3);

	PYDX12_ENUM(DXGI_SCALING_STRETCH);
	PYDX12_ENUM(DXGI_SCALING_NONE);
	PYDX12_ENUM(DXGI_SCALING_ASPECT_RATIO_STRETCH);

	PYDX12_ENUM(DXGI_SWAP_EFFECT_DISCARD);
	PYDX12_ENUM(DXGI_SWAP_EFFECT_SEQUENTIAL);
	PYDX12_ENUM(DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL);
	PYDX12_ENUM(DXGI_SWAP_EFFECT_FLIP_DISCARD);

	PYDX12_ENUM(DXGI_ALPHA_MODE_UNSPECIFIED);
	PYDX12_ENUM(DXGI_ALPHA_MODE_PREMULTIPLIED);
	PYDX12_ENUM(DXGI_ALPHA_MODE_STRAIGHT);
	PYDX12_ENUM(DXGI_ALPHA_MODE_IGNORE);
	PYDX12_ENUM(DXGI_ALPHA_MODE_FORCE_DWORD);

	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_NONPREROTATED);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_GDI_COMPATIBLE);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_RESTRICTED_CONTENT);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_RESTRICT_SHARED_RESOURCE_DRIVER);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_DISPLAY_ONLY);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_FRAME_LATENCY_WAITABLE_OBJECT);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_FOREGROUND_LAYER);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_FULLSCREEN_VIDEO);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_YUV_VIDEO);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_HW_PROTECTED);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_ALLOW_TEARING);
	PYDX12_ENUM(DXGI_SWAP_CHAIN_FLAG_RESTRICTED_TO_ALL_HOLOGRAPHIC_DISPLAYS);

	return 0;
}