#include "pydx12.h"

PYDX12_TYPE(D3D12_DEPTH_STENCIL_VALUE);
PYDX12_FLOAT_GETTER_SETTER(D3D12_DEPTH_STENCIL_VALUE, Depth, FLOAT);
PYDX12_GETTER_SETTER(D3D12_DEPTH_STENCIL_VALUE, Stencil, UnsignedLong, UINT8);
PYDX12_GETSETTERS(D3D12_DEPTH_STENCIL_VALUE) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DEPTH_STENCIL_VALUE, Depth),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DEPTH_STENCIL_VALUE, Stencil),
	{NULL}  /* Sentinel */
};

PYDX12_TYPE_COM(ID3D12Device);
PYDX12_TYPE_COM(ID3D12Device1);
PYDX12_TYPE_COM(ID3D12Device2);
PYDX12_TYPE_COM(ID3D12Device3);
PYDX12_TYPE_COM(ID3D12Device4);
PYDX12_TYPE_COM(ID3D12Device5);
PYDX12_TYPE_COM(ID3D12Device6);
PYDX12_TYPE_COM(ID3D12Device7);
PYDX12_TYPE_COM(ID3D12Device8);
PYDX12_TYPE_COM(ID3D12InfoQueue);
PYDX12_TYPE_COM(ID3D12DeviceChild);
PYDX12_TYPE_COM(ID3D12Pageable);
PYDX12_TYPE_COM(ID3D12Heap);

static PyObject* pydx12_ID3D12Device_CreateCommittedResource(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_heap_properties;
	D3D12_HEAP_FLAGS py_heap_flags;
	PyObject* py_resource_desc;
	D3D12_RESOURCE_STATES initial_resource_state;
	PyObject* py_clear_value = NULL;
	if (!PyArg_ParseTuple(args, "OLOL|O", &py_heap_properties, &py_heap_flags, &py_resource_desc, &initial_resource_state, &py_clear_value))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_HEAP_PROPERTIES, heap_properties);
	PYDX12_ARG_CHECK(D3D12_RESOURCE_DESC, resource_desc);

	PYDX12_ARG_CHECK_NONE(D3D12_CLEAR_VALUE, clear_value);

	ID3D12Resource* resource;
	if (self->com_ptr->CreateCommittedResource(heap_properties, py_heap_flags, resource_desc, initial_resource_state, clear_value, __uuidof(ID3D12Resource), (void**)&resource) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create ID3D12Resource");
	}

	return pydx12_com_instantiate<ID3D12Resource>(resource, false);
}

static PyObject* pydx12_ID3D12Device_CreatePlacedResource(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_heap;
	UINT64 heap_offset;
	PyObject* py_resource_desc;
	D3D12_RESOURCE_STATES initial_resource_state;
	PyObject* py_clear_value = NULL;
	if (!PyArg_ParseTuple(args, "OKOL|O", &py_heap, &heap_offset, &py_resource_desc, &initial_resource_state, &py_clear_value))
		return NULL;

	PYDX12_ARG_CHECK(ID3D12Heap, heap);
	PYDX12_ARG_CHECK(D3D12_RESOURCE_DESC, resource_desc);

	PYDX12_ARG_CHECK_NONE(D3D12_CLEAR_VALUE, clear_value);

	ID3D12Resource* resource;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreatePlacedResource, heap, heap_offset, resource_desc, initial_resource_state, clear_value, __uuidof(ID3D12Resource), (void**)&resource);

	return pydx12_com_instantiate<ID3D12Resource>(resource, false);
}

static PyObject* pydx12_ID3D12Device_CreateHeap(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_desc;
	if (!PyArg_ParseTuple(args, "O", &py_desc))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_HEAP_DESC, desc);

	ID3D12Heap* heap;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreateHeap, desc, __uuidof(ID3D12Heap), (void**)&heap);

	return pydx12_com_instantiate<ID3D12Heap>(heap, false);
}

static PyObject* pydx12_ID3D12Device_GetAdapterLuid(pydx12_COM<ID3D12Device>* self)
{
	return pydx12_instantiate<LUID>(&self->com_ptr->GetAdapterLuid(), NULL, NULL);
}

static PyObject* pydx12_ID3D12Device_CreateCommandAllocator(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	D3D12_COMMAND_LIST_TYPE type;
	if (!PyArg_ParseTuple(args, "L", &type))
		return NULL;

	ID3D12CommandAllocator* allocator;
	if (self->com_ptr->CreateCommandAllocator(type, __uuidof(ID3D12CommandAllocator), (void**)&allocator) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create ID3D12CommandAllocator");
	}

	return pydx12_com_instantiate<ID3D12CommandAllocator>(allocator, false);
}

static PyObject* pydx12_ID3D12Device_CreateCommandQueue(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_command_queue_desc;
	if (!PyArg_ParseTuple(args, "O", &py_command_queue_desc))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_COMMAND_QUEUE_DESC, command_queue_desc);

	ID3D12CommandQueue* queue;
	if (self->com_ptr->CreateCommandQueue(command_queue_desc, __uuidof(ID3D12CommandQueue), (void**)&queue) != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to create ID3D12CommandQueue");
	}

	return pydx12_com_instantiate<ID3D12CommandQueue>(queue, false);
}

static PyObject* pydx12_ID3D12Device_CreateCommandList(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	UINT node_mask;
	D3D12_COMMAND_LIST_TYPE type;
	PyObject* py_command_allocator;
	PyObject* py_initial_state = NULL;
	if (!PyArg_ParseTuple(args, "ILO|O", &node_mask, &type, &py_command_allocator, &py_initial_state))
		return NULL;

	PYDX12_ARG_CHECK(ID3D12CommandAllocator, command_allocator);
	PYDX12_ARG_CHECK_NONE(ID3D12PipelineState, initial_state);

	ID3D12GraphicsCommandList* command_list;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreateCommandList, node_mask, type, command_allocator, initial_state, __uuidof(ID3D12GraphicsCommandList), (void**)&command_list);

	return pydx12_com_instantiate<ID3D12GraphicsCommandList>(command_list, false);
}

static PyObject* pydx12_ID3D12Device_CreateFence(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	UINT64 initial_value = 0;
	D3D12_FENCE_FLAGS flags = D3D12_FENCE_FLAG_NONE;
	if (!PyArg_ParseTuple(args, "|KL", &initial_value, &flags))
		return NULL;

	ID3D12Fence* fence;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreateFence, initial_value, flags, __uuidof(ID3D12Fence), (void**)&fence);

	return pydx12_com_instantiate<ID3D12Fence>(fence, false);
}

static PyObject* pydx12_ID3D12Device_CreateDescriptorHeap(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_descriptor_heap_desc;
	if (!PyArg_ParseTuple(args, "O", &py_descriptor_heap_desc))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_DESCRIPTOR_HEAP_DESC, descriptor_heap_desc);

	ID3D12DescriptorHeap* descriptor_heap;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreateDescriptorHeap, descriptor_heap_desc, __uuidof(ID3D12DescriptorHeap), (void**)&descriptor_heap);

	return pydx12_com_instantiate<ID3D12DescriptorHeap>(descriptor_heap, false);
}

static PyObject* pydx12_ID3D12Device_CreateShaderResourceView(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_resource;
	PyObject* py_shader_resource_view_desc;
	PyObject* py_dest_descriptor;
	if (!PyArg_ParseTuple(args, "OOO", &py_resource, &py_shader_resource_view_desc, &py_dest_descriptor))
		return NULL;

	PYDX12_ARG_CHECK_NONE(ID3D12Resource, resource);
	PYDX12_ARG_CHECK_NONE(D3D12_SHADER_RESOURCE_VIEW_DESC, shader_resource_view_desc);
	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, dest_descriptor);

	PYDX12_COM_CALL(CreateShaderResourceView, resource, shader_resource_view_desc, *dest_descriptor);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Device_CreateUnorderedAccessView(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_resource;
	PyObject* py_counter_resource;
	PyObject* py_unordered_access_view_desc;
	PyObject* py_dest_descriptor;
	if (!PyArg_ParseTuple(args, "OOOO", &py_resource, &py_counter_resource, &py_unordered_access_view_desc, &py_dest_descriptor))
		return NULL;

	PYDX12_ARG_CHECK_NONE(ID3D12Resource, resource);
	PYDX12_ARG_CHECK_NONE(ID3D12Resource, counter_resource);
	PYDX12_ARG_CHECK_NONE(D3D12_UNORDERED_ACCESS_VIEW_DESC, unordered_access_view_desc);
	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, dest_descriptor);

	PYDX12_COM_CALL(CreateUnorderedAccessView, resource, counter_resource, unordered_access_view_desc, *dest_descriptor);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Device_CreateConstantBufferView(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_constant_buffer_view_desc;
	PyObject* py_dest_descriptor;
	if (!PyArg_ParseTuple(args, "OO", &py_constant_buffer_view_desc, &py_dest_descriptor))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_CONSTANT_BUFFER_VIEW_DESC, constant_buffer_view_desc);
	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, dest_descriptor);

	PYDX12_COM_CALL(CreateConstantBufferView, constant_buffer_view_desc, *dest_descriptor);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Device_CreateDepthStencilView(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_resource;
	PyObject* py_depth_stencil_view_desc;
	PyObject* py_dest_descriptor;
	if (!PyArg_ParseTuple(args, "OOO", &py_resource, &py_depth_stencil_view_desc, &py_dest_descriptor))
		return NULL;

	PYDX12_ARG_CHECK_NONE(ID3D12Resource, resource);
	PYDX12_ARG_CHECK_NONE(D3D12_DEPTH_STENCIL_VIEW_DESC, depth_stencil_view_desc);
	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, dest_descriptor);

	PYDX12_COM_CALL(CreateDepthStencilView, resource, depth_stencil_view_desc, *dest_descriptor);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Device_CreateRenderTargetView(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_resource;
	PyObject* py_render_target_view_desc;
	PyObject* py_dest_descriptor;
	if (!PyArg_ParseTuple(args, "OOO", &py_resource, &py_render_target_view_desc, &py_dest_descriptor))
		return NULL;

	PYDX12_ARG_CHECK_NONE(ID3D12Resource, resource);
	PYDX12_ARG_CHECK_NONE(D3D12_RENDER_TARGET_VIEW_DESC, render_target_view_desc);
	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, dest_descriptor);

	PYDX12_COM_CALL(CreateRenderTargetView, resource, render_target_view_desc, *dest_descriptor);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12Device_CreateRootSignature(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	UINT node_mask;
	Py_buffer view;
	if (!PyArg_ParseTuple(args, "Iw*", &node_mask, &view))
		return NULL;

	ID3D12RootSignature* root_signature;
	HRESULT result = self->com_ptr->CreateRootSignature(node_mask, view.buf, view.len, __uuidof(ID3D12RootSignature), (void**)&root_signature);
	PyBuffer_Release(&view);
	if (result != S_OK)
	{
		return PyErr_Format(PyExc_Exception, "ID3D12Device::CreateRootSignature");
	}
	return pydx12_com_instantiate<ID3D12RootSignature>(root_signature, false);
}

static PyObject* pydx12_ID3D12Device_CreateGraphicsPipelineState(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_desc;
	if (!PyArg_ParseTuple(args, "O", &py_desc))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_GRAPHICS_PIPELINE_STATE_DESC, desc);

	ID3D12PipelineState* pipeline_state;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreateGraphicsPipelineState, desc, __uuidof(ID3D12PipelineState), (void**)&pipeline_state);

	return pydx12_com_instantiate<ID3D12PipelineState>(pipeline_state, false);
}

static PyObject* pydx12_ID3D12Device_GetNodeCount(pydx12_COM<ID3D12Device>* self)
{
	return PyLong_FromUnsignedLong(self->com_ptr->GetNodeCount());
}

static PyObject* pydx12_ID3D12Device_GetCopyableFootprints(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_resource_desc;
	UINT first_subresource;
	UINT num_subresources;
	UINT64 base_offset;
	if (!PyArg_ParseTuple(args, "OIIK", &py_resource_desc, &first_subresource, &num_subresources, &base_offset))
		return NULL;

	if (num_subresources < 1 || num_subresources >(D3D12_REQ_SUBRESOURCES - first_subresource))
		return PyErr_Format(PyExc_Exception, "invalid number of subresources: %u", num_subresources);

	PYDX12_ARG_CHECK(D3D12_RESOURCE_DESC, resource_desc);

	D3D12_PLACED_SUBRESOURCE_FOOTPRINT layouts;
	UINT* num_rows = (UINT*)PyMem_Malloc(sizeof(UINT) * num_subresources);
	if (!num_rows)
		return PyErr_NoMemory();

	UINT64* row_size_in_bytes = (UINT64*)PyMem_Malloc(sizeof(UINT64) * num_subresources);
	if (!row_size_in_bytes)
	{
		PyMem_Free(num_rows);
		return PyErr_NoMemory();
	}

	UINT64 total_bytes;

	PYDX12_COM_CALL(GetCopyableFootprints, resource_desc, first_subresource, num_subresources, base_offset, &layouts, num_rows, row_size_in_bytes, &total_bytes);

	PyObject* py_num_rows = PyTuple_New(num_subresources);
	PyObject* py_row_size_in_bytes = PyTuple_New(num_subresources);
	for (UINT i = 0; i < num_subresources; i++)
	{
		PyTuple_SetItem(py_num_rows, i, PyLong_FromUnsignedLong(num_rows[i]));
		PyTuple_SetItem(py_row_size_in_bytes, i, PyLong_FromUnsignedLongLong(row_size_in_bytes[i]));
	}
	PyObject* py_ret = Py_BuildValue("(NNNK)", pydx12_instantiate<D3D12_PLACED_SUBRESOURCE_FOOTPRINT>(&layouts, NULL, NULL), py_num_rows, py_row_size_in_bytes, total_bytes);
	PyMem_Free(num_rows);
	PyMem_Free(row_size_in_bytes);
	return py_ret;
}

static PyObject* pydx12_ID3D12Device_CreateComputePipelineState(pydx12_COM<ID3D12Device>* self, PyObject* args)
{
	PyObject* py_desc;
	if (!PyArg_ParseTuple(args, "O", &py_desc))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_COMPUTE_PIPELINE_STATE_DESC, desc);

	ID3D12PipelineState* pipeline_state;
	PYDX12_COM_CALL_HRESULT(ID3D12Device, CreateComputePipelineState, desc, __uuidof(ID3D12PipelineState), (void**)&pipeline_state);

	return pydx12_com_instantiate<ID3D12PipelineState>(pipeline_state, false);
}

PYDX12_METHODS(ID3D12Device) = {
	{"CreateCommittedResource", (PyCFunction)pydx12_ID3D12Device_CreateCommittedResource, METH_VARARGS, "Creates both a resource and an implicit heap, such that the heap is big enough to contain the entire resource, and the resource is mapped to the heap"},
	{"CreatePlacedResource", (PyCFunction)pydx12_ID3D12Device_CreatePlacedResource, METH_VARARGS, "Creates a resource that is placed in a specific heap"},
	{"GetAdapterLuid", (PyCFunction)pydx12_ID3D12Device_GetAdapterLuid, METH_NOARGS, "Gets a locally unique identifier for the current device (adapter)"},
	{"CreateCommandQueue", (PyCFunction)pydx12_ID3D12Device_CreateCommandQueue, METH_VARARGS, "Creates a command queue"},
	{"CreateCommandAllocator", (PyCFunction)pydx12_ID3D12Device_CreateCommandAllocator, METH_VARARGS, "Creates a command allocator object"},
	{"CreateCommandList", (PyCFunction)pydx12_ID3D12Device_CreateCommandList, METH_VARARGS, "Creates a command list"},
	{"CreateFence", (PyCFunction)pydx12_ID3D12Device_CreateFence, METH_VARARGS, "Creates a fence object"},
	{"CreateDescriptorHeap", (PyCFunction)pydx12_ID3D12Device_CreateDescriptorHeap, METH_VARARGS, "Creates a descriptor heap object"},
	{"CreateRenderTargetView", (PyCFunction)pydx12_ID3D12Device_CreateRenderTargetView, METH_VARARGS, "Creates a render-target view for accessing resource data"},
	{"CreateDepthStencilView", (PyCFunction)pydx12_ID3D12Device_CreateDepthStencilView, METH_VARARGS, "Creates a depth-stencil view for accessing resource data"},
	{"CreateUnorderedAccessView", (PyCFunction)pydx12_ID3D12Device_CreateUnorderedAccessView, METH_VARARGS, "Creates a view for unordered accessing"},
	{"CreateShaderResourceView", (PyCFunction)pydx12_ID3D12Device_CreateShaderResourceView, METH_VARARGS, "Creates a shader-resource view for accessing data in a resource"},
	{"CreateConstantBufferView", (PyCFunction)pydx12_ID3D12Device_CreateConstantBufferView, METH_VARARGS, "Creates a constant-buffer view for accessing resource data"},
	{"CreateRootSignature", (PyCFunction)pydx12_ID3D12Device_CreateRootSignature, METH_VARARGS, "Creates a root signature layout"},
	{"CreateGraphicsPipelineState", (PyCFunction)pydx12_ID3D12Device_CreateGraphicsPipelineState, METH_VARARGS, "Creates a graphics pipeline state object"},
	{"GetNodeCount", (PyCFunction)pydx12_ID3D12Device_GetNodeCount, METH_NOARGS, "Reports the number of physical adapters (nodes) that are associated with this device"},
	{"GetCopyableFootprints", (PyCFunction)pydx12_ID3D12Device_GetCopyableFootprints, METH_VARARGS, "Gets a resource layout that can be copied"},
	{"CreateComputePipelineState", (PyCFunction)pydx12_ID3D12Device_CreateComputePipelineState, METH_VARARGS, "Creates a compute pipeline state object"},
	{"CreateHeap", (PyCFunction)pydx12_ID3D12Device_CreateHeap, METH_VARARGS, "Creates a heap that can be used with placed resources and reserved resources"},
	{NULL}  /* Sentinel */
};

static PyObject* pydx12_ID3D12Device5_CreateStateObject(pydx12_COM<ID3D12Device5>* self, PyObject* args)
{
	PyObject* py_desc;
	if (!PyArg_ParseTuple(args, "O", &py_desc))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_STATE_OBJECT_DESC, desc);

	printf("DESC = %p %d %d\n", desc->pSubobjects[0].pDesc, desc->Type, desc->pSubobjects[0].Type);

	ID3D12StateObject* state_object;

	self->com_ptr->CreateStateObject(desc, __uuidof(ID3D12StateObject), (void**)&state_object);

	printf("CALLED!\n");

	PYDX12_COM_CALL_HRESULT(ID3D12Device5, CreateStateObject, desc, __uuidof(ID3D12StateObject), (void**)&state_object);

	printf("CALLED CreateStateObject %p\n", state_object);

	return pydx12_com_instantiate<ID3D12StateObject>(state_object, false);
}

PYDX12_METHODS(ID3D12Device5) = {
	{"CreateStateObject", (PyCFunction)pydx12_ID3D12Device5_CreateStateObject, METH_VARARGS, "Creates an ID3D12StateObject"},
	{NULL}  /* Sentinel */
};


static PyObject* pydx12_ID3D12InfoQueue_GetNumStoredMessages(pydx12_COM<ID3D12InfoQueue>* self, PyObject* args)
{
	return PyLong_FromUnsignedLongLong(self->com_ptr->GetNumStoredMessages());
}

static PyObject* pydx12_ID3D12InfoQueue_GetMessage(pydx12_COM<ID3D12InfoQueue>* self, PyObject* args)
{
	UINT64 message_index;
	if (!PyArg_ParseTuple(args, "K", &message_index))
		return NULL;

	if (message_index >= self->com_ptr->GetNumStoredMessages())
	{
		return PyErr_Format(PyExc_IndexError, "Invalid ID3D12InfoQueue message index");
	}

	SIZE_T message_len = 0;
	self->com_ptr->GetMessage(message_index, NULL, &message_len);
	if (message_len < sizeof(D3D12_MESSAGE))
	{
		return PyErr_Format(PyExc_MemoryError, "unable to allocate D3D12_MESSAGE");
	}

	PyObject* py_message = pydx12_instantiate_with_size<D3D12_MESSAGE>(NULL, NULL, NULL, message_len);
	if (!py_message)
	{
		return PyErr_Format(PyExc_MemoryError, "unable to allocate D3D12_MESSAGE");
	}

	D3D12_MESSAGE* message = pydx12_structure_get_data<D3D12_MESSAGE>(py_message);

	if (self->com_ptr->GetMessage(message_index, message, &message_len) != S_OK)
	{
		Py_DECREF(py_message);
		return PyErr_Format(PyExc_ValueError, "ID3D12InfoQueue::GetMessage() failed");
	}

	return py_message;
}

static PyObject* pydx12_ID3D12InfoQueue_ClearStoredMessages(pydx12_COM<ID3D12InfoQueue>* self, PyObject* args)
{
	self->com_ptr->ClearStoredMessages();
	Py_RETURN_NONE;
}

PYDX12_METHODS(ID3D12InfoQueue) = {
	{"GetNumStoredMessages", (PyCFunction)pydx12_ID3D12InfoQueue_GetNumStoredMessages, METH_NOARGS, "Get the number of messages currently stored in the message queue"},
	{"GetMessage", (PyCFunction)pydx12_ID3D12InfoQueue_GetMessage, METH_VARARGS, "Get a message from the message queue"},
	{"ClearStoredMessages", (PyCFunction)pydx12_ID3D12InfoQueue_ClearStoredMessages, METH_NOARGS, "Clear all messages from the message queue"},
	{NULL}  /* Sentinel */
};

int pydx12_init_device(PyObject* m)
{
	pydx12_ID3D12Device_Type.tp_methods = pydx12_ID3D12Device_methods;
	PYDX12_REGISTER_COM(ID3D12Device, ID3D12Object);
	PYDX12_REGISTER_COM(ID3D12Device1, ID3D12Device);
	PYDX12_REGISTER_COM(ID3D12Device2, ID3D12Device1);
	PYDX12_REGISTER_COM(ID3D12Device3, ID3D12Device2);
	PYDX12_REGISTER_COM(ID3D12Device4, ID3D12Device3);

	pydx12_ID3D12Device5_Type.tp_methods = pydx12_ID3D12Device5_methods;
	PYDX12_REGISTER_COM(ID3D12Device5, ID3D12Device4);
	PYDX12_REGISTER_COM(ID3D12Device6, ID3D12Device5);
	PYDX12_REGISTER_COM(ID3D12Device7, ID3D12Device6);
	PYDX12_REGISTER_COM(ID3D12Device8, ID3D12Device7);


	PYDX12_REGISTER_COM(ID3D12DeviceChild, ID3D12Object);
	PYDX12_REGISTER_COM(ID3D12Pageable, ID3D12DeviceChild);

	pydx12_ID3D12InfoQueue_Type.tp_methods = pydx12_ID3D12InfoQueue_methods;
	PYDX12_REGISTER_COM(ID3D12InfoQueue, IUnknown);

	PYDX12_REGISTER_COM(ID3D12Heap, ID3D12Pageable);

	PYDX12_REGISTER_STRUCT(D3D12_DEPTH_STENCIL_VALUE);

	PYDX12_ENUM(D3D_FEATURE_LEVEL_12_0);
	PYDX12_ENUM(D3D_FEATURE_LEVEL_12_1);

	PYDX12_ENUM(D3D12_HEAP_FLAG_NONE);
	PYDX12_ENUM(D3D12_HEAP_FLAG_SHARED);
	PYDX12_ENUM(D3D12_HEAP_FLAG_DENY_BUFFERS);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_DISPLAY);
	PYDX12_ENUM(D3D12_HEAP_FLAG_SHARED_CROSS_ADAPTER);
	PYDX12_ENUM(D3D12_HEAP_FLAG_DENY_RT_DS_TEXTURES);
	PYDX12_ENUM(D3D12_HEAP_FLAG_DENY_NON_RT_DS_TEXTURES);
	PYDX12_ENUM(D3D12_HEAP_FLAG_HARDWARE_PROTECTED);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_WRITE_WATCH);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_SHADER_ATOMICS);
	PYDX12_ENUM(D3D12_HEAP_FLAG_CREATE_NOT_RESIDENT);
	PYDX12_ENUM(D3D12_HEAP_FLAG_CREATE_NOT_ZEROED);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_ALL_BUFFERS_AND_TEXTURES);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_ONLY_BUFFERS);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_ONLY_NON_RT_DS_TEXTURES);
	PYDX12_ENUM(D3D12_HEAP_FLAG_ALLOW_ONLY_RT_DS_TEXTURES);

	PYDX12_ENUM(D3D12_RESOURCE_STATE_COMMON);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_INDEX_BUFFER);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_RENDER_TARGET);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_DEPTH_WRITE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_DEPTH_READ);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_STREAM_OUT);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_COPY_DEST);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_COPY_SOURCE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_RESOLVE_DEST);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_RESOLVE_SOURCE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_RAYTRACING_ACCELERATION_STRUCTURE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_SHADING_RATE_SOURCE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_GENERIC_READ);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_PRESENT);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_PREDICATION);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VIDEO_DECODE_READ);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VIDEO_DECODE_WRITE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VIDEO_PROCESS_READ);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VIDEO_PROCESS_WRITE);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VIDEO_ENCODE_READ);
	PYDX12_ENUM(D3D12_RESOURCE_STATE_VIDEO_ENCODE_WRITE);

	return 0;
}