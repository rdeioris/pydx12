#include "pydx12.h"

PYDX12_IMPORT_COM(ID3D12Pageable);

PYDX12_TYPE_COM(ID3D12Fence);

static PyObject* pydx12_ID3D12Fence_GetCompletedValue(pydx12_ID3D12Fence* self, PyObject* args)
{
	return PyLong_FromUnsignedLongLong(PYDX12_COM_CALL(GetCompletedValue));
}

PYDX12_METHODS(ID3D12Fence) = {
	{"GetCompletedValue", (PyCFunction)pydx12_ID3D12Fence_GetCompletedValue, METH_VARARGS, "Gets the current value of the fence"},
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