#include "pydx12.h"

PYDX12_IMPORT_HANDLE(Event);
PYDX12_IMPORT_COM(ID3D12Pageable);

PYDX12_TYPE_COM(ID3D12Fence);

static PyObject* pydx12_ID3D12Fence_GetCompletedValue(pydx12_ID3D12Fence* self)
{
	return PyLong_FromUnsignedLongLong(PYDX12_COM_CALL(GetCompletedValue));
}

static PyObject* pydx12_ID3D12Fence_Signal(pydx12_ID3D12Fence* self, PyObject* args)
{
	UINT64 value = 0;
	if (!PyArg_ParseTuple(args, "K", &value))
		return NULL;
	
	PYDX12_COM_CALL_HRESULT(ID3D12Fence, Signal, value);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Fence_SetEventOnCompletion(pydx12_ID3D12Fence* self, PyObject* args)
{
	UINT64 value;
	PyObject* py_handle_event;
	if (!PyArg_ParseTuple(args, "KO", &value, &py_handle_event))
		return NULL;

	PYDX12_ARG_CHECK_HANDLE(Event, handle_event);

	PYDX12_COM_CALL_HRESULT(ID3D12Fence, SetEventOnCompletion, value, handle_event);

	Py_RETURN_NONE;
}

PYDX12_METHODS(ID3D12Fence) = {
	{"GetCompletedValue", (PyCFunction)pydx12_ID3D12Fence_GetCompletedValue, METH_NOARGS, "Gets the current value of the fence"},
	{"Signal", (PyCFunction)pydx12_ID3D12Fence_Signal, METH_VARARGS, "Sets the fence to the specified value"},
	{"SetEventOnCompletion", (PyCFunction)pydx12_ID3D12Fence_SetEventOnCompletion, METH_VARARGS, "Specifies an event that should be fired when the fence reaches a certain value"},
	{NULL}  /* Sentinel */
};

int pydx12_init_fence(PyObject* m)
{
	pydx12_ID3D12FenceType.tp_methods = pydx12_ID3D12Fence_methods;
	PYDX12_REGISTER_COM(ID3D12Fence, ID3D12Pageable);

	PYDX12_ENUM(D3D12_FENCE_FLAG_NONE);
	PYDX12_ENUM(D3D12_FENCE_FLAG_SHARED);
	PYDX12_ENUM(D3D12_FENCE_FLAG_SHARED_CROSS_ADAPTER);
	PYDX12_ENUM(D3D12_FENCE_FLAG_NON_MONITORED);

	return 0;
}