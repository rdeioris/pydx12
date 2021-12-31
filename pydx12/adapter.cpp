#include "pydx12.h"

PYDX12_IMPORT(LUID);
PYDX12_IMPORT_COM(IDXGIObject);

PYDX12_TYPE(DXGI_ADAPTER_DESC);
PYDX12_WSTRING_GETTER(DXGI_ADAPTER_DESC, Description);
PYDX12_GETTER(DXGI_ADAPTER_DESC, VendorId, UnsignedLong);
PYDX12_GETTER(DXGI_ADAPTER_DESC, DeviceId, UnsignedLong);
PYDX12_GETTER(DXGI_ADAPTER_DESC, SubSysId, UnsignedLong);
PYDX12_GETTER(DXGI_ADAPTER_DESC, Revision, UnsignedLong);
PYDX12_GETTER(DXGI_ADAPTER_DESC, DedicatedVideoMemory, UnsignedLongLong);
PYDX12_GETTER(DXGI_ADAPTER_DESC, DedicatedSystemMemory, UnsignedLongLong);
PYDX12_GETTER(DXGI_ADAPTER_DESC, SharedSystemMemory, UnsignedLongLong);
PYDX12_STRUCT_GETTER(DXGI_ADAPTER_DESC, AdapterLuid, LUID);
PYDX12_GETSETTERS(DXGI_ADAPTER_DESC) = {
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, Description),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, VendorId),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, DeviceId),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, SubSysId),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, Revision),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, DedicatedVideoMemory),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, DedicatedSystemMemory),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, SharedSystemMemory),
	PYDX12_DECLARE_GETTER(DXGI_ADAPTER_DESC, AdapterLuid),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_COM(IDXGIAdapter);

static PyObject* pydx12_IDXGIAdapter_GetDesc(pydx12_IDXGIAdapter* self, void* closure)
{
	DXGI_ADAPTER_DESC desc;
	if (self->com_ptr->GetDesc(&desc) != S_OK)
	{
		Py_RETURN_NONE;
	}
	return pydx12_DXGI_ADAPTER_DESC_instantiate(&desc, NULL, NULL);
}

PYDX12_METHODS(IDXGIAdapter) = {
	{"GetDesc", (PyCFunction)pydx12_IDXGIAdapter_GetDesc, METH_NOARGS, "Get Adapter description"},
	{NULL}  /* Sentinel */
};

int pydx12_init_adapter(PyObject* m)
{
	pydx12_IDXGIAdapterType.tp_methods = pydx12_IDXGIAdapter_methods;
	PYDX12_REGISTER_COM(IDXGIAdapter, IDXGIObject);

	PYDX12_REGISTER_STRUCT(DXGI_ADAPTER_DESC);

	return 0;
}