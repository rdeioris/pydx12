#pragma once

#define PYDX12_OWNER self->data_owner ? self->data_owner : (PyObject*)self

#include "pydx12_templates.h"

#define PYDX12_TYPE_DEFINE(base, t) static PyTypeObject pydx12_##t##_Type = \
{\
	PyVarObject_HEAD_INIT(NULL, 0)\
	"pydx12." #t,              /* tp_name */ \
	sizeof(base<t>), /* tp_basicsize */\
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
};

#define PYDX12_TYPE_STRUCT_MEMBERS(t) static PySequenceMethods pydx12_##t##_sequence_methods = {\
       NULL,\
       NULL,\
       NULL,\
       (ssizeargfunc)pydx12_sq_item<t>\
};\
static PyBufferProcs pydx12_##t##_as_buffer = {\
	(getbufferproc)pydx12_get_buffer<t>,\
	(releasebufferproc)pydx12_release_buffer<t>\
};\
static PyMethodDef pydx12_##t##_methods[] = {\
	{"get_fields", (PyCFunction)pydx12_get_fields<t>, METH_NOARGS, "returns a list of structure's fields"},\
	{"to_dict", (PyCFunction)pydx12_to_dict<t>, METH_NOARGS, "returns a dictionary representation of the structure"},\
	{"to_bytes", (PyCFunction)pydx12_to_bytes<t>, METH_NOARGS, "returns structure's content as a bytes object"},\
	{"to_bytearray", (PyCFunction)pydx12_to_bytearray<t>, METH_NOARGS, "returns structure's content as a bytearray object"},\
	{"get_chunks", (PyCFunction)pydx12_get_chunks<t>, METH_NOARGS, "returns structure's memory chunks"},\
	{"get_ptr", (PyCFunction)pydx12_get_ptr<t>, METH_NOARGS, "returns structure's data pointer"},\
	{NULL}\
}

#define PYDX12_TYPE_INSTANTIATE(t) \
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
			if (track_type->type == PYDX12_TRACK_TYPE_CHUNK_ARRAY)\
			{\
				void** ptr = (void**) (((char*)data) + track_type->offset);\
				pydx12_memory_chunk* chunk = pydx12_##t##_chunk_get(self, *ptr);\
				if (chunk)\
				{\
					void** array_ptr = (void**)chunk->ptr;\
					for(size_t i =0; i < chunk->elements; i++)\
					{\
						pydx12_##t##_chunk_free(self, array_ptr[i]);\
					}\
				}\
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
}

#define PYDX12_TYPE(t) PYDX12_TYPE_DEFINE(pydx12_Structure, t);\
PYDX12_TYPE_STRUCT_MEMBERS(t);\
template<>\
PyTypeObject* pydx12_get_type<t>()\
{\
	return &pydx12_##t##_Type;\
}\
template<>\
const char* pydx12_get_type_name<t>()\
{\
	return #t;\
}

#define PYDX12_TYPE_COM(t) PYDX12_TYPE_DEFINE(pydx12_COM, t);\
template<>\
PyTypeObject* pydx12_get_type<t>()\
{\
	return &pydx12_##t##_Type;\
}\
template<>\
const char* pydx12_get_type_name<t>()\
{\
	return #t;\
}

#define PYDX12_TYPE_HANDLE(t) PYDX12_TYPE_DEFINE(pydx12_HANDLE, t);\
template<>\
PyTypeObject* pydx12_get_type<t>()\
{\
	return &pydx12_##t##_Type;\
}\
template<>\
const char* pydx12_get_type_name<t>()\
{\
	return #t;\
}

#define PYDX12_ENUM(t) PyModule_AddObject(m, #t, PyLong_FromLongLong(t))

#define PYDX12_REGISTER_STRUCT(t) pydx12_##t##_Type.tp_new = PyType_GenericNew;\
if (!pydx12_##t##_Type.tp_dealloc)\
	pydx12_##t##_Type.tp_dealloc = (destructor)pydx12_dealloc<t>;\
pydx12_##t##_Type.tp_getset = pydx12_##t##_getsetters;\
pydx12_##t##_Type.tp_init = (initproc)pydx12_init<t>;\
pydx12_##t##_Type.tp_methods = pydx12_##t##_methods;\
pydx12_##t##_Type.tp_as_sequence = &pydx12_##t##_sequence_methods;\
pydx12_##t##_Type.tp_weaklistoffset  = offsetof(pydx12_Structure<t>, weakreflist);\
pydx12_##t##_Type.tp_as_buffer = &pydx12_##t##_as_buffer;\
if (pydx12_register<t>(m))\
	return -1

#define PYDX12_REGISTER_COM(t, s) pydx12_##t##_Type.tp_base = pydx12_get_type<s>();\
pydx12_##t##_Type.tp_new = PyType_GenericNew;\
pydx12_##t##_Type.tp_init = (initproc)pydx12_com_init<t>;\
pydx12_##t##_Type.tp_richcompare = (richcmpfunc)pydx12_com_richcompare<t>;\
PYDX12_REGISTER_COM_BASE(t)

#define PYDX12_REGISTER_HANDLE(t) pydx12_##t##_Type.tp_new = PyType_GenericNew;\
pydx12_##t##_Type.tp_dealloc = (destructor)pydx12_##t##_dealloc;\
pydx12_##t##_Type.tp_init = (initproc)pydx12_##t##_init;\
if (pydx12_register<t>(m))\
	return -1

#define PYDX12_REGISTER_SUBHANDLE(t, s) pydx12_##t##_Type.tp_base = pydx12_##s##_get_type();\
if (pydx12_register<t>(m))\
	return -1

#define PYDX12_REGISTER_COM_BASE(t) pydx12_##t##_Type.tp_dealloc = (destructor)pydx12_com_dealloc<t>;\
if (pydx12_register<t>(m))\
	return -1

#define PYDX12_GETTER(t, field, py_type) static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	return PyLong_From##py_type(self->data->##field);\
}

#define PYDX12_SETTER(t, field, py_type, cast) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
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

#define PYDX12_PTR_GETTER(t, field) static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	return PyLong_FromUnsignedLongLong((unsigned long long)self->data->##field);\
}

#define PYDX12_PTR_SETTER(t, field, cast) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
{\
	if (!PyNumber_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a number");\
		return -1;\
	}\
	self->data->##field = (cast *)PyLong_AsUnsignedLongLong(value);\
	return 0;\
}

#define PYDX12_PTR_GETTER_SETTER(t, field, cast) PYDX12_PTR_GETTER(t, field)\
PYDX12_PTR_SETTER(t, field, cast)

#define PYDX12_FLOAT_GETTER(t, field) static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	return PyFloat_FromDouble(self->data->##field);\
}

#define PYDX12_FLOAT_SETTER(t, field, cast) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
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

#define PYDX12_ARRAY_GETTER(t, field, cast, len, func) static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	PyObject* py_tuple = PyTuple_New(len);\
	for(Py_ssize_t i = 0; i < len; i++)\
	{\
		PyTuple_SetItem(py_tuple, i, func((cast)self->data->##field[i]));\
	}\
	return py_tuple;\
}

#define PYDX12_ARRAY_SETTER(t, field, cast, len, func) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
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

#define PYDX12_STRUCT_GETTER(t, field, type) static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	return pydx12_instantiate<type>(&self->data->##field, PYDX12_OWNER, self->com_owner);\
}

#define PYDX12_STRUCT_SETTER(t, field, type) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_structure_check<type>(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	pydx12_chunk_clear<type>((pydx12_Structure<type>*)self, &self->data->##field);\
	self->data->##field = *data;\
	pydx12_chunk_fix<type>((pydx12_Structure<type>*)self, (pydx12_Structure<type>*) value, &self->data->##field);\
	return 0;\
}

#define PYDX12_STRUCT_GETTER_SETTER(t, field, type) PYDX12_STRUCT_GETTER(t, field, type)\
PYDX12_STRUCT_SETTER(t, field, type)

#define PYDX12_STRUCT_CARRAY_GETTER(t, field, type) static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	return pydx12_instantiate<type>(&self->data->##field[0], PYDX12_OWNER, self->com_owner);\
}

#define PYDX12_STRUCT_CARRAY_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	pydx12_##type##_chunk_clear((pydx12_##type*)self, &self->data->##field[0]);\
	self->data->##field##[0] = *data;\
	pydx12_##type##_chunk_fix((pydx12_##type*)self, (pydx12_##type*) value, &self->data->##field[0]);\
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
		PyObject* py_item = pydx12_instantiate<type>((type*)&self->data->##field[i], PYDX12_OWNER, self->com_owner);\
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
		self->data->##field = (type*)new_array;\
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

#define PYDX12_STRING_GETTER(t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK, offsetof(t, field)}; static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	pydx12_memory_chunk* chunk = pydx12_chunk_get<t>(self, (void*)self->data->##field);\
	if (!chunk)\
		return PyUnicode_FromString((const char*)self->data->##field);\
	return PyUnicode_FromStringAndSize((const char*)chunk->ptr, chunk->size - 1);\
}

#define PYDX12_STRING_SETTER(t, field) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
{\
	if (value == Py_None)\
	{\
		pydx12_chunk_free<t>(self, (void*)self->data->##field);\
		self->data->##field = NULL;\
		return 0;\
	}\
	if (!PyUnicode_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a unicode object");\
		return -1;\
	}\
	pydx12_chunk_free<t>(self, (void*)self->data->##field);\
	Py_ssize_t size;\
	const char* utf8 = PyUnicode_AsUTF8AndSize(value, &size);\
	pydx12_memory_chunk* chunk = pydx12_chunk_alloc<t>(self, (void*) utf8, size + 1, 1);\
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

#define PYDX12_WSTRING_GETTER(t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK, offsetof(t, field)}; static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	return PyUnicode_FromWideChar(self->data->##field, -1);\
}

#define PYDX12_WSTRING_SETTER(t, field) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
{\
	if (value == Py_None)\
	{\
		pydx12_chunk_free<t>(self, (void*)self->data->##field);\
		self->data->##field = NULL;\
		return 0;\
	}\
	if (!PyUnicode_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a unicode object");\
		return -1;\
	}\
	pydx12_chunk_free<t>(self, (void*)self->data->##field);\
	Py_ssize_t size;\
	wchar_t* unicode = PyUnicode_AsWideCharString(value, &size);\
	pydx12_memory_chunk* chunk = pydx12_chunk_alloc<t>(self, (void*) unicode, (size * sizeof(wchar_t)) + 1, 1);\
	if (!chunk)\
	{\
		PyErr_SetString(PyExc_MemoryError, "unable to allocate memory chunk for " #t "::" #field);\
		return -1;\
	}\
	self->data->##field = (const wchar_t*)chunk->ptr;\
	return 0;\
}

#define PYDX12_WSTRING_GETTER_SETTER(t, field) PYDX12_WSTRING_GETTER(t, field)\
PYDX12_WSTRING_SETTER(t, field)

#define PYDX12_WSTRING_ARRAY_GETTER(t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK_ARRAY, offsetof(t, field)}; static PyObject* pydx12_##t##_get_##field(pydx12_##t* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	pydx12_memory_chunk* chunk = pydx12_chunk_get<t>(self, (void*)self->data->##field);\
	if (!chunk)\
		Py_RETURN_NONE;\
	PyObject* py_list = PyList_New(0);\
	for(Py_ssize_t i = 0; i < (Py_ssize_t)chunk->elements; i++)\
	{\
		PyObject* py_item = PyUnicode_FromWideChar((wchar_t*)self->data->##field[i], -1);\
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

#define PYDX12_WSTRING_ARRAY_SETTER(t, field) static int pydx12_##t##_set_##field(pydx12_##t* self, PyObject* value, void* closure)\
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
			pydx12_##t##_chunk_free(self,(void*)self->data->##field[i]);\
		}\
		pydx12_##t##_chunk_free(self,(void*)self->data->##field);\
		self->data->##field = NULL;\
	}\
	Py_ssize_t counter = 0;\
	while(PyObject* py_item = PyIter_Next(py_iter))\
	{\
		if (!PyUnicode_Check(py_item))\
		{\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_MemoryError, "expected an iterable of unicode objects");\
			return -1;\
		}\
		Py_ssize_t unicode_len;\
		wchar_t* unicode = PyUnicode_AsWideCharString(py_item, &unicode_len);\
		if (!unicode)\
		{\
			if (self->data->##field)\
				PyMem_Free((void*)self->data->##field);\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_MemoryError, "unable to allocate memory for unicode string");\
			return -1;\
		}\
		counter++;\
		wchar_t** new_array = (wchar_t**)PyMem_Realloc((void*)self->data->##field, sizeof(wchar_t*) * counter);\
		if (!new_array)\
		{\
			PyMem_Free(unicode);\
			if (self->data->##field)\
				PyMem_Free((void*)self->data->##field);\
			Py_DECREF(py_item);\
			Py_DECREF(py_iter);\
			PyErr_SetString(PyExc_MemoryError, "unable to allocate memory for unicode string");\
			return -1;\
		}\
		new_array[counter-1] = unicode;\
		self->data->##field = (LPCWSTR*)new_array;\
		pydx12_##t##_chunk_map(self, (void*)unicode, unicode_len+1, 1);\
		Py_DECREF(py_item);\
	}\
	Py_DECREF(py_iter);\
	if (self->data->##field)\
	{\
		pydx12_##t##_chunk_map(self, (void*)self->data->##field, sizeof(wchar_t*) * counter, counter);\
	}\
	return 0;\
}

#define PYDX12_WSTRING_ARRAY_GETTER_SETTER(t, field) PYDX12_WSTRING_ARRAY_GETTER(t, field)\
PYDX12_WSTRING_ARRAY_SETTER(t, field)

#define PYDX12_BOOL_GETTER(t, field) static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	if (self->data->##field)\
	{\
		Py_RETURN_TRUE;\
	}\
	Py_RETURN_FALSE;\
}

#define PYDX12_BOOL_SETTER(t, field) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
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

#define PYDX12_BUFFER_GETTER(t, field) static pydx12_field_track_type pydx12_##t##_##field##_track_chunk_type = {PYDX12_TRACK_TYPE_CHUNK, offsetof(t, field)}; static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	if (!self->data->##field)\
		Py_RETURN_NONE;\
	pydx12_memory_chunk* chunk = pydx12_chunk_get<t>(self, (void*)self->data->##field);\
	if (!chunk)\
		Py_RETURN_NONE;\
	return PyBytes_FromStringAndSize((const char*)chunk->ptr, chunk->size);\
}

#define PYDX12_BUFFER_SETTER(t, field, cast) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* value, void* closure)\
{\
	Py_buffer view;\
	if (value != Py_None && !PyObject_CheckBuffer(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a buffer object");\
		return -1; \
	}\
	pydx12_chunk_free<t>(self, (void*)self->data->##field);\
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
	pydx12_memory_chunk* chunk = pydx12_chunk_alloc<t>(self, view.buf, view.len, 1);\
	if (!chunk)\
	{\
		PyErr_SetString(PyExc_MemoryError, "unable to acquire buffer");\
		PyBuffer_Release(&view);\
		return -1;\
	}\
	self->data->##field = (cast*)chunk->ptr;\
	PyBuffer_Release(&view);\
	return 0;\
}

#define PYDX12_BUFFER_GETTER_SETTER(t, field, cast) PYDX12_BUFFER_GETTER(t, field)\
PYDX12_BUFFER_SETTER(t, field, cast)

#define PYDX12_COM_GETTER(t, field_type, field) static pydx12_field_track_type pydx12_##t##_##field##_track_com_type = {PYDX12_TRACK_TYPE_COM, offsetof(t, field)}; static PyObject* pydx12_##t##_get_##field(pydx12_Structure<t>* self, void* closure)\
{\
	if (self->data->##field)\
	{\
		return pydx12_com_instantiate<field_type>(self->data->##field, true);\
	}\
	Py_RETURN_NONE;\
}

#define PYDX12_COM_SETTER(t, field_type, field) static int pydx12_##t##_set_##field(pydx12_Structure<t>* self, PyObject* py_value, void* closure)\
{\
	field_type* value = NULL;\
	if (py_value && py_value != Py_None)\
	{\
		value = pydx12_com_check<field_type>(py_value);\
		if (!value)\
		{\
			PyErr_SetString(PyExc_ValueError, "value must be a " #field_type);\
			return -1;\
		}\
		pydx12_com_addref<t>(self, value);\
	}\
	if (self->data->##field)\
		pydx12_com_release<t>(self, self->data->##field);\
	self->data->##field = value;\
	return 0;\
}

#define PYDX12_COM_GETTER_SETTER(t, field_type, field) PYDX12_COM_GETTER(t, field_type, field)\
PYDX12_COM_SETTER(t, field_type, field)

#define PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, closure) {#field, (getter)pydx12_##t##_get_##field, (setter)pydx12_##t##_set_##field, #t " " #field " field", closure}
#define PYDX12_DECLARE_GETTER_CLOSURE(t, field, closure) {#field, (getter)pydx12_##t##_get_##field, NULL, #t " " #field " field", closure}

#define PYDX12_DECLARE_GETTER_SETTER(t, field) PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, NULL)
#define PYDX12_DECLARE_GETTER(t, field) PYDX12_DECLARE_GETTER_CLOSURE(t, field, NULL)

#define PYDX12_DECLARE_GETTER_SETTER_CHUNK(t, field) PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_chunk_type)
#define PYDX12_DECLARE_GETTER_CHUNK(t, field)  PYDX12_DECLARE_GETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_chunk_type)

#define PYDX12_DECLARE_GETTER_SETTER_COM(t, field) PYDX12_DECLARE_GETTER_SETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_com_type)
#define PYDX12_DECLARE_GETTER_COM(t, field)  PYDX12_DECLARE_GETTER_CLOSURE(t, field, (void*)&pydx12_##t##_##field##_track_com_type)

#define PYDX12_IMPORT_HANDLE(t, ht) ht pydx12_##t##_check(PyObject* py_object);

#define PYDX12_METHODS(t) static PyMethodDef pydx12_##t##_methods[]
#define PYDX12_GETSETTERS(t) static PyGetSetDef pydx12_##t##_getsetters[]

#define PYDX12_COM_CALL(func, ...) self->com_ptr->##func(__VA_ARGS__)

#define PYDX12_CALL_HRESULT(func, ...) { HRESULT ret = func(__VA_ARGS__); if (ret != S_OK)\
	{\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, #func "(): %s", err.ErrorMessage());\
	}\
}

#define PYDX12_COM_CALL_HRESULT(t, func, ...) { HRESULT ret = PYDX12_COM_CALL(func, __VA_ARGS__); if (ret != S_OK)\
	{\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, #t "::" #func "(): %s", err.ErrorMessage());\
	}\
}

#define PYDX12_COM_CALL_HRESULT_AND_FREE(object_to_free, t, func, ...) { HRESULT ret = PYDX12_COM_CALL(func, __VA_ARGS__); if (ret != S_OK)\
	{\
		PyMem_Free(object_to_free);\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, #t "::" #func "(): %s", err.ErrorMessage());\
	}\
}\
PyMem_Free(object_to_free)

#define PYDX12_COM_CALL_HRESULT_AND_BUFFER_RELEASE(buffer_to_release, t, func, ...) { HRESULT ret = PYDX12_COM_CALL(func, __VA_ARGS__); if (ret != S_OK)\
	{\
		PyBuffer_Release(&buffer_to_release);\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, #t "::" #func "(): %s", err.ErrorMessage());\
	}\
}\
PyBuffer_Release(&buffer_to_release)

#define PYDX12_UNICODE_CHECK(name) if (!PyUnicode_Check(py_##name))\
{\
	return PyErr_Format(PyExc_TypeError, "expected a unicode object");\
}\
wchar_t* name = PyUnicode_AsWideCharString(py_##name, NULL);\
if (!name)\
	return NULL;

#define PYDX12_UNICODE_CHECK_NONE(name) wchar_t* name = NULL; if (PyUnicode_Check(py_##name))\
{\
	name = PyUnicode_AsWideCharString(py_##name, NULL);\
	if (!name)\
		return NULL;\
}\
else if (py_##name != Py_None)\
{\
	return PyErr_Format(PyExc_TypeError, "expected a unicode object");\
}

#define PYDX12_ARG_CHECK(t, name) t* name = pydx12_structure_check<t>(py_##name);\
if (!name)\
	return PyErr_Format(PyExc_TypeError, "argument must be a " #t);

#define PYDX12_ARG_CHECK_COM(t, name) t* name = pydx12_com_check<t>(py_##name);\
if (!name)\
	return PyErr_Format(PyExc_TypeError, "argument must be a " #t);

#define PYDX12_ARG_CHECK_HANDLE(t, name) t* name = pydx12_handle_check<t>(py_##name);\
if (!name)\
	return PyErr_Format(PyExc_TypeError, "argument must be a " #t);

#define PYDX12_ARG_CHECK_NONE(t, name) t* name = NULL;\
if (py_##name && py_##name != Py_None)\
{\
	name = pydx12_structure_check<t>(py_##name);\
	if (!name)\
		return PyErr_Format(PyExc_TypeError, "argument must be a " #t);\
}

#define PYDX12_ARG_ITER_CHECK(t, name, append_null) UINT name##_counter = 0; t* name = pydx12_iter<t>(py_##name, &##name##_counter, append_null);\
if (!name)\
	return NULL;

#define PYDX12_ARG_ITER_CHECK_NONE(t, name, append_null) UINT name##_counter = 0; t* name = NULL;\
if (py_##name && py_##name != Py_None)\
{\
	name = pydx12_iter<t>(py_##name, &##name##_counter, append_null);\
	if (!name)\
		return NULL;\
}

#define PYDX12_INTERFACE_CREATE(t, func, ...) { t* interface_ptr;\
	HRESULT ret = func(__VA_ARGS__, __uuidof(t), (void**)&interface_ptr);\
	if (ret == S_OK)\
	{\
		return pydx12_com_instantiate<t>(interface_ptr, false);\
	}\
	else if (ret != E_NOINTERFACE)\
	{\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, "unable to create " #t ": %s", err.ErrorMessage());\
	}\
}

#define PYDX12_INTERFACE_CREATE_LAST(t, func, ...) PYDX12_INTERFACE_CREATE(t, func, __VA_ARGS__);\
return PyErr_Format(PyExc_ValueError, "unable to create " #t)

#define PYDX12_INTERFACE_CREATE_NO_ARGS(t, func) { t* interface_ptr;\
	HRESULT ret = func(__uuidof(t), (void**)&interface_ptr);\
	if (ret == S_OK)\
	{\
		return pydx12_com_instantiate<t>(interface_ptr, false);\
	}\
	else if (ret != E_NOINTERFACE)\
	{\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, "unable to create " #t ": %s", err.ErrorMessage());\
	}\
}

#define PYDX12_INTERFACE_CREATE_CAST(t, cast, func, ...) { t* interface_ptr;\
	HRESULT ret = func(__VA_ARGS__, (cast**)&interface_ptr);\
	if (ret == S_OK)\
	{\
		return pydx12_com_instantiate<t>(interface_ptr, false);\
	}\
	else if (ret != E_NOINTERFACE)\
	{\
		_com_error err(ret);\
		return PyErr_Format(PyExc_Exception, "unable to create " #t ": %s", err.ErrorMessage());\
	}\
}

#define PYDX12_EXCEPTION(t, func) { _com_error err(ret);\
	return PyErr_Format(PyExc_Exception, #t "::" #func "(): %s", err.ErrorMessage());\
}

#define PYDX12_INTERFACE_CREATE_CAST_LAST(t, cast, func, ...) PYDX12_INTERFACE_CREATE_CAST(t, cast, func, __VA_ARGS__);\
return PyErr_Format(PyExc_Exception, "unable to create " #t)

#define PYDX12_INTERFACE_CREATE_NO_ARGS_LAST(t, func) PYDX12_INTERFACE_CREATE_NO_ARGS(t, func);\
return PyErr_Format(PyExc_Exception, "unable to create " #t)

#define PYDX12_HANDLE_NEW(t, value, destroy) pydx12_##t* py_##value = PyObject_New(pydx12_##t, pydx12_##t##_get_type());\
if (!py_##value)\
{\
	value->##destroy();\
	return NULL;\
}\
py_##value->handle = value;\
return (PyObject*)py_##value

#define PYDX12_HANDLE_NEW_WITH_COM(t, value, destroy, com_field) pydx12_##t* py_##value = PyObject_New(pydx12_##t, pydx12_##t##_get_type());\
if (!py_##value)\
{\
	value->##destroy();\
	return NULL;\
}\
py_##value->handle = value;\
py_##value->##com_field = self->com_ptr;\
self->com_ptr->AddRef();\
return (PyObject*)py_##value

/** Custom Structures **/

using Event = HANDLE;

struct Window
{
	HWND hwnd;
	PyObject* py_window_proc;
	WINDOWPLACEMENT pre_fullscreen_placement;
	bool py_window_proc_exception;
};