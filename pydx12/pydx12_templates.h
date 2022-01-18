#pragma once

#include <Python.h>
#include <dxgi1_6.h>
#include <d3d12.h>
#include <d3dcompiler.h>
#include <xaudio2.h>
#include <dxcapi.h>
#include <comdef.h>

struct pydx12_memory_chunk
{
	void* ptr;
	size_t size;
	size_t elements;
};

#define PYDX12_TRACK_TYPE_CHUNK 0
#define PYDX12_TRACK_TYPE_COM 1
#define PYDX12_TRACK_TYPE_CHUNK_ARRAY 2

struct pydx12_field_track_type
{
	size_t type;
	size_t offset;
};

struct pydx12_com_track
{
	IUnknown* com_ptr;
	size_t refs;
};

template<typename T>
struct pydx12_Structure
{
	PyObject_HEAD;
	T* data;
	size_t data_len;
	PyObject* data_owner;
	IUnknown* com_owner;
	pydx12_memory_chunk* chunks;
	size_t number_of_chunks;
	pydx12_com_track* coms;
	size_t number_of_coms;
	PyObject* weakreflist;
};

template<typename T>
struct pydx12_COM
{
	PyObject_HEAD;
	T* com_ptr;
};

template<typename T>
struct pydx12_HANDLE
{
	PyObject_HEAD;
	T handle;
};


template<typename T>
PyTypeObject* pydx12_get_type();

template<typename T>
const char* pydx12_get_type_name();


template<typename T>
PyObject* pydx12_instantiate_with_size(T* data, PyObject* data_owner, IUnknown* com_owner, const size_t len)
{
	pydx12_Structure<T>* py_object = PyObject_New(pydx12_Structure<T>, pydx12_get_type<T>());
	if (!py_object)
	{
		return NULL;
	}
	char* offset = (char*)py_object;
	memset(offset + sizeof(PyObject), 0, sizeof(pydx12_Structure<T>) - sizeof(PyObject));
	py_object->data_owner = data_owner;
	py_object->data_len = len;
	if (!data_owner)
	{
		py_object->data = (T*)PyMem_Malloc(len);
		if (!py_object->data)
			return NULL;
		if (data)
			*(py_object->data) = *data;
	}
	else
	{
		py_object->data = data;
		Py_INCREF(data_owner);
	}
	if (com_owner)
	{
		com_owner->AddRef();
		py_object->com_owner = com_owner;
	}
	return (PyObject*)py_object;
}

template<typename T>
PyObject* pydx12_instantiate(T* data, PyObject* data_owner, IUnknown* com_owner)
{
	return pydx12_instantiate_with_size<T>(data, data_owner, com_owner, sizeof(T));
}

template<typename T>
T* pydx12_structure_get_data(PyObject* py_object)
{
	pydx12_Structure<T>* pydx12_object = (pydx12_Structure<T>*)py_object;
	return pydx12_object->data;
}

template<typename T>
T* pydx12_structure_check(PyObject* py_object)
{
	if (!PyObject_IsInstance(py_object, (PyObject*)pydx12_get_type<T>))
	{
		return NULL;
	}
	return pydx12_structure_get_data<T>(py_object);
}

template<typename T>
T* pydx12_com_get_ptr(PyObject* py_object)
{
	pydx12_COM<T>* pydx12_object = (pydx12_COM<T>*)py_object;
	return pydx12_object->com_ptr;
}

template<typename T>
T* pydx12_com_check(PyObject* py_object)
{
	if (!PyObject_IsInstance(py_object, (PyObject*)pydx12_get_type<T>))
	{
		return NULL;
	}
	return pydx12_com_get_ptr<T>(py_object);
}

template<typename T>
T* pydx12_handle_get_ptr(PyObject* py_object)
{
	pydx12_HANDLE<T>* pydx12_object = (pydx12_HANDLE<T>*)py_object;
	return &pydx12_object->handle;
}

template<typename T>
T* pydx12_handle_check(PyObject* py_object)
{
	if (!PyObject_IsInstance(py_object, (PyObject*)pydx12_get_type<T>))
	{
		return NULL;
	}
	return pydx12_handle_get_ptr<T>(py_object);
}

template<typename T>
void pydx12_com_addref(pydx12_Structure<T>* self, IUnknown* com_ptr)
{
	pydx12_Structure<T>* owner = (pydx12_Structure<T>*) (self->data_owner ? self->data_owner : (PyObject*)self);
	for (size_t i = 0; i < owner->number_of_coms; i++)
	{
		pydx12_com_track* com_track = &owner->coms[i];
		if (com_track->com_ptr == com_ptr)
		{
			com_track->refs++;
			com_track->com_ptr->AddRef();
			return;
		}
	}
	for (size_t i = 0; i < owner->number_of_coms; i++)
	{
		pydx12_com_track* com_track = &owner->coms[i];
		if (com_track->com_ptr == NULL)
		{
			com_track->com_ptr = com_ptr;
			com_track->refs = 1;
			com_track->com_ptr->AddRef();
			return;
		}
	}
	owner->number_of_tracked_coms++;
	pydx12_com_track* new_com_tracked = (pydx12_com_track*)PyMem_Realloc(owner->coms, sizeof(pydx12_com_track) * owner->number_of_coms);
	if (!new_com_tracked)
	{
		return;
	}
	owner->coms = new_com_tracked;
	owner->coms[owner->number_of_coms - 1].com_ptr = com_ptr;
	owner->coms[owner->number_of_coms - 1].refs = 1;
	com_ptr->AddRef();
}

template<typename T>
void pydx12_com_release(pydx12_Structure<T>* self, IUnknown* com_ptr)
{
	pydx12_Structure<T>* owner = (pydx12_Structure<T>*) (self->data_owner ? self->data_owner : (PyObject*)self);
	for (size_t i = 0; i < owner->number_of_tracked_coms; i++)
	{
		pydx12_com_track* com_track = &owner->tracked_coms[i];
		if (com_track->com_ptr == com_ptr)
		{
			assert(com_track->refs > 0);
			com_track->refs--;
			com_track->com_ptr->Release();
			if (com_track->refs == 0)
				com_track->com_ptr = NULL;
			return;
		}
	}
}

template<typename T>
void pydx12_chunk_free(pydx12_Structure<T>* self, void* addr)
{
	if (!addr)
		return;
	pydx12_Structure<T>* owner = (pydx12_Structure<T>*) (self->data_owner ? self->data_owner : (PyObject*)self);
	for (size_t i = 0; i < owner->number_of_chunks; i++)
	{
		pydx12_memory_chunk* chunk = &owner->chunks[i];
		if (chunk->ptr == addr)
		{
			PyMem_Free(chunk->ptr);
			chunk->ptr = NULL;
			chunk->size = 0;
			chunk->elements = 0;
			break;
		}
	}
}

template<typename T>
void pydx12_chunk_clear(pydx12_Structure<T>* self, T* data)
{
	PyGetSetDef* getset = pydx12_get_type<T>().tp_getset;
	while (getset->name)
	{
		if (getset->closure != NULL)\
		{
			pydx12_field_track_type* track_type = (pydx12_field_track_type*)getset->closure;
			if (track_type->type == PYDX12_TRACK_TYPE_CHUNK)
			{
				void** ptr = (void**)(((char*)data) + track_type->offset);
				pydx12_chunk_free<T>(self, *ptr);
			}
			if (track_type->type == PYDX12_TRACK_TYPE_CHUNK_ARRAY)
			{
				void** ptr = (void**)(((char*)data) + track_type->offset);
				pydx12_memory_chunk* chunk = pydx12_chunk_get<T>(self, *ptr);
				if (chunk)
				{
					void** array_ptr = (void**)chunk->ptr;
					for (size_t i = 0; i < chunk->elements; i++)
					{
						pydx12_chunk_free<T>(self, array_ptr[i]);
					}
				}
				pydx12_chunk_free<T>(self, *ptr);
			}
			else if (track_type->type == PYDX12_TRACK_TYPE_COM)
			{
				IUnknown** ptr = (IUnknown**)(((char*)data) + track_type->offset);
				if (*ptr)
					pydx12_com_release<T>(self, *ptr);
			}
		}
		getset++;
	}
}

template<typename T>
T* pydx12_iter(PyObject* py_object, UINT* list_counter, const bool append_null)
{
	PyObject* py_iter = PyObject_GetIter(py_object);
	if (!py_iter)
	{
		return NULL;
	}
	T* list = NULL;
	*list_counter = 0;
	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		T* item = pydx12_structure_check<T>(py_item);
		if (!item)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (list)
				PyMem_Free(list);
			return (T*)PyErr_Format(PyExc_TypeError, "argument must be an iterable of %s", pydx12_get_type_name<T>());
		}
		(*list_counter)++;
		T* new_list = (T*)PyMem_Realloc(list, sizeof(T) * (*list_counter));
		if (!new_list)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (list)
				PyMem_Free(list);
			return (T*)PyErr_Format(PyExc_MemoryError, "unable to allocate memory for %s array", pydx12_get_type_name<T>());
		}
		list = new_list;
		list[(*list_counter) - 1] = *item;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);
	if (append_null)
	{
		(*list_counter)++;
		T* new_list = (T*)PyMem_Realloc(list, sizeof(T) * (*list_counter));
		if (!new_list)
		{
			if (list)
				PyMem_Free(list);
			return (T*)PyErr_Format(PyExc_MemoryError, "unable to allocate memory for %s array", pydx12_get_type_name<T>());
		}
		list = new_list;
		memset(&list[(*list_counter) - 1], 0, sizeof(T));
	}
	return list;
}

template<typename T>
void pydx12_dealloc(pydx12_Structure<T>* self)
{
	if (self->data)
	{
		if (!self->data_owner)
		{
			PyMem_Free(self->data);
		}
		else
		{
			Py_DECREF(self->data_owner);
		}
	}

	if (self->com_owner)
		self->com_owner->Release();

	for (size_t i = 0; i < self->number_of_chunks; i++)
	{
		if (self->chunks[i].ptr)
		{
			PyMem_Free(self->chunks[i].ptr);
		}
	}

	if (self->chunks)
		PyMem_Free(self->chunks);

	for (size_t i = 0; i < self->number_of_coms; i++)
	{
		for (size_t j = 0; j < self->coms[i].refs; j++)
		{
			self->coms[i].com_ptr->Release();
		}
	}

	if (self->coms)
		PyMem_Free(self->coms);

	if (self->weakreflist)
		PyObject_ClearWeakRefs((PyObject*)self);

	Py_TYPE(self)->tp_free((PyObject*)self);
}

template<typename T>
PyObject* pydx12_com_instantiate(T* com_ptr, const bool add_ref)
{
	pydx12_COM<T>* py_object = PyObject_New(pydx12_COM<T>, pydx12_get_type<T>());
	if (!py_object)
	{
		if (com_ptr && !add_ref)
			com_ptr->Release();
		return NULL;
	}
	char* offset = (char*)py_object;
	memset(offset + sizeof(PyObject), 0, sizeof(pydx12_COM<T>) - sizeof(PyObject));
	if (com_ptr && add_ref)
	{
		com_ptr->AddRef();
	}
	py_object->com_ptr = com_ptr;
	return (PyObject*)py_object;
}

template<typename T>
int pydx12_init(pydx12_Structure<T>* self, PyObject* args, PyObject* kwds)
{
	self->data = (T*)PyMem_Calloc(1, sizeof(T));
	if (!self->data)
	{
		return -1;
	}
	self->data_len = sizeof(T);
	self->data_owner = NULL;
	PyTypeObject* type = pydx12_get_type<T>();
	if (type->tp_getset && kwds != NULL && PyDict_Check(kwds) && PyDict_Size(kwds))
	{
		PyObject* py_key, * py_value;
		Py_ssize_t pos = 0;
		while (PyDict_Next(kwds, &pos, &py_key, &py_value))
		{
			const char* field = PyUnicode_AsUTF8(py_key);
			int found = 0;
			PyGetSetDef* getset = type->tp_getset;
			while (getset->name)
			{
				if (!strcmp(field, getset->name))
				{
					if (!getset->set)
					{
						PyErr_Format(PyExc_KeyError, "field %s is not writable", field);
						return -1;
					}
					if (getset->set((PyObject*)self, py_value, getset->closure))
					{
						return -1;
					}
					found = 1;
					break;
				}
				getset++;
			}
			if (!found)
			{
				PyErr_Format(PyExc_KeyError, "unknown field %s", field);
				return -1;
			}
		}
	}
	return 0;
}

template<typename T>
PyObject* pydx12_get_fields(pydx12_Structure<T>* self)
{
	PyObject* py_list = PyList_New(0);
	PyGetSetDef* getset = pydx12_get_type<T>()->tp_getset;
	while (getset->name)
	{
		PyObject* py_name = PyUnicode_FromString(getset->name);
		PyList_Append(py_list, py_name);
		Py_DECREF(py_name);
		getset++;
	}
	return py_list;
}

template<typename T>
PyObject* pydx12_to_dict(pydx12_Structure<T>* self)
{
	PyObject* py_dict = PyDict_New();
	PyGetSetDef* getset = pydx12_get_type<T>()->tp_getset;
	while (getset->name)
	{
		if (getset->get)
		{
			PyObject* py_value = getset->get((PyObject*)self, getset->closure);
			if (!py_value)
			{
				Py_DECREF(py_dict);
				return NULL;
			}
			PyDict_SetItemString(py_dict, getset->name, py_value);
			Py_DECREF(py_value);
		}
		getset++;
	}
	return py_dict;
}

template<typename T>
PyObject* pydx12_to_bytes(pydx12_Structure<T>* self)
{
	if (!self->data)
		Py_RETURN_NONE;
	return PyBytes_FromStringAndSize((const char*)self->data, self->data_len);
}

template<typename T>
PyObject* pydx12_to_bytearray(pydx12_Structure<T>* self)
{
	if (!self->data)
		Py_RETURN_NONE;
	return PyByteArray_FromStringAndSize((const char*)self->data, self->data_len);
}

template<typename T>
PyObject* pydx12_get_chunks(pydx12_Structure<T>* self)
{
	PyObject* py_list = PyList_New(0);
	for (size_t i = 0; i < self->number_of_chunks; i++)
	{
		if (!self->chunks[i].ptr)
			continue; \
			PyObject* py_chunk = Py_BuildValue("(KKK)", self->chunks[i].ptr, self->chunks[i].size, self->chunks[i].elements);
		PyList_Append(py_list, py_chunk);
		Py_DECREF(py_chunk);
	}
	return py_list;
}

template<typename T>
PyObject* pydx12_get_ptr(pydx12_Structure<T>* self)
{
	if (!self->data)
		Py_RETURN_NONE;
	return PyLong_FromUnsignedLongLong((unsigned long long)self->data);
}

template<typename T>
int pydx12_register(PyObject* m)
{
	PyTypeObject* type = pydx12_get_type<T>();
	if (PyType_Ready(type) < 0)
		return -1;
	Py_INCREF(type);
	if (PyModule_AddObject(m, pydx12_get_type_name<T>(), (PyObject*)type) < 0)
	{
		Py_DECREF(type);
		return -1;
	}
	return 0;
}

template<typename T>
PyObject* pydx12_sq_item(pydx12_Structure<T>* self, Py_ssize_t index)\
{
	return pydx12_instantiate<T>(self->data + index, PYDX12_OWNER, self->com_owner);
}

template<typename T>
int pydx12_get_buffer(pydx12_Structure<T>* exporter, Py_buffer* view, int flags)
{
	PyBuffer_FillInfo(view, (PyObject*)exporter, exporter->data, exporter->data_len, 0, flags);
	return 0;
}

template<typename T>
void pydx12_release_buffer(pydx12_Structure<T>* exporter, Py_buffer* view)
{
}

template<typename T>
void pydx12_com_dealloc(pydx12_COM<T>* self)
{
	if (self->com_ptr)
	{
		self->com_ptr->Release();
	}
	Py_TYPE(self)->tp_free((PyObject*)self);
}

template<typename T>
int pydx12_com_init(pydx12_COM<T>* self, PyObject* args, PyObject* kwds)
{
	PyObject* py_unknown;
	if (!PyArg_ParseTuple(args, "O", &py_unknown))
	{
		return -1;
	}
	IUnknown* unknown = pydx12_com_check<IUnknown>(py_unknown);
	if (!unknown)
	{
		PyErr_SetString(PyExc_ValueError, "expected a IUnknown");
		return -1;
	}
	self->com_ptr = NULL;
	if (unknown->QueryInterface<T>(&self->com_ptr) != S_OK)
	{
		PyErr_Format(PyExc_ValueError, "QueryInterface<%s> failed", pydx12_get_type_name<T>());
		return -1;
	}
	return 0;
}

template<typename T>
PyObject* pydx12_com_richcompare(pydx12_COM<T>* self, PyObject* other, int op)
{
	if (op == Py_EQ)
	{
		IUnknown* unknown = pydx12_com_check<IUnknown>(other);
		if (unknown)
		{
			if (self->com_ptr == unknown)
			{
				Py_RETURN_TRUE;
			}
		}
	}
	Py_RETURN_FALSE;
}

template<typename T>
int pydx12_chunk_fix(pydx12_Structure<T>* self, pydx12_Structure<T>* value, T* data)
{
	PyGetSetDef* getset = pydx12_get_type<T>()->tp_getset;
	while (getset->name)
	{
		if (getset->closure != NULL)
		{
			pydx12_field_track_type* track_type = (pydx12_field_track_type*)getset->closure;
			if (track_type->type == PYDX12_TRACK_TYPE_CHUNK)
			{
				void** ptr = (void**)(((char*)data) + track_type->offset);
				pydx12_memory_chunk* chunk = pydx12_chunk_get<T>(value, *ptr);
				if (chunk)
				{
					chunk = pydx12_chunk_alloc<T>(self, chunk->ptr, chunk->size, chunk->elements);
					if (!chunk)
						return -1;
					*ptr = chunk->ptr;
				}
			}
			else if (track_type->type == PYDX12_TRACK_TYPE_CHUNK_ARRAY)
			{
				void** ptr = (void**)(((char*)data) + track_type->offset);
				pydx12_memory_chunk* chunk = pydx12_chunk_get<T>(value, *ptr);
				if (chunk)
				{
					pydx12_memory_chunk* new_chunk = pydx12_chunk_alloc<T>(self, chunk->ptr, chunk->size, chunk->elements);
					if (!new_chunk)
						return -1;
					bool failed = false;
					void** array_ptr = (void**)chunk->ptr;
					void** new_array_ptr = (void**)new_chunk->ptr;
					for (size_t i = 0; i < new_chunk->elements; i++)
					{
						new_array_ptr[i] = NULL;
						if (failed)
							continue;
						pydx12_memory_chunk* item_chunk = pydx12_chunk_get<T>(value, array_ptr[i]);
						if (item_chunk)
						{
							new_array_ptr[i] = pydx12_chunk_alloc<T>(self, item_chunk->ptr, item_chunk->size, item_chunk->elements);
							if (!new_array_ptr[i])
								failed = true;
						}
						else
							failed = true;
					}
					if (failed)
						return -1;
					*ptr = new_chunk->ptr;
				}
			}
			else if (track_type->type == PYDX12_TRACK_TYPE_COM)
			{
				IUnknown** ptr = (IUnknown**)(((char*)data) + track_type->offset);
				if (*ptr)
				{
					pydx12_com_addref<T>(self, *ptr);
				}
			}
		}
		getset++;
	}
	return 0;
}

template<typename T>
pydx12_memory_chunk* pydx12_chunk_alloc(pydx12_Structure<T>* self, void* addr, const size_t size, const size_t elements)
{
	if (!addr)
		return NULL;
	pydx12_Structure<T>* owner = (pydx12_Structure<T>*) (self->data_owner ? self->data_owner : (PyObject*)self);
	for (size_t i = 0; i < owner->number_of_chunks; i++)
	{
		pydx12_memory_chunk* chunk = &owner->chunks[i];
		if (chunk->ptr == NULL)
		{
			void* ptr = PyMem_Malloc(size);
			if (!ptr)
				return NULL;
			memcpy(ptr, addr, size);
			chunk->ptr = ptr;
			chunk->size = size;
			chunk->elements = elements;
			return chunk;
		}
	}
	owner->number_of_chunks++;
	pydx12_memory_chunk* new_chunks = (pydx12_memory_chunk*)PyMem_Realloc(owner->chunks, sizeof(pydx12_memory_chunk) * owner->number_of_chunks);
	if (!new_chunks)
	{
		return NULL;
	}
	pydx12_memory_chunk* chunk = &new_chunks[owner->number_of_chunks - 1];
	void* ptr = PyMem_Malloc(size);
	if (!ptr)
	{
		chunk->ptr = NULL;
		return NULL;
	}
	owner->chunks = new_chunks;
	memcpy(ptr, addr, size);
	chunk->ptr = ptr;
	chunk->size = size;
	chunk->elements = elements;
	return chunk;
}

template<typename T>
pydx12_memory_chunk* pydx12_chunk_get(pydx12_Structure<T>* self, void* addr)
{
	if (!addr)
		return NULL;
	pydx12_Structure<T>* owner = (pydx12_Structure<T>*) (self->data_owner ? self->data_owner : (PyObject*)self);
	for (size_t i = 0; i < owner->number_of_chunks; i++)
	{
		pydx12_memory_chunk* chunk = &owner->chunks[i];
		if (chunk->ptr == addr)
		{
			return chunk;
		}
	}
	return NULL;
}