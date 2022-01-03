#pragma once

#include <Python.h>
#include <dxgi1_4.h>
#include <d3d12.h>
#include <d3dcompiler.h>

#define PYDX12_TYPE_MEMBERS(t) static PyTypeObject pydx12_##t##Type = \
{\
	PyVarObject_HEAD_INIT(NULL, 0)\
	"pydx12." #t,              /* tp_name */ \
	sizeof(pydx12_##t),		   /* tp_basicsize */\
	0,                         /* tp_itemsize */\
	0,                         /* tp_dealloc */\
	0,                         /* tp_print */\
	0,                         /* tp_getattr */\
	0,                         /* tp_setattr */\
	0,                         /* tp_reserved */\
	0,                         /* tp_repr */\
	0,                         /* tp_as_number */\
	0,                         /* tp_as_sequence */\
	0,                         /* tp_as_mapping */\
	0,                         /* tp_hash  */\
	0,                         /* tp_call */\
	0,                         /* tp_str */\
	0,                         /* tp_getattro */\
	0,                         /* tp_setattro */\
	0,                         /* tp_as_buffer */\
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,        /* tp_flags */\
	#t,           /* tp_doc */\
}

typedef struct
{
	void* ptr;
	size_t number_of_items;
	void (*hook)(void*, const size_t);
} pydx12_allocated_chunk;

#define PYDX12_TYPE_INSTANTIATE(t) PyObject* pydx12_##t##_instantiate_with_size(t* data, PyObject* data_owner, IUnknown* com_owner, const size_t len)\
{\
	printf("allocing " #t " com_owner: %p\n", com_owner);\
	pydx12_##t* py_object = PyObject_New(pydx12_##t, &pydx12_##t##Type);\
	if (!py_object)\
	{\
		return NULL;\
	}\
	char* offset = (char*)py_object;\
	memset(offset + sizeof(PyObject), 0, sizeof(pydx12_##t) - sizeof(PyObject));\
	py_object->data_owner = data_owner;\
	py_object->data_len = len;\
	if (!data_owner)\
	{\
		py_object->data = (t*)PyMem_Malloc(len);\
		if (!py_object->data)\
			return NULL;\
		if (data)\
			*(py_object->data) = *data;\
	}\
	else\
	{\
		py_object->data = data;\
		Py_INCREF(data_owner);\
	}\
	if (com_owner)\
	{\
		com_owner->AddRef();\
		printf("[2] allocing " #t " com_owner: %p %p\n", py_object, com_owner);\
		py_object->com_owner = com_owner;\
	}\
	return (PyObject*)py_object;\
}\
PyObject* pydx12_##t##_instantiate(t* data, PyObject* data_owner, IUnknown* com_owner)\
{\
	return pydx12_##t##_instantiate_with_size(data, data_owner, com_owner, sizeof(t));\
}\
t* pydx12_##t##_get_data(PyObject* py_object)\
{\
	pydx12_##t##* pydx12_object = (pydx12_##t*)py_object;\
	return pydx12_object->data; \
}\
t* pydx12_##t##_check(PyObject* py_object)\
{\
	if (!PyObject_IsInstance(py_object, (PyObject*)&pydx12_##t##Type))\
	{\
		return NULL; \
	}\
	pydx12_##t##* pydx12_object = (pydx12_##t*)py_object; \
	return pydx12_object->data; \
}\
void pydx12_##t##_add_refs(t* data);\
void pydx12_##t##_release_refs(t* data);\
static void pydx12_##t##_dealloc(pydx12_##t* self)\
{\
	printf("dealloc " #t " %p %p\n", self, self->com_owner);\
	if (self->mem_list)\
	{\
		printf("about to clean %d items\n", self->mem_list_size);\
		for(size_t i = 0; i < self->mem_list_size;i++)\
		{\
				pydx12_allocated_chunk* allocated_chunk = &self->mem_list[i];\
				if (allocated_chunk->ptr)\
				{\
					printf("chunk at %p %p\n", allocated_chunk, allocated_chunk->hook); \
					allocated_chunk->hook(allocated_chunk->ptr, allocated_chunk->number_of_items); \
					PyMem_Free(allocated_chunk->ptr); \
				}\
		}\
		PyMem_Free(self->mem_list);\
	}\
	if (self->data)\
	{\
		pydx12_##t##_release_refs(self->data);\
		if (!self->data_owner)\
		{\
			PyMem_Free(self->data);\
		}\
		else\
		{\
			Py_DECREF(self->data_owner);\
		}\
	}\
	if (self->com_owner)\
		self->com_owner->Release();\
	if (self->weakreflist)\
		PyObject_ClearWeakRefs((PyObject*)self);\
	Py_TYPE(self)->tp_free((PyObject*)self);\
}\
static int pydx12_##t##_init(pydx12_##t* self, PyObject *args, PyObject *kwds)\
{\
	self->data = (t*)PyMem_Calloc(1, sizeof(t));\
	if (!self->data)\
	{\
		return -1;\
	}\
	self->data_owner = NULL;\
	if (pydx12_##t##Type.tp_getset && kwds != NULL && PyDict_Check(kwds) && PyDict_Size(kwds))\
	{\
		PyObject *py_key, *py_value;\
		Py_ssize_t pos = 0;\
		while (PyDict_Next(kwds, &pos, &py_key, &py_value))\
		{\
			const char* field = PyUnicode_AsUTF8(py_key);\
			int found = 0;\
			PyGetSetDef* getset = pydx12_##t##Type.tp_getset;\
			while (getset->name)\
			{\
				if (!strcmp(field, getset->name))\
				{\
					if (!getset->set)\
					{\
						PyErr_Format(PyExc_KeyError, "field %s is not writable", field);\
						return -1;\
					}\
					if (getset->set((PyObject*)self, py_value, getset->closure))\
					{\
						return -1;\
					}\
					found = 1;\
					break;\
				}\
				getset++;\
			}\
			if (!found)\
			{\
				PyErr_Format(PyExc_KeyError, "unknown field %s", field);\
				return -1;\
			}\
		}\
	}\
	return 0;\
}\
static PyObject* pydx12_##t##_sq_item(pydx12_##t* self, Py_ssize_t index)\
{\
	printf("getting index %lld\n", index);\
	if (PyObject* py_struct = pydx12_##t##_instantiate(self->data + index, (PyObject*)self, self->com_owner))\
	{\
		pydx12_##t##_add_refs(self->data + index);\
		return py_struct;\
	}\
	return NULL;\
}\
static PySequenceMethods pydx12_##t##_sequence_methods = {\
	NULL,\
	NULL,\
	NULL,\
	(ssizeargfunc)pydx12_##t##_sq_item\
};\
static PyObject* pydx12_##t##_get_fields(pydx12_##t* self)\
{\
	PyObject* py_list = PyList_New(0);\
	PyGetSetDef* getset = pydx12_##t##Type.tp_getset;\
	while (getset->name)\
	{\
		PyObject* py_name = PyUnicode_FromString(getset->name);\
		PyList_Append(py_list, py_name);\
		Py_DECREF(py_name);\
		getset++;\
	}\
	return py_list;\
}\
static PyObject* pydx12_##t##_to_dict(pydx12_##t* self)\
{\
	PyObject* py_dict = PyDict_New();\
	PyGetSetDef* getset = pydx12_##t##Type.tp_getset;\
	while (getset->name)\
	{\
		if (getset->get)\
		{\
			PyObject* py_value = getset->get((PyObject*)self, getset->closure);\
			if (!py_value)\
			{\
				Py_DECREF(py_dict);\
				return NULL;\
			}\
			PyDict_SetItemString(py_dict, getset->name, py_value);\
			Py_DECREF(py_value);\
		}\
		getset++;\
	}\
	return py_dict;\
}\
static PyObject* pydx12_##t##_to_bytes(pydx12_##t* self)\
{\
	if (!self->data)\
		Py_RETURN_NONE;\
	return PyBytes_FromStringAndSize((const char*)self->data, self->data_len);\
}\
static PyObject* pydx12_##t##_to_bytearray(pydx12_##t* self)\
{\
	if (!self->data)\
		Py_RETURN_NONE;\
	return PyByteArray_FromStringAndSize((const char*)self->data, self->data_len);\
}\
static PyObject* pydx12_##t##_get_tracked_refs(PyObject* cls)\
{\
	Py_INCREF(pydx12_##t##_refs_tracker);\
	return pydx12_##t##_refs_tracker;\
}\
static PyMethodDef pydx12_##t##_methods[] = {\
	{"get_fields", (PyCFunction)pydx12_##t##_get_fields, METH_NOARGS, "returns a list of structure's fields"},\
	{"to_dict", (PyCFunction)pydx12_##t##_to_dict, METH_NOARGS, "returns a dictionary representation of the structure"},\
	{"to_bytes", (PyCFunction)pydx12_##t##_to_bytes, METH_NOARGS, "returns structure's content as a bytes object"},\
	{"to_bytearray", (PyCFunction)pydx12_##t##_to_bytearray, METH_NOARGS, "returns structure's content as a bytearray object"},\
	{"get_tracked_refs", (PyCFunction)pydx12_##t##_get_tracked_refs, METH_NOARGS | METH_CLASS, "returns structure's type tracked references"},\
	{NULL}\
};\
void pydx12_##t##_track(unsigned long long addr, PyObject* py_object)\
{\
	PyObject* py_tracked_key = PyLong_FromUnsignedLongLong(addr);\
	PyObject* py_already_tracked_ref = PyDict_GetItem(pydx12_##t##_refs_tracker, py_tracked_key);\
	if (py_already_tracked_ref)\
	{\
		PyObject* py_ref_counter = PyTuple_GetItem(py_already_tracked_ref, 1);\
		unsigned long long ref_counter = PyLong_AsUnsignedLongLong(py_ref_counter);\
		printf("[already tracked] increasing address " #t " %p\n", addr);\
		PyTuple_SetItem(py_already_tracked_ref, 1, PyLong_FromUnsignedLongLong(ref_counter + 1));\
	}\
	else\
	{\
			PyObject* py_tracked_new_ref = PyTuple_New(2); \
			Py_INCREF(py_object); \
			PyTuple_SetItem(py_tracked_new_ref, 0, py_object); \
			PyTuple_SetItem(py_tracked_new_ref, 1, PyLong_FromUnsignedLongLong(1)); \
			printf("py_tracked_new_ref for " #t " %p %p\n", py_tracked_new_ref, py_object); \
			PyDict_SetItem(pydx12_##t##_refs_tracker, py_tracked_key, py_tracked_new_ref); \
			Py_DECREF(py_tracked_new_ref);\
			printf("tracking " #t " %p %p\n", addr, py_object);\
	}\
	Py_DECREF(py_tracked_key);\
}\
void pydx12_##t##_track_mem(unsigned long long addr)\
{\
	PyObject* py_tracked_key = PyLong_FromUnsignedLongLong(addr);\
	PyObject* py_already_tracked_ref = PyDict_GetItem(pydx12_##t##_refs_tracker, py_tracked_key);\
	if (py_already_tracked_ref)\
	{\
		unsigned long long ref_counter = PyLong_AsUnsignedLongLong(py_already_tracked_ref);\
		printf("[already tracked] increasing address " #t " %p\n", addr);\
		PyObject* py_new_ref = PyLong_FromUnsignedLongLong(ref_counter + 1);\
		PyDict_SetItem(pydx12_##t##_refs_tracker, py_tracked_key, py_new_ref);\
		Py_DECREF(py_new_ref);\
	}\
	else\
	{\
			PyObject* py_new_ref = PyLong_FromUnsignedLongLong(1); \
			PyDict_SetItem(pydx12_##t##_refs_tracker, py_tracked_key, py_new_ref); \
			Py_DECREF(py_new_ref); \
			printf("[MEM] tracking " #t " %p\n", addr); \
	}\
	Py_DECREF(py_tracked_key);\
}\
void pydx12_##t##_incref(unsigned long long addr)\
{\
	if (addr)\
	{\
		PyObject* py_tracked_key = PyLong_FromUnsignedLongLong(addr); \
		PyObject* py_tracked_ref = PyDict_GetItem(pydx12_##t##_refs_tracker, py_tracked_key); \
		if (py_tracked_ref)\
		{\
			if (PyLong_Check(py_tracked_ref))\
			{\
				PyObject* py_new_ref = PyLong_FromUnsignedLongLong(PyLong_AsUnsignedLong(py_tracked_ref) + 1); \
				PyDict_SetItem(pydx12_##t##_refs_tracker, py_tracked_key, py_new_ref); \
				Py_DECREF(py_new_ref); \
				printf("add tracking " #t " %p\n", addr); \
			}\
			else\
			{\
				PyObject* py_ref_counter = PyTuple_GetItem(py_tracked_ref, 1); \
				unsigned long long ref_counter = PyLong_AsUnsignedLongLong(py_ref_counter); \
				printf("INCREF " #t " %p\n", addr); \
				PyTuple_SetItem(py_tracked_ref, 1, PyLong_FromUnsignedLongLong(ref_counter + 1)); \
			}\
		}\
		Py_DECREF(py_tracked_key); \
	}\
}\
void pydx12_##t##_decref(unsigned long long addr)\
{\
	if (addr)\
	{\
		PyObject* py_tracked_key = PyLong_FromUnsignedLongLong((unsigned long long)addr);\
		PyObject* py_tracked_ref = PyDict_GetItem(pydx12_##t##_refs_tracker, py_tracked_key);\
		if (py_tracked_ref)\
		{\
			if (PyLong_Check(py_tracked_ref))\
			{\
				unsigned long long ref_counter = PyLong_AsUnsignedLongLong(py_tracked_ref);\
				ref_counter--;\
				if (ref_counter == 0)\
				{\
					PyDict_DelItem(pydx12_##t##_refs_tracker, py_tracked_key);\
					printf("[FINAL] destroyng mem address " #t " %p\n", addr);\
					PyMem_Free((void*)addr);\
				}\
				else\
				{\
					PyObject* py_new_ref = PyLong_FromUnsignedLongLong(ref_counter); \
					PyDict_SetItem(pydx12_##t##_refs_tracker, py_tracked_key, py_new_ref); \
					Py_DECREF(py_new_ref); \
					printf("DECREF " #t " %p %llu\n", addr, ref_counter); \
				}\
			}\
			else\
			{\
				PyObject* py_ref_counter = PyTuple_GetItem(py_tracked_ref, 1);\
				unsigned long long ref_counter = PyLong_AsUnsignedLongLong(py_ref_counter);\
				ref_counter--;\
				printf("decreasing address " #t " %p %llu\n", addr, ref_counter);\
				if (ref_counter == 0)\
				{\
						PyDict_DelItem(pydx12_##t##_refs_tracker, py_tracked_key);\
						printf("destroyng address " #t " %p\n", addr);\
				}\
				else\
				{\
					PyTuple_SetItem(py_tracked_ref, 1, PyLong_FromUnsignedLongLong(ref_counter));\
				}\
			}\
		}\
		Py_DECREF(py_tracked_key);\
	}\
}\
static void pydx12_##t##_cleanup(void* data, const size_t number_of_elements)\
{\
	printf("cleaning " #t " up %p\n", data);\
	t* items = (t*)data;\
	for(size_t i = 0; i < number_of_elements; i++)\
	{\
		pydx12_##t##_release_refs((t*)&items[i]);\
	}\
}

#define PYDX12_TYPE_INSTANTIATE_COM(t) PyObject* pydx12_##t##_instantiate(t* com_ptr, const bool add_ref)\
{\
	pydx12_##t* py_object = PyObject_New(pydx12_##t, &pydx12_##t##Type);\
	if (!py_object)\
	{\
		return NULL;\
	}\
	char* offset = (char*)py_object;\
	memset(offset + sizeof(PyObject), 0, sizeof(pydx12_##t) - sizeof(PyObject));\
	if (com_ptr && add_ref)\
	{\
		printf("AddRef() for " #t " : %p %ld\n", com_ptr, com_ptr->AddRef());\
	}\
	else\
	{\
		printf("NoRef for " #t " : %p\n", com_ptr);\
	}\
	py_object->com_ptr = com_ptr;\
	return (PyObject*)py_object;\
}\
t* pydx12_##t##_check(PyObject* py_object)\
{\
	if (!PyObject_IsInstance(py_object, (PyObject*)&pydx12_##t##Type))\
	{\
		return NULL; \
	}\
	pydx12_##t##* pydx12_object = (pydx12_##t*)py_object; \
	return pydx12_object->com_ptr; \
}\
static void pydx12_##t##_dealloc(pydx12_##t* self)\
{\
	if (self->com_ptr)\
	{\
		printf("com release for " #t " %p %ld\n", self->com_ptr, self->com_ptr->Release());\
	}\
	Py_TYPE(self)->tp_free((PyObject*)self);\
}\
static int pydx12_##t##_init(pydx12_##t* self, PyObject* args, PyObject* kwds)\
{\
	PyObject* py_unknown;\
	if (!PyArg_ParseTuple(args, "O", &py_unknown))\
	{\
		return -1;\
	}\
	IUnknown* unknown = pydx12_IUnknown_check(py_unknown);\
	if (!unknown)\
	{\
		PyErr_SetString(PyExc_ValueError, "expected a IUnknown");\
		return -1;\
	}\
	self->com_ptr = NULL;\
	if (unknown->QueryInterface<t>(&self->com_ptr) != S_OK)\
	{\
		PyErr_SetString(PyExc_ValueError, "QueryInterface<" #t "> failed");\
		return -1;\
	}\
	return 0;\
}\
PyTypeObject* pydx12_##t##_get_type()\
{\
	return (PyTypeObject*)&pydx12_##t##Type;\
}

#define PYDX12_TYPE_WITH_REFS(t, ...) typedef struct\
{\
	PyObject_HEAD\
	t* data;\
	size_t data_len;\
	PyObject* data_owner;\
	IUnknown* com_owner;\
	PyObject *weakreflist;\
	size_t mem_list_size;\
	pydx12_allocated_chunk *mem_list;\
	__VA_ARGS__;\
} pydx12_##t;\
static PyObject* pydx12_##t##_refs_tracker = NULL;\
PYDX12_TYPE_MEMBERS(t);\
PYDX12_TYPE_INSTANTIATE(t)

#define PYDX12_TYPE(t, ...) PYDX12_TYPE_WITH_REFS(t, __VA_ARGS__);\
void pydx12_##t##_add_refs(t* data) {}\
void pydx12_##t##_release_refs(t* data) {}

#define PYDX12_TYPE_COM(t, ...) typedef struct\
{\
	PyObject_HEAD\
	t* com_ptr;\
	__VA_ARGS__;\
} pydx12_##t;\
PYDX12_TYPE_MEMBERS(t);\
PYDX12_TYPE_INSTANTIATE_COM(t)

#define PYDX12_TYPE_HANDLE(t, ht, ...) typedef struct\
{\
	PyObject_HEAD\
	ht handle;\
	__VA_ARGS__;\
} pydx12_##t;\
PYDX12_TYPE_MEMBERS(t);\
ht pydx12_##t##_check(PyObject* py_object)\
{\
	if (PyLong_Check(py_object))\
	{\
		return (ht)PyLong_AsUnsignedLongLong(py_object);\
	}\
	if (!PyObject_IsInstance(py_object, (PyObject*)&pydx12_##t##Type))\
	{\
		return NULL; \
	}\
	pydx12_##t##* pydx12_object = (pydx12_##t*)py_object; \
	return pydx12_object->handle; \
}

#define PYDX12_ENUM(t) PyModule_AddObject(m, #t, PyLong_FromLongLong(t))

#define PYDX12_REGISTER(t) if (PyType_Ready(&pydx12_##t##Type) < 0)\
		return -1;\
Py_INCREF(&pydx12_##t##Type);\
if (PyModule_AddObject(m, #t, (PyObject*)&pydx12_##t##Type) < 0)\
{\
		Py_DECREF(&pydx12_##t##Type);\
		return -1;\
}

#define PYDX12_REGISTER_STRUCT(t) pydx12_##t##Type.tp_new = PyType_GenericNew;\
if (!pydx12_##t##Type.tp_dealloc)\
	pydx12_##t##Type.tp_dealloc = (destructor)pydx12_##t##_dealloc;\
pydx12_##t##Type.tp_getset = pydx12_##t##_getsetters;\
pydx12_##t##Type.tp_init = (initproc)pydx12_##t##_init;\
pydx12_##t##Type.tp_as_sequence = &pydx12_##t##_sequence_methods;\
pydx12_##t##Type.tp_methods = pydx12_##t##_methods;\
pydx12_##t##Type.tp_weaklistoffset  = offsetof(pydx12_##t, weakreflist);\
pydx12_##t##_refs_tracker = PyDict_New();\
PYDX12_REGISTER(t)

#define PYDX12_REGISTER_COM(t, s) pydx12_##t##Type.tp_base = pydx12_##s##_get_type();\
pydx12_##t##Type.tp_new = PyType_GenericNew;\
pydx12_##t##Type.tp_init = (initproc)pydx12_##t##_init;\
PYDX12_REGISTER_COM_BASE(t)

#define PYDX12_REGISTER_HANDLE(t) pydx12_##t##Type.tp_new = PyType_GenericNew;\
pydx12_##t##Type.tp_dealloc = (destructor)pydx12_##t##_dealloc;\
pydx12_##t##Type.tp_init = (initproc)pydx12_##t##_init;\
PYDX12_REGISTER(t)

#define PYDX12_REGISTER_COM_BASE(t) pydx12_##t##Type.tp_dealloc = (destructor)pydx12_##t##_dealloc;\
PYDX12_REGISTER(t)

#define PYDX12_TRACK(t, addr, py_object) pydx12_##t##_track((unsigned long long)addr, py_object)

#define PYDX12_TRACK_MEM(t, addr) pydx12_##t##_track_mem((unsigned long long)addr)

#define PYDX12_INCREF(t, addr) pydx12_##t##_incref((unsigned long long)addr)

#define PYDX12_DECREF(t, addr) pydx12_##t##_decref((unsigned long long)addr)


#define PYDX12_GETTER(t, field, py_type) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	return PyLong_From##py_type(self->data->##field);\
}

#define PYDX12_SETTER(t, field, py_type, cast) static int pydx12_##t##_set##field(pydx12_##t##* self, PyObject* value, void* closure)\
{\
	if (!PyNumber_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a number");\
		return -1;\
	}\
	self->data->##field = (cast)PyLong_As##py_type(value);\
	return 0;\
}

#define PYDX12_GETTER_SETTER(t, field, py_type, cast) PYDX12_GETTER(t, field, py_type)\
PYDX12_SETTER(t, field, py_type, cast)

#define PYDX12_FLOAT_GETTER(t, field) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	return PyFloat_FromDouble(self->data->##field);\
}

#define PYDX12_FLOAT_SETTER(t, field, cast) static int pydx12_##t##_set##field(pydx12_##t##* self, PyObject* value, void* closure)\
{\
	if (!PyNumber_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a number");\
		return -1;\
	}\
	self->data->##field = (cast)PyFloat_AsDouble(value);\
	return 0;\
}

#define PYDX12_FLOAT_GETTER_SETTER(t, field, cast) PYDX12_FLOAT_GETTER(t, field)\
PYDX12_FLOAT_SETTER(t, field, cast)

#define PYDX12_ARRAY_GETTER(t, field, cast, len, func) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	PyObject* py_tuple = PyTuple_New(len);\
	for(Py_ssize_t i = 0; i < len; i++)\
	{\
		PyTuple_SetItem(py_tuple, i, func((cast)self->data->##field[i]));\
	}\
	return py_tuple;\
}

#define PYDX12_ARRAY_SETTER(t, field, cast, len, func) static int pydx12_##t##_set##field(pydx12_##t##* self, PyObject* value, void* closure)\
{\
	if (!PyTuple_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a tuple");\
		return -1;\
	}\
	Py_ssize_t tuple_len = PyTuple_Size(value);\
	if (tuple_len > len)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a tuple of max " #len " items");\
		return -1;\
	}\
	for(Py_ssize_t i=0; i<tuple_len;i++)\
	{\
		PyObject* py_item = PyTuple_GetItem(value, i);\
		if (!PyNumber_Check(py_item))\
		{\
			PyErr_SetString(PyExc_TypeError, "value must be a tuple of numeric items");\
			return -1;\
		}\
		self->data->##field[i] = (cast)func(py_item); \
	}\
	return 0; \
}

#define PYDX12_ARRAY_GETTER_SETTER(t, field, cast, len, get_func, set_func) PYDX12_ARRAY_GETTER(t, field, cast, len, get_func)\
PYDX12_ARRAY_SETTER(t, field, cast, len, set_func)

#define PYDX12_STRUCT_GETTER(t, field, type) static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	if (PyObject* py_struct = pydx12_##type##_instantiate(&self->data->##field, (PyObject*)self, self->com_owner))\
	{\
		pydx12_##type##_add_refs(&self->data->##field);\
		return (PyObject*)py_struct;\
	}\
	return NULL;\
}

#define PYDX12_STRUCT_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	pydx12_##type##_release_refs(&self->data->##field);\
	self->data->##field = *data;\
	pydx12_##type##_add_refs(&self->data->##field);\
	return 0;\
}

#define PYDX12_STRUCT_GETTER_SETTER(t, field, type) PYDX12_STRUCT_GETTER(t, field, type)\
PYDX12_STRUCT_SETTER(t, field, type)

#define PYDX12_STRUCT_CARRAY_GETTER(t, field, type) static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	if (PyObject* py_struct = pydx12_##type##_instantiate(&self->data->##field[0], (PyObject*)self, self->com_owner))\
	{\
		pydx12_##type##_add_refs((type*)&self->data->##field[0]);\
		return py_struct;\
	}\
	return NULL;\
}

#define PYDX12_STRUCT_CARRAY_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	pydx12_##type##_release_refs((type*)&self->data->##field##[0]);\
	self->data->##field##[0] = *data;\
	pydx12_##type##_add_refs((type*)&self->data->##field##[0]);\
	return 0;\
}

#define PYDX12_STRUCT_CARRAY_GETTER_SETTER(t, field, type) PYDX12_STRUCT_CARRAY_GETTER(t, field, type)\
PYDX12_STRUCT_CARRAY_SETTER(t, field, type)

#define PYDX12_STRUCT_ARRAY_GETTER(t, field, type, field_size) static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	if (!self->data->##field || !self->data->##field_size)\
		Py_RETURN_NONE;\
	PyObject* py_list = PyList_New(0);\
	for(Py_ssize_t i = 0; i < self->data->##field_size; i++)\
	{\
		PyObject* py_item = pydx12_##type##_instantiate((type*)&self->data->##field[i], (PyObject*)self, self->com_owner);\
		if (!py_item)\
		{\
			Py_DECREF(py_list);\
			return NULL;\
		}\
		printf("calling add refs for " #type "\n");\
		pydx12_##type##_add_refs((type*)&self->data->##field[i]);\
		PyList_Append(py_list, py_item);\
		Py_DECREF(py_item);\
	}\
	return py_list;\
}

#define PYDX12_STRUCT_ARRAY_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	PyObject* py_iter = PyObject_GetIter(value);\
	if (!py_iter)\
	{\
		return -1;\
	}\
	if (self->data->##field)\
	{\
		pydx12_##type##_release_refs((type*)&self->data->##field);\
		pydx12_##t* data_owner = self;\
		while(data_owner->data_owner)\
		{\
			data_owner = (pydx12_##t*)data_owner->data_owner;\
		}\
		printf("DATA OWNER FOR " #t " IS %p\n", data_owner);\
		for(size_t i = 0; i < data_owner->mem_list_size;i++)\
		{\
			if (data_owner->mem_list[i].ptr == self->data->##field)\
			{\
				pydx12_allocated_chunk* allocated_chunk = &data_owner->mem_list[i];\
				allocated_chunk->hook(allocated_chunk->ptr, allocated_chunk->number_of_items);\
				PyMem_Free(allocated_chunk->ptr);\
				data_owner->mem_list[i].ptr = NULL;\
				break;\
			}\
		}\
		self->data->##field = NULL;\
	}\
	Py_ssize_t counter = 0;\
	while(PyObject* py_item = PyIter_Next(py_iter))\
	{\
		type* data = pydx12_##type##_check(py_item);\
		if (!data)\
		{\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_TypeError, "value must be an iterable of " #type);\
			return -1;\
		}\
		counter++;\
		type* new_array = (type*)PyMem_Realloc((void*)self->data->##field, sizeof(type) * counter);\
		if (!new_array)\
		{\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_MemoryError, "unable to allocate memory for array of " #type);\
			return -1;\
		}\
		new_array[counter-1] = *data;\
		pydx12_##type##_add_refs((type*)&new_array[counter-1]);\
		self->data->##field = (const type*)new_array;\
		Py_DECREF(py_item);\
	}\
	Py_DECREF(py_iter);\
	if (self->data->##field)\
	{\
		pydx12_##t* data_owner = self;\
		while(data_owner->data_owner)\
		{\
			data_owner = (pydx12_##t*)data_owner->data_owner;\
		}\
		printf("DATA OWNER FOR " #t " IS %p\n", data_owner);\
		bool tracked = false;\
		for(size_t i = 0; i < data_owner->mem_list_size;i++)\
		{\
			if (data_owner->mem_list[i].ptr == NULL)\
			{\
				data_owner->mem_list[i].ptr = (void*)self->data->##field;\
				data_owner->mem_list[i].number_of_items = counter;\
				data_owner->mem_list[i].hook = pydx12_##type##_cleanup;\
				tracked = true;\
				break;\
			}\
		}\
		if (!tracked)\
		{\
			data_owner->mem_list_size++;\
			pydx12_allocated_chunk* new_mem_list = (pydx12_allocated_chunk*)PyMem_Realloc(data_owner->mem_list, sizeof(pydx12_allocated_chunk) * data_owner->mem_list_size);\
			if (!new_mem_list)\
			{\
				return -1;\
			}\
			data_owner->mem_list = new_mem_list;\
			data_owner->mem_list[data_owner->mem_list_size-1].ptr = (void*)self->data->##field;\
			data_owner->mem_list[data_owner->mem_list_size-1].number_of_items = counter;\
			data_owner->mem_list[data_owner->mem_list_size-1].hook = pydx12_##type##_cleanup;\
		}\
	}\
	return 0;\
}

#define PYDX12_STRUCT_ARRAY_GETTER_SETTER(t, field, type, field_size) PYDX12_STRUCT_ARRAY_GETTER(t, field, type, field_size)\
PYDX12_STRUCT_ARRAY_SETTER(t, field, type)

#define PYDX12_STRING_GETTER(t, field) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	return PyUnicode_FromString(self->data->##field);\
}

#define PYDX12_STRING_SETTER(t, field) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	if (!PyUnicode_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a unicode object");\
		return -1;\
	}\
	PYDX12_DECREF(t, self->data->##field);\
	self->data->##field = PyUnicode_AsUTF8(value);\
	PYDX12_TRACK(t, self->data->##field, value);\
	return 0;\
}

#define PYDX12_STRING_GETTER_SETTER(t, field) PYDX12_STRING_GETTER(t, field)\
PYDX12_STRING_SETTER(t, field)

#define PYDX12_WSTRING_GETTER(t, field) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	return PyUnicode_FromWideChar(self->data->##field, -1);\
}

#define PYDX12_BOOL_GETTER(t, field) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (self->data->##field)\
	{\
		Py_RETURN_TRUE;\
	}\
	Py_RETURN_FALSE;\
}

#define PYDX12_BOOL_SETTER(t, field) static int pydx12_##t##_set##field(pydx12_##t##* self, PyObject* value, void* closure)\
{\
	if (!PyBool_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a boolean");\
		return -1;\
	}\
	self->data->##field = value == Py_True ? TRUE : FALSE;\
	return 0;\
}

#define PYDX12_BOOL_GETTER_SETTER(t, field) PYDX12_BOOL_GETTER(t, field)\
PYDX12_BOOL_SETTER(t, field)

#define PYDX12_BUFFER_GETTER(t, field, field_size) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (!self->data->##field || !self->data->##field_size)\
		Py_RETURN_NONE;\
	return PyBytes_FromStringAndSize((const char*)self->data->##field, self->data->##field_size);\
}

#define PYDX12_BUFFER_SETTER(t, field) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	Py_buffer view;\
	if (value != Py_None && !PyObject_CheckBuffer(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a buffer object");\
		return -1; \
	}\
	if (PyObject_GetBuffer(value, &view, PyBUF_SIMPLE))\
	{\
		PyErr_SetString(PyExc_TypeError, "unable to acquire buffer");\
		return -1;\
	}\
	PYDX12_DECREF(t, self->data->##field);\
	if (value == Py_None)\
	{\
		self->data->##field = NULL;\
	}\
	else\
	{\
		self->data->##field = view.buf;\
		printf("tracking " #t " %p\n", self->data->##field);\
		PYDX12_TRACK(t, self->data->##field, value);\
		PyBuffer_Release(&view);\
	}\
	return 0;\
}

#define PYDX12_BUFFER_GETTER_SETTER(t, field, field_size) PYDX12_BUFFER_GETTER(t, field, field_size)\
PYDX12_BUFFER_SETTER(t, field)


#define PYDX12_COM_GETTER(t, field_t, field) static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (self->data->##field)\
	{\
		return pydx12_##field_t##_instantiate(self->data->##field, true);\
	}\
	Py_RETURN_NONE;\
}

#define PYDX12_COM_SETTER(t, field_t, field) static int pydx12_##t##_set##field(pydx12_##t##* self, PyObject* py_value, void* closure)\
{\
	field_t* value = NULL;\
	if (py_value && py_value != Py_None)\
	{\
		value = pydx12_##field_t##_check(py_value);\
		if (!value)\
		{\
			PyErr_SetString(PyExc_ValueError, "value must be a " #field_t);\
			return -1;\
		}\
		printf("resource increase: %llu\n", value->AddRef());\
	}\
	if (self->data->##field)\
		self->data->##field->Release();\
	self->data->##field = value;\
	return 0;\
}

#define PYDX12_COM_GETTER_SETTER(t, field_t, field) PYDX12_COM_GETTER(t, field_t, field)\
PYDX12_COM_SETTER(t, field_t, field)

#define PYDX12_DECLARE_GETTER_SETTER(t, field) {#field, (getter)pydx12_##t##_get##field, (setter)pydx12_##t##_set##field, #t " " #field " field", NULL}
#define PYDX12_DECLARE_GETTER(t, field) {#field, (getter)pydx12_##t##_get##field, NULL, #t " " #field " field", NULL}

#define PYDX12_IMPORT(t) PyObject* pydx12_##t##_instantiate(t* data, PyObject* data_owner, IUnknown* com_owner);\
PyObject* pydx12_##t##_instantiate_with_size(t* data, PyObject* data_owner, IUnknown* com_owner, const size_t len);\
t* pydx12_##t##_get_data(PyObject* py_object);\
t* pydx12_##t##_check(PyObject* py_object);\
void pydx12_##t##_add_refs(t* data);\
void pydx12_##t##_release_refs(t* data)

#define PYDX12_IMPORT_COM(t) PyObject* pydx12_##t##_instantiate(t* com_ptr, const bool add_ref);\
t* pydx12_##t##_check(PyObject* py_object);\
PyTypeObject* pydx12_##t##_get_type()

#define PYDX12_IMPORT_HANDLE(t, ht) ht pydx12_##t##_check(PyObject* py_object);

#define PYDX12_METHODS(t) static PyMethodDef pydx12_##t##_methods[]
#define PYDX12_GETSETTERS(t) static PyGetSetDef pydx12_##t##_getsetters[]

#define PYDX12_COM_CALL(func, ...) self->com_ptr->##func(__VA_ARGS__)

#define PYDX12_COM_CALL_HRESULT(t, func, ...) if (PYDX12_COM_CALL(func, __VA_ARGS__) != S_OK)\
{\
	return PyErr_Format(PyExc_Exception, #t "::" #func);\
}

#define PYDX12_COM_CALL_HRESULT_AND_FREE(object_to_free, t, func, ...) if (PYDX12_COM_CALL(func, __VA_ARGS__) != S_OK)\
{\
	PyMem_Free(object_to_free);\
	return PyErr_Format(PyExc_Exception, #t "::" #func);\
}\
PyMem_Free(object_to_free)

#define PYDX12_UNICODE_CHECK(name, py_object) if (!PyUnicode_Check(py_object))\
{\
	return PyErr_Format(PyExc_TypeError, "expected a unicode object");\
}\
wchar_t* name = PyUnicode_AsWideCharString(py_object, NULL);\
if (!name)\
	return NULL;

#define PYDX12_ARG_CHECK(t, name) t* name = pydx12_##t##_check(py_##name);\
if (!name)\
	return PyErr_Format(PyExc_TypeError, "argument must be a " #t);

#define PYDX12_ARG_CHECK_HANDLE(t, ht, name) ht name = pydx12_##t##_check(py_##name);\
if (!name)\
	return PyErr_Format(PyExc_TypeError, "argument must be a raw numeric HANDLE or " #t);

#define PYDX12_ARG_CHECK_NONE(t, name) t* name = NULL;\
if (py_##name && py_##name != Py_None)\
{\
	name = pydx12_##t##_check(py_##name);\
	if (!name)\
		return PyErr_Format(PyExc_TypeError, "argument must be a " #t);\
}

#define PYDX12_ADD_REFS(t) void pydx12_##t##_add_refs(t* data)
#define PYDX12_RELEASE_REFS(t) void pydx12_##t##_release_refs(t* data)
#define PYDX12_COM_ADD(field) if (data->##field) data->##field->AddRef()
#define PYDX12_COM_RELEASE(field) if (data->##field) data->##field->Release();

#define PYDX12_COM_INSTANTIATE(t, object, add_ref) pydx12_##t##_instantiate(object, add_ref)

/** Common imports */
PYDX12_IMPORT_COM(IUnknown);