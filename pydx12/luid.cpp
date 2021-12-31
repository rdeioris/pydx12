#include "pydx12.h"

PYDX12_TYPE(LUID);
PYDX12_GETTER_SETTER(LUID, LowPart, UnsignedLong, DWORD);
PYDX12_GETTER_SETTER(LUID, HighPart, Long, LONG);
PYDX12_GETSETTERS(LUID) = {
	PYDX12_DECLARE_GETTER_SETTER(LUID, LowPart),
	PYDX12_DECLARE_GETTER_SETTER(LUID, HighPart),
	{ NULL }  /* Sentinel */
};

int pydx12_init_luid(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(LUID);
	return 0;
}