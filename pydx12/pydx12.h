#pragma once

#include <Python.h>
#include <dxgi1_6.h>
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
	size_t size;
	size_t elements;
} pydx12_memory_chunk;

#define PYDX12_TRACK_TYPE_CHUNK 0
#define PYDX12_TRACK_TYPE_COM 1

struct pydx12_field_track_type
{
	size_t type;
	size_t offset;
};

typedef struct
{
	IUnknown* com_ptr;
	size_t refs;
} pydx12_com_track;

#define PYDX12_TYPE_INSTANTIATE(t) PyObject* pydx12_##t##_instantiate_with_size(t* data, PyObject* data_owner, IUnknown* com_owner, const size_t len)\
{\
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
static void pydx12_##t##_com_addref(pydx12_##t* self, IUnknown* com_ptr)\
{\
	pydx12_##t* owner = (pydx12_##t*) (self->data_owner ? self->data_owner : (PyObject*)self);\
	for(size_t i = 0; i < owner->number_of_tracked_coms; i++)\
	{\
		pydx12_com_track* com_track = &owner->tracked_coms[i];\
		if (com_track->com_ptr == com_ptr)\
		{\
			com_track->refs++;\
			com_track->com_ptr->AddRef();\
			return;\
		}\
	}\
	for(size_t i = 0; i < owner->number_of_tracked_coms; i++)\
	{\
		pydx12_com_track* com_track = &owner->tracked_coms[i];\
		if (com_track->com_ptr == NULL)\
		{\
			com_track->com_ptr = com_ptr;\
			com_track->refs = 1;\
			com_track->com_ptr->AddRef();\
			return;\
		}\
	}\
	owner->number_of_tracked_coms++;\
	pydx12_com_track* new_com_tracked = (pydx12_com_track*)PyMem_Realloc(owner->tracked_coms, sizeof(pydx12_com_track) * owner->number_of_tracked_coms);\
	if (!new_com_tracked)\
	{\
		return;\
	}\
	owner->tracked_coms = new_com_tracked;\
	owner->tracked_coms[owner->number_of_tracked_coms-1].com_ptr = com_ptr;\
	owner->tracked_coms[owner->number_of_tracked_coms-1].refs = 1;\
	com_ptr->AddRef();\
}\
static void pydx12_##t##_com_release(pydx12_##t* self, IUnknown* com_ptr)\
{\
	pydx12_##t* owner = (pydx12_##t*) (self->data_owner ? self->data_owner : (PyObject*)self);\
	for(size_t i = 0; i < owner->number_of_tracked_coms; i++)\
	{\
		pydx12_com_track* com_track = &owner->tracked_coms[i];\
		if (com_track->com_ptr == com_ptr)\
		{\
			assert(com_track->refs > 0);\
			com_track->refs--;\
			com_track->com_ptr->Release();\
			if (com_track->refs == 0)\
				com_track->com_ptr = NULL;\
			return;\
		}\
	}\
}\
t* pydx12_##t##_iter(PyObject* py_object, UINT* list_counter, const bool append_null)\
{\
	PyObject* py_iter = PyObject_GetIter(py_object);\
	if (!py_iter)\
	{\
		return NULL;\
	}\
	t* list = NULL;\
	*list_counter = 0;\
	while (PyObject* py_item = PyIter_Next(py_iter))\
	{\
		t* item = pydx12_##t##_check(py_item);\
		if (!item)\
		{\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			if (list)\
				PyMem_Free(list);\
			return (t*)PyErr_Format(PyExc_TypeError, "argument must be an iterable of " #t);\
		}\
		(*list_counter)++;\
		t* new_list = (t*)PyMem_Realloc(list, sizeof(t) * (*list_counter));\
		if (!new_list)\
		{\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			if (list)\
				PyMem_Free(list);\
			return (t*)PyErr_Format(PyExc_MemoryError, "unable to allocate memory for " #t " array");\
		}\
		list = new_list;\
		list[(*list_counter) - 1] = *item;\
		Py_DECREF(py_item);\
	}\
	Py_DECREF(py_iter);\
	if (append_null)\
	{\
		(*list_counter)++;\
		t* new_list = (t*)PyMem_Realloc(list, sizeof(t) * (*list_counter));\
		if (!new_list)\
		{\
			if (list)\
				PyMem_Free(list);\
			return (t*)PyErr_Format(PyExc_MemoryError, "unable to allocate memory for " #t " array");\
		}\
		list = new_list;\
		memset(&list[(*list_counter) - 1], 0, sizeof(t));\
	}\
	return list;\
}\
static pydx12_memory_chunk* pydx12_##t##_chunk_map(pydx12_##t* self, void* addr, const size_t size, const size_t elements)\
{\
	if (!addr)\
		return NULL;\
	pydx12_##t* owner = (pydx12_##t*) (self->data_owner ? self->data_owner : (PyObject*)self);\
	for(size_t i = 0; i < owner->number_of_chunks; i++)\
	{\
		pydx12_memory_chunk* chunk = &owner->chunks[i];\
		if (!chunk->ptr)\
		{\
			chunk->ptr = addr;\
			chunk->size = size;\
			chunk->elements = elements;\
			return chunk;\
		}\
	}\
	owner->number_of_chunks++;\
	pydx12_memory_chunk* new_chunks = (pydx12_memory_chunk*)PyMem_Realloc(owner->chunks, sizeof(pydx12_memory_chunk) * owner->number_of_chunks);\
	if (!new_chunks)\
	{\
		return NULL;\
	}\
	owner->chunks = new_chunks;\
	pydx12_memory_chunk* chunk = &owner->chunks[owner->number_of_chunks-1];\
	chunk->ptr = addr;\
	chunk->size = size;\
	chunk->elements = elements;\
	return chunk;\
}\
static void pydx12_##t##_chunk_free(pydx12_##t* self, void* addr)\
{\
	if (!addr)\
		return;\
	pydx12_##t* owner = (pydx12_##t*) (self->data_owner ? self->data_owner : (PyObject*)self);\
	for(size_t i = 0; i < owner->number_of_chunks; i++)\
	{\
		pydx12_memory_chunk* chunk = &owner->chunks[i];\
		if (chunk->ptr == addr)\
		{\
			PyMem_Free(chunk->ptr);\
			chunk->ptr = NULL;\
			chunk->size = 0;\
			chunk->elements = 0;\
			break;\
		}\
	}\
}\
static pydx12_memory_chunk* pydx12_##t##_chunk_get(pydx12_##t* self, void* addr)\
{\
	if (!addr)\
		return NULL;\
	pydx12_##t* owner = (pydx12_##t*) (self->data_owner ? self->data_owner : (PyObject*)self);\
	for(size_t i = 0; i < owner->number_of_chunks; i++)\
	{\
		pydx12_memory_chunk* chunk = &owner->chunks[i];\
		if (chunk->ptr == addr)\
		{\
			return chunk;\
		}\
	}\
	return NULL;\
}\
static pydx12_memory_chunk* pydx12_##t##_chunk_alloc(pydx12_##t* self, void* addr, const size_t size, const size_t elements)\
{\
	if (!addr)\
		return NULL;\
	pydx12_##t* owner = (pydx12_##t*) (self->data_owner ? self->data_owner : (PyObject*)self);\
	for(size_t i = 0; i < owner->number_of_chunks; i++)\
	{\
		pydx12_memory_chunk* chunk = &owner->chunks[i];\
		if (chunk->ptr == NULL)\
		{\
			void* ptr = PyMem_Malloc(size);\
			if (!ptr)\
				return NULL;\
			memcpy(ptr, addr, size);\
			chunk->ptr = ptr;\
			chunk->size = size;\
			chunk->elements = elements;\
			return chunk;\
		}\
	}\
	owner->number_of_chunks++;\
	pydx12_memory_chunk* new_chunks = (pydx12_memory_chunk*)PyMem_Realloc(owner->chunks, sizeof(pydx12_memory_chunk) * owner->number_of_chunks);\
	if (!new_chunks)\
	{\
		return NULL;\
	}\
	pydx12_memory_chunk* chunk = &new_chunks[owner->number_of_chunks-1];\
	void* ptr = PyMem_Malloc(size);\
	if (!ptr)\
	{\
		chunk->ptr = NULL;\
		return NULL;\
	}\
	owner->chunks = new_chunks;\
	memcpy(ptr, addr, size);\
	chunk->ptr = ptr;\
	chunk->size = size;\
	chunk->elements = elements;\
	return chunk;\
}\
int pydx12_##t##_chunk_fix(pydx12_##t* self, pydx12_##t* value, t* data)\
{\
	PyGetSetDef* getset = pydx12_##t##Type.tp_getset;\
	while (getset->name)\
	{\
		if (getset->closure != NULL)\
		{\
			pydx12_field_track_type* track_type = (pydx12_field_track_type*)getset->closure;\
			if (track_type->type == PYDX12_TRACK_TYPE_CHUNK)\
			{\
				void** ptr = (void**)(((char*)data) + track_type->offset);\
				pydx12_memory_chunk* chunk = pydx12_##t##_chunk_get(value, *ptr); \
				if (chunk)\
				{\
					chunk = pydx12_##t##_chunk_alloc(self, chunk->ptr, chunk->size, chunk->elements);\
					if (!chunk)\
						return -1; \
					*ptr = chunk->ptr;\
				}\
			}\
			else if (track_type->type == PYDX12_TRACK_TYPE_COM)\
			{\
				IUnknown** ptr = (IUnknown**)(((char*)data) + track_type->offset);\
				if (*ptr)\
				{\
					pydx12_##t##_com_addref(self, *ptr);\
				}\
			}\
		}\
		getset++;\
	}\
	return 0;\
}\
void pydx12_##t##_chunk_clear(pydx12_##t* self, t* data)\
{\
	PyGetSetDef* getset = pydx12_##t##Type.tp_getset;\
	while (getset->name)\
	{\
		if (getset->closure != NULL)\
		{\
			pydx12_field_track_type* track_type = (pydx12_field_track_type*)getset->closure;\
			if (track_type->type == PYDX12_TRACK_TYPE_CHUNK)\
			{\
				void** ptr = (void**) (((char*)data) + track_type->offset);\
				pydx12_##t##_chunk_free(self, *ptr);\
			}\
			else if (track_type->type == PYDX12_TRACK_TYPE_COM)\
			{\
				IUnknown** ptr = (IUnknown**)(((char*)data) + track_type->offset);\
				if (*ptr)\
					pydx12_##t##_com_release(self, *ptr);\
			}\
		}\
		getset++;\
	}\
}\
static void pydx12_##t##_dealloc(pydx12_##t* self)\
{\
	if (self->data)\
	{\
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
	for(size_t i = 0; i < self->number_of_chunks; i++)\
	{\
		if (self->chunks[i].ptr)\
		{\
			PyMem_Free(self->chunks[i].ptr);\
		}\
	}\
	if (self->chunks)\
		PyMem_Free(self->chunks);\
	for(size_t i=0; i< self->number_of_tracked_coms;i++)\
	{\
		for(size_t j=0;j<self->tracked_coms[i].refs;j++)\
		{\
			self->tracked_coms[i].com_ptr->Release();\
		}\
	}\
	if (self->tracked_coms)\
		PyMem_Free(self->tracked_coms);\
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
	return pydx12_##t##_instantiate(self->data + index, PYDX12_OWNER, self->com_owner);\
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
static PyObject* pydx12_##t##_get_chunks(pydx12_##t* self)\
{\
	PyObject* py_list = PyList_New(0);\
	for(size_t i = 0; i < self->number_of_chunks; i++)\
	{\
		if (!self->chunks[i].ptr)\
			continue;\
		PyObject* py_chunk = Py_BuildValue("(KKK)", self->chunks[i].ptr, self->chunks[i].size, self->chunks[i].elements);\
		PyList_Append(py_list, py_chunk);\
		Py_DECREF(py_chunk);\
	}\
	return py_list;\
}\
static PyMethodDef pydx12_##t##_methods[] = {\
	{"get_fields", (PyCFunction)pydx12_##t##_get_fields, METH_NOARGS, "returns a list of structure's fields"},\
	{"to_dict", (PyCFunction)pydx12_##t##_to_dict, METH_NOARGS, "returns a dictionary representation of the structure"},\
	{"to_bytes", (PyCFunction)pydx12_##t##_to_bytes, METH_NOARGS, "returns structure's content as a bytes object"},\
	{"to_bytearray", (PyCFunction)pydx12_##t##_to_bytearray, METH_NOARGS, "returns structure's content as a bytearray object"},\
	{"get_chunks", (PyCFunction)pydx12_##t##_get_chunks, METH_NOARGS, "returns structure's memory chunks"},\
	{NULL}\
};

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
		com_ptr->AddRef();\
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
		self->com_ptr->Release();\
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

#define PYDX12_TYPE(t, ...) typedef struct\
{\
	PyObject_HEAD\
	t* data;\
	size_t data_len;\
	PyObject* data_owner;\
	IUnknown* com_owner;\
	pydx12_memory_chunk* chunks;\
	size_t number_of_chunks;\
	pydx12_com_track* tracked_coms;\
	size_t number_of_tracked_coms;\
	PyObject* weakreflist;\
	__VA_ARGS__;\
} pydx12_##t;\
PYDX12_TYPE_MEMBERS(t);\
PYDX12_TYPE_INSTANTIATE(t)

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
	return pydx12_##type##_instantiate(&self->data->##field, PYDX12_OWNER, self->com_owner);\
}

#define PYDX12_STRUCT_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	pydx12_##type##_chunk_clear((pydx12_##type*)self, &self->data->##field);\
	self->data->##field = *data;\
	pydx12_##type##_chunk_fix((pydx12_##type*)self, (pydx12_##type*) value, &self->data->##field);\
	return 0;\
}

#define PYDX12_STRUCT_GETTER_SETTER(t, field, type) PYDX12_STRUCT_GETTER(t, field, type)\
PYDX12_STRUCT_SETTER(t, field, type)

#define PYDX12_STRUCT_CARRAY_GETTER(t, field, type) static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	return pydx12_##type##_instantiate(&self->data->##field[0], PYDX12_OWNER, self->com_owner);\
}

#define PYDX12_STRUCT_CARRAY_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	/* cleanup all */\
	self->data->##field##[0] = *data;\
	/* reassign */\
	return 0;\
}

#define PYDX12_STRUCT_CARRAY_GETTER_SETTER(t, field, type) PYDX12_STRUCT_CARRAY_GETTER(t, field, type)\
PYDX12_STRUCT_CARRAY_SETTER(t, field, type)

#define PYDX12_STRUCT_ARRAY_GETTER(t, field, type) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK, offsetof(t, field)}; static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	pydx12_memory_chunk* chunk = pydx12_##t##_chunk_get(self, (void*)self->data->##field);\
	if (!chunk)\
		Py_RETURN_NONE;\
	PyObject* py_list = PyList_New(0);\
	for(Py_ssize_t i = 0; i < (Py_ssize_t)chunk->elements; i++)\
	{\
		PyObject* py_item = pydx12_##type##_instantiate((type*)&self->data->##field[i], PYDX12_OWNER, self->com_owner);\
		if (!py_item)\
		{\
			Py_DECREF(py_list);\
			return NULL;\
		}\
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
		pydx12_memory_chunk* chunk = pydx12_##t##_chunk_get(self, (void*)self->data->##field);\
		if (!chunk)\
			return -1;\
		for(size_t i = 0; i< chunk->elements; i++)\
		{\
			pydx12_##type##_chunk_clear((pydx12_##type*)self, (type*)&self->data->##field[i]);\
		}\
		pydx12_##t##_chunk_free(self,(void*)self->data->##field);\
		self->data->##field = NULL;\
	}\
	Py_ssize_t counter = 0;\
	while(PyObject* py_item = PyIter_Next(py_iter))\
	{\
		type* data = pydx12_##type##_check(py_item);\
		if (!data)\
		{\
			if (self->data->##field)\
				PyMem_Free((void*)self->data->##field);\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_TypeError, "value must be an iterable of " #type);\
			return -1;\
		}\
		counter++;\
		type* new_array = (type*)PyMem_Realloc((void*)self->data->##field, sizeof(type) * counter);\
		if (!new_array)\
		{\
			if (self->data->##field)\
				PyMem_Free((void*)self->data->##field);\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_MemoryError, "unable to allocate memory for array of " #type);\
			return -1;\
		}\
		new_array[counter-1] = *data;\
		self->data->##field = (const type*)new_array;\
		pydx12_##type##_chunk_fix((pydx12_##type*)self, (pydx12_##type*) py_item, (type*)&self->data->##field[counter-1]);\
		Py_DECREF(py_item);\
	}\
	Py_DECREF(py_iter);\
	if (self->data->##field)\
	{\
		pydx12_##t##_chunk_map(self, (void*)self->data->##field, sizeof(type) * counter, counter);\
	}\
	return 0;\
}

#define PYDX12_STRUCT_ARRAY_GETTER_SETTER(t, field, type) PYDX12_STRUCT_ARRAY_GETTER(t, field, type)\
PYDX12_STRUCT_ARRAY_SETTER(t, field, type)

#define PYDX12_STRING_GETTER(t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK, offsetof(t, field)}; static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	pydx12_memory_chunk* chunk = pydx12_##t##_chunk_get(self, (void*)self->data->##field);\
	if (!chunk)\
		return PyUnicode_FromString((const char*)self->data->##field);\
	return PyUnicode_FromStringAndSize((const char*)chunk->ptr, chunk->size - 1);\
}

#define PYDX12_STRING_SETTER(t, field) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	if (value == Py_None)\
	{\
		pydx12_##t##_chunk_free(self, (void*)self->data->##field);\
		self->data->##field = NULL;\
		return 0;\
	}\
	if (!PyUnicode_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a unicode object");\
		return -1;\
	}\
	pydx12_##t##_chunk_free(self, (void*)self->data->##field);\
	Py_ssize_t size;\
	const char* utf8 = PyUnicode_AsUTF8AndSize(value, &size);\
	pydx12_memory_chunk* chunk = pydx12_##t##_chunk_alloc(self, (void*) utf8, size + 1, 1);\
	if (!chunk)\
	{\
		PyErr_SetString(PyExc_MemoryError, "unable to allocate memory chunk for " #t "::" #field);\
		return -1;\
	}\
	self->data->##field = (const char*)chunk->ptr;\
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

#define PYDX12_BUFFER_GETTER(t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK, offsetof(t, field)}; static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	pydx12_memory_chunk* chunk = pydx12_##t##_chunk_get(self, (void*)self->data->##field);\
	if (!chunk)\
		Py_RETURN_NONE;\
	return PyBytes_FromStringAndSize((const char*)chunk->ptr, chunk->size);\
}

#define PYDX12_BUFFER_SETTER(t, field) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	Py_buffer view;\
	if (value != Py_None && !PyObject_CheckBuffer(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a buffer object");\
		return -1; \
	}\
	pydx12_##t##_chunk_free(self, (void*)self->data->##field);\
	if (value == Py_None)\
	{\
		self->data->##field = NULL;\
		return 0;\
	}\
	if (PyObject_GetBuffer(value, &view, PyBUF_SIMPLE))\
	{\
		PyErr_SetString(PyExc_TypeError, "unable to acquire buffer");\
		return -1;\
	}\
	pydx12_memory_chunk* chunk = pydx12_##t##_chunk_alloc(self, view.buf, view.len, 1);\
	if (!chunk)\
	{\
		PyErr_SetString(PyExc_MemoryError, "unable to acquire buffer");\
		PyBuffer_Release(&view);\
		return -1;\
	}\
	self->data->##field = chunk->ptr;\
	PyBuffer_Release(&view);\
	return 0;\
}

#define PYDX12_BUFFER_GETTER_SETTER(t, field, field_size) PYDX12_BUFFER_GETTER(t, field)\
PYDX12_BUFFER_SETTER(t, field)


#define PYDX12_COM_GETTER(t, field_t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_com_type = {PYDX12_TRACK_TYPE_COM, offsetof(t, field)}; static PyObject* pydx12_##t##_get##field(pydx12_##t##* self, void* closure)\
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
		pydx12_##t##_com_addref(self, value);\
	}\
	if (self->data->##field)\
		pydx12_##t##_com_release(self, self->data->##field);\
	self->data->##field = value;\
	return 0;\
}

#define PYDX12_COM_GETTER_SETTER(t, field_t, field) PYDX12_COM_GETTER(t, field_t, field)\
PYDX12_COM_SETTER(t, field_t, field)

#define PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, closure) {#field, (getter)pydx12_##t##_get##field, (setter)pydx12_##t##_set##field, #t " " #field " field", closure}
#define PYDX12_DECLARE_GETTER_CLOSURE(t, field, closure) {#field, (getter)pydx12_##t##_get##field, NULL, #t " " #field " field", closure}

#define PYDX12_DECLARE_GETTER_SETTER(t, field) PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, NULL)
#define PYDX12_DECLARE_GETTER(t, field) PYDX12_DECLARE_GETTER_CLOSURE(t, field, NULL)

#define PYDX12_DECLARE_GETTER_SETTER_CHUNK(t, field) PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_chunk_type)
#define PYDX12_DECLARE_GETTER_CHUNK(t, field)  PYDX12_DECLARE_GETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_chunk_type)

#define PYDX12_DECLARE_GETTER_SETTER_COM(t, field) PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_com_type)
#define PYDX12_DECLARE_GETTER_COM(t, field)  PYDX12_DECLARE_GETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_com_type)

#define PYDX12_IMPORT(t) PyObject* pydx12_##t##_instantiate(t* data, PyObject* data_owner, IUnknown* com_owner);\
PyObject* pydx12_##t##_instantiate_with_size(t* data, PyObject* data_owner, IUnknown* com_owner, const size_t len);\
t* pydx12_##t##_get_data(PyObject* py_object);\
t* pydx12_##t##_check(PyObject* py_object);\
t* pydx12_##t##_iter(PyObject* py_object, UINT* list_counter, const bool append_null);\
struct pydx12_##t;\
void pydx12_##t##_chunk_clear(pydx12_##t* self, t* data);\
int pydx12_##t##_chunk_fix(pydx12_##t* self, pydx12_##t* value, t* data);

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

#define PYDX12_ARG_ITER_CHECK(t, name, append_null) UINT name##_counter = 0; t* name = pydx12_##t##_iter(py_##name, &##name##_counter, append_null);\
if (!name)\
	return NULL;

#define PYDX12_ARG_ITER_CHECK_NONE(t, name, append_null) UINT name##_counter = 0; t* name = NULL;\
if (py_##name && py_##name != Py_None)\
{\
	name = pydx12_##t##_iter(py_##name, &##name##_counter, append_null);\
	if (!name)\
		return NULL;\
}

#define PYDX12_OWNER self->data_owner ? self->data_owner : (PyObject*)self

#define PYDX12_COM_INSTANTIATE(t, object, add_ref) pydx12_##t##_instantiate(object, add_ref)

#define PYDX12_INTERFACE_CREATE(t, func, ...) { t* interface_ptr;\
	HRESULT ret = func(__VA_ARGS__, __uuidof(t), (void**)&interface_ptr);\
	if (ret == S_OK)\
	{\
		return pydx12_##t##_instantiate(interface_ptr, false);\
	}\
	else if (ret != E_NOINTERFACE)\
	{\
		return PyErr_Format(PyExc_ValueError, "unable to create " #t);\
	}\
}

#define PYDX12_INTERFACE_CREATE_LAST(t, func, ...) PYDX12_INTERFACE_CREATE(t, func, __VA_ARGS__);\
return PyErr_Format(PyExc_ValueError, "unable to create " #t)

#define PYDX12_INTERFACE_CREATE_NO_ARGS(t, func) { t* interface_ptr;\
	HRESULT ret = func(__uuidof(t), (void**)&interface_ptr);\
	if (ret == S_OK)\
	{\
		return pydx12_##t##_instantiate(interface_ptr, false);\
	}\
	else if (ret != E_NOINTERFACE)\
	{\
		return PyErr_Format(PyExc_ValueError, "unable to create " #t);\
	}\
}

#define PYDX12_INTERFACE_CREATE_CAST(t, cast, func, ...) { t* interface_ptr;\
	HRESULT ret = func(__VA_ARGS__, (cast**)&interface_ptr);\
	if (ret == S_OK)\
	{\
		return pydx12_##t##_instantiate(interface_ptr, false);\
	}\
	else if (ret != E_NOINTERFACE)\
	{\
		return PyErr_Format(PyExc_ValueError, "unable to create " #t);\
	}\
}

#define PYDX12_INTERFACE_CREATE_CAST_LAST(t, cast, func, ...) PYDX12_INTERFACE_CREATE_CAST(t, cast, func, __VA_ARGS__);\
return PyErr_Format(PyExc_ValueError, "unable to create " #t)

#define PYDX12_INTERFACE_CREATE_NO_ARGS_LAST(t, func) PYDX12_INTERFACE_CREATE_NO_ARGS(t, func);\
return PyErr_Format(PyExc_ValueError, "unable to create " #t)

/** Common imports */
PYDX12_IMPORT_COM(IUnknown);