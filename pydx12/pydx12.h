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
		printf("[2] allocing " #t " com_owner: %p\n", com_owner);\
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
static void pydx12_##t##_dealloc(pydx12_##t* self)\
{\
	printf("dealloc " #t " %p\n", self->com_owner);\
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
	printf("dealloc " #t " step %p\n", self->com_owner);\
	if (self->com_owner)\
		self->com_owner->Release();\
	printf("dealloced " #t "\n");\
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
	return pydx12_##t##_instantiate(self->data + index, (PyObject*)self, self->com_owner);\
}\
static PySequenceMethods pydx12_##t##_sequence_methods = {\
	NULL,\
	NULL,\
	NULL,\
	(ssizeargfunc)pydx12_##t##_sq_item\
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
		printf("AddRef() for " #t " : %ld\n",com_ptr->AddRef());\
	}\
	else\
	{\
		printf("NoRef for " #t "\n");\
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
		printf("com release for " #t " %ld\n", self->com_ptr->Release());\
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
	if (unknown->QueryInterface<t>(&self->com_ptr) != S_OK)\
	{\
		PyErr_SetString(PyExc_ValueError, "QueryInterface<" #t "> failed");\
		return -1;\
	}\
	self->com_ptr->AddRef();\
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
pydx12_##t##Type.tp_dealloc = (destructor)pydx12_##t##_dealloc;\
pydx12_##t##Type.tp_getset = pydx12_##t##_getsetters;\
pydx12_##t##Type.tp_init = (initproc)pydx12_##t##_init;\
pydx12_##t##Type.tp_as_sequence = &pydx12_##t##_sequence_methods;\
PYDX12_REGISTER(t)

#define PYDX12_REGISTER_COM(t, s) pydx12_##t##Type.tp_base = pydx12_##s##_get_type();\
pydx12_##t##Type.tp_new = PyType_GenericNew;\
pydx12_##t##Type.tp_init = (initproc)pydx12_##t##_init;\
PYDX12_REGISTER_COM_BASE(t)

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
	return pydx12_##type##_instantiate(&self->data->##field, (PyObject*)self, self->com_owner);\
}

#define PYDX12_STRUCT_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	self->data->##field = *data;\
	return 0;\
}

#define PYDX12_STRUCT_GETTER_SETTER(t, field, type) PYDX12_STRUCT_GETTER(t, field, type)\
PYDX12_STRUCT_SETTER(t, field, type)

#define PYDX12_STRUCT_CARRAY_GETTER(t, field, type) static PyObject* pydx12_##t##_get##field(pydx12_##t* self, void* closure)\
{\
	return pydx12_##type##_instantiate(&self->data->##field[0], (PyObject*)self, self->com_owner);\
}

#define PYDX12_STRUCT_CARRAY_SETTER(t, field, type) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	type* data = pydx12_##type##_check(value);\
	if (!data)\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a " #type);\
		return -1;\
	}\
	self->data->##field##[0] = *data;\
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
		return NULL;\
	}\
	if (self->data->##field)\
	{\
		PyMem_Free((void*)self->data->##field);\
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
		self->data->##field = (const type*)new_array;\
		Py_DECREF(py_item);\
	}\
	Py_DECREF(py_iter);\
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

#define PYDX12_STRING_SETTER(t, field, py_ref_field) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
{\
	if (!PyUnicode_Check(value))\
	{\
		PyErr_SetString(PyExc_TypeError, "value must be a unicode object");\
		return -1;\
	}\
	Py_XDECREF(self->##py_ref_field);\
	self->data->##field = PyUnicode_AsUTF8(value);\
	self->##py_ref_field = value;\
	Py_INCREF(self->##py_ref_field);\
	return 0;\
}

#define PYDX12_STRING_GETTER_SETTER(t, field, py_ref_field) PYDX12_STRING_GETTER(t, field)\
PYDX12_STRING_SETTER(t, field, py_ref_field)

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

#define PYDX12_BUFFER_SETTER(t, field, py_ref_field) static int pydx12_##t##_set##field(pydx12_##t* self, PyObject* value, void* closure)\
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
	Py_XDECREF(self->##py_ref_field);\
	if (value == Py_None)\
	{\
		self->data->##field = NULL;\
		self->##py_ref_field = NULL;\
	}\
	else\
	{\
		self->data->##field = view.buf;\
		self->##py_ref_field = value;\
		Py_INCREF(self->##py_ref_field);\
		PyBuffer_Release(&view);\
	}\
	return 0;\
}

#define PYDX12_BUFFER_GETTER_SETTER(t, field, field_size, py_ref_field) PYDX12_BUFFER_GETTER(t, field, field_size)\
PYDX12_BUFFER_SETTER(t, field, py_ref_field)


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
		}\
		value->AddRef();\
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
t* pydx12_##t##_check(PyObject* py_object)

#define PYDX12_IMPORT_COM(t) PyObject* pydx12_##t##_instantiate(t* com_ptr, const bool add_ref);\
t* pydx12_##t##_check(PyObject* py_object);\
PyTypeObject* pydx12_##t##_get_type()

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

#define PYDX12_ARG_CHECK_NONE(t, name) t* name = NULL;\
if (py_##name && py_##name != Py_None)\
{\
	name = pydx12_##t##_check(py_##name);\
	if (!name)\
		return PyErr_Format(PyExc_TypeError, "argument must be a " #t);\
}

#define PYDX12_COM_INSTANTIATE(t, object, add_ref) pydx12_##t##_instantiate(object, add_ref)

/** Common imports */
PYDX12_IMPORT_COM(IUnknown);