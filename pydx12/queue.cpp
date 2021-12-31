#include "pydx12.h"

PYDX12_IMPORT(D3D12_TEXTURE_COPY_LOCATION);
PYDX12_IMPORT(D3D12_RESOURCE_BARRIER);
PYDX12_IMPORT(D3D12_CPU_DESCRIPTOR_HANDLE);
PYDX12_IMPORT(D3D12_VERTEX_BUFFER_VIEW);
PYDX12_IMPORT(D3D12_VIEWPORT);
PYDX12_IMPORT(D3D12_RECT);

PYDX12_IMPORT_COM(ID3D12Resource);
PYDX12_IMPORT_COM(ID3D12Pageable);
PYDX12_IMPORT_COM(ID3D12DeviceChild);
PYDX12_IMPORT_COM(ID3D12Fence);
PYDX12_IMPORT_COM(ID3D12PipelineState);
PYDX12_IMPORT_COM(ID3D12RootSignature);

PYDX12_TYPE(D3D12_COMMAND_QUEUE_DESC);
PYDX12_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, Type, LongLong, D3D12_COMMAND_LIST_TYPE);
PYDX12_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, Priority, Long, INT);
PYDX12_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, Flags, LongLong, D3D12_COMMAND_QUEUE_FLAGS);
PYDX12_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, NodeMask, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_COMMAND_QUEUE_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, Type),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, Priority),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, Flags),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMMAND_QUEUE_DESC, NodeMask),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_BOX);
PYDX12_GETTER_SETTER(D3D12_BOX, left, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_BOX, top, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_BOX, front, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_BOX, right, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_BOX, bottom, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_BOX, back, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_BOX) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BOX, left),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BOX, top),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BOX, front),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BOX, right),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BOX, bottom),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BOX, back),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_RECT);
PYDX12_GETTER_SETTER(D3D12_RECT, left, Long, LONG);
PYDX12_GETTER_SETTER(D3D12_RECT, top, Long, LONG);
PYDX12_GETTER_SETTER(D3D12_RECT, right, Long, LONG);
PYDX12_GETTER_SETTER(D3D12_RECT, bottom, Long, LONG);
PYDX12_GETSETTERS(D3D12_RECT) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RECT, left),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RECT, top),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RECT, right),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RECT, bottom),
	{ NULL }  /* Sentinel */
};



PYDX12_TYPE_COM(ID3D12CommandQueue);
PYDX12_TYPE_COM(ID3D12CommandAllocator);
PYDX12_TYPE_COM(ID3D12CommandList);
PYDX12_TYPE_COM(ID3D12GraphicsCommandList);

static PyObject* pydx12_ID3D12GraphicsCommandList_Reset(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_command_allocator;
	PyObject* py_initial_state = NULL;
	if (!PyArg_ParseTuple(args, "O|O", &py_command_allocator, &py_initial_state))
		return NULL;

	PYDX12_ARG_CHECK(ID3D12CommandAllocator, command_allocator);
	PYDX12_ARG_CHECK_NONE(ID3D12PipelineState, initial_state);

	PYDX12_COM_CALL_HRESULT(ID3D12GraphicsCommandList, Reset, command_allocator, initial_state);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_Dispatch(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT ThreadGroupCountX;
	UINT ThreadGroupCountY;
	UINT ThreadGroupCountZ;
	if (!PyArg_ParseTuple(args, "III", &ThreadGroupCountX, &ThreadGroupCountY, &ThreadGroupCountZ))
		return NULL;

	self->com_ptr->Dispatch(ThreadGroupCountX, ThreadGroupCountY, ThreadGroupCountZ);
	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_Close(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	if (self->com_ptr->Close() != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to Close ID3D12GraphicsCommandList");
	}

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_CopyResource(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_dst_resource;
	PyObject* py_src_resource;
	if (!PyArg_ParseTuple(args, "OO", &py_dst_resource, &py_src_resource))
		return NULL;

	ID3D12Resource* dst_resource = pydx12_ID3D12Resource_check(py_dst_resource);
	if (!dst_resource)
		return PyErr_Format(PyExc_TypeError, "first argument must be a ID3D12Resource");

	ID3D12Resource* src_resource = pydx12_ID3D12Resource_check(py_src_resource);
	if (!src_resource)
		return PyErr_Format(PyExc_TypeError, "second argument must be a ID3D12Resource");

	self->com_ptr->CopyResource(src_resource, dst_resource);
	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_CopyTextureRegion(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_dst;
	UINT dst_x;
	UINT dst_y;
	UINT dst_z;
	PyObject* py_src;
	PyObject* py_src_box = NULL;
	if (!PyArg_ParseTuple(args, "OIIIO|O", &py_dst, &dst_x, &dst_y, &dst_z, &py_src, &py_src_box))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_TEXTURE_COPY_LOCATION, dst);
	PYDX12_ARG_CHECK(D3D12_TEXTURE_COPY_LOCATION, src);
	PYDX12_ARG_CHECK_NONE(D3D12_BOX, src_box);

	PYDX12_COM_CALL(CopyTextureRegion, dst, dst_x, dst_y, dst_z, src, src_box);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_ResourceBarrier(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_list_resource_barriers;
	if (!PyArg_ParseTuple(args, "O", &py_list_resource_barriers))
		return NULL;

	PyObject* py_iter = PyObject_GetIter(py_list_resource_barriers);
	if (!py_iter)
	{
		return NULL;
	}

	D3D12_RESOURCE_BARRIER* resource_barriers = NULL;
	UINT resource_barriers_counter = 0;

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		D3D12_RESOURCE_BARRIER* resource_barrier = pydx12_D3D12_RESOURCE_BARRIER_check(py_item);
		if (!resource_barrier)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (resource_barriers)
				PyMem_Free(resource_barriers);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of D3D12_RESOURCE_BARRIER");
		}
		resource_barriers_counter++;
		D3D12_RESOURCE_BARRIER* new_resource_barriers = (D3D12_RESOURCE_BARRIER*)PyMem_Realloc(resource_barriers, sizeof(D3D12_RESOURCE_BARRIER) * resource_barriers_counter);
		if (!new_resource_barriers)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (resource_barriers)
				PyMem_Free(resource_barriers);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_RESOURCE_BARRIER's array");
		}
		resource_barriers = new_resource_barriers;
		resource_barriers[resource_barriers_counter - 1] = *resource_barrier;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	self->com_ptr->ResourceBarrier(resource_barriers_counter, resource_barriers);

	if (resource_barriers)
		PyMem_Free(resource_barriers);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_ClearRenderTargetView(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_render_target_view;
	FLOAT color_rgba[4];
	PyObject* py_rects = NULL;
	if (!PyArg_ParseTuple(args, "O(ffff)|O", &py_render_target_view, &color_rgba[0], &color_rgba[1], &color_rgba[2], &color_rgba[3], &py_rects))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, render_target_view);

	D3D12_RECT* rects = NULL;
	UINT rects_counter = 0;

	if (py_rects && py_rects != Py_None)
	{
		PyObject* py_iter = PyObject_GetIter(py_rects);
		if (!py_iter)
		{
			return NULL;
		}

		while (PyObject* py_item = PyIter_Next(py_iter))
		{
			D3D12_RECT* rect = pydx12_D3D12_RECT_check(py_item);
			if (!rect)
			{
				Py_DECREF(py_item);
				Py_DECREF(py_iter);
				if (rects)
					PyMem_Free(rects);
				return PyErr_Format(PyExc_TypeError, "argument must be an iterable of D3D12_RECT");
			}
			rects_counter++;
			D3D12_RECT* new_rects = (D3D12_RECT*)PyMem_Realloc(rects, sizeof(D3D12_RECT) * rects_counter);
			if (!new_rects)
			{
				Py_DECREF(py_item);
				Py_DECREF(py_iter);
				if (rects)
					PyMem_Free(rects);
				return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_RECT's array");
			}
			rects = new_rects;
			rects[rects_counter - 1] = *rect;
			Py_DECREF(py_item);
		}
		Py_DECREF(py_iter);
	}

	PYDX12_COM_CALL(ClearRenderTargetView, *render_target_view, color_rgba, rects_counter, rects);

	if (rects)
		PyMem_Free(rects);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_DrawInstanced(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT vertex_count_per_instance;
	UINT instance_count;
	UINT start_vertex_location;
	UINT start_instance_location;
	if (!PyArg_ParseTuple(args, "IIII", &vertex_count_per_instance, &instance_count, &start_vertex_location, &start_instance_location))
		return NULL;

	PYDX12_COM_CALL(DrawInstanced, vertex_count_per_instance, instance_count, start_vertex_location, start_instance_location);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_IASetPrimitiveTopology(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	D3D12_PRIMITIVE_TOPOLOGY primitive_topology;
	if (!PyArg_ParseTuple(args, "L", &primitive_topology))
		return NULL;

	PYDX12_COM_CALL(IASetPrimitiveTopology, primitive_topology);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetGraphicsRootSignature(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_root_signature;
	if (!PyArg_ParseTuple(args, "O", &py_root_signature))
		return NULL;

	PYDX12_ARG_CHECK(ID3D12RootSignature, root_signature);
	PYDX12_COM_CALL(SetGraphicsRootSignature, root_signature);

	Py_RETURN_NONE;
}


static PyObject* pydx12_ID3D12GraphicsCommandList_IASetVertexBuffers(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT start_slot;
	PyObject* py_views;
	if (!PyArg_ParseTuple(args, "IO", &start_slot, &py_views))
		return NULL;

	D3D12_VERTEX_BUFFER_VIEW* views = NULL;
	UINT views_counter = 0;

	PyObject* py_iter = PyObject_GetIter(py_views);
	if (!py_iter)
	{
		return NULL;
	}

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		D3D12_VERTEX_BUFFER_VIEW* view = pydx12_D3D12_VERTEX_BUFFER_VIEW_check(py_item);
		if (!view)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (views)
				PyMem_Free(views);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of D3D12_VERTEX_BUFFER_VIEW");
		}
		views_counter++;
		D3D12_VERTEX_BUFFER_VIEW* new_views = (D3D12_VERTEX_BUFFER_VIEW*)PyMem_Realloc(views, sizeof(D3D12_VERTEX_BUFFER_VIEW) * views_counter);
		if (!new_views)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (views)
				PyMem_Free(views);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_VERTEX_BUFFER_VIEW's array");
		}
		views = new_views;
		views[views_counter - 1] = *view;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	PYDX12_COM_CALL(IASetVertexBuffers, start_slot, views_counter, views);

	if (views)
		PyMem_Free(views);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_OMSetRenderTargets(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_render_target_descriptors;
	PyObject* py_depth_stencil_descriptor = NULL;
	if (!PyArg_ParseTuple(args, "O|O", &py_render_target_descriptors, &py_depth_stencil_descriptor))
		return NULL;

	PYDX12_ARG_CHECK_NONE(D3D12_CPU_DESCRIPTOR_HANDLE, depth_stencil_descriptor);

	D3D12_CPU_DESCRIPTOR_HANDLE* descriptors = NULL;
	UINT descriptors_counter = 0;

	PyObject* py_iter = PyObject_GetIter(py_render_target_descriptors);
	if (!py_iter)
	{
		return NULL;
	}

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		D3D12_CPU_DESCRIPTOR_HANDLE* descriptor = pydx12_D3D12_CPU_DESCRIPTOR_HANDLE_check(py_item);
		if (!descriptor)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (descriptors)
				PyMem_Free(descriptors);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of D3D12_CPU_DESCRIPTOR_HANDLE");
		}
		descriptors_counter++;
		D3D12_CPU_DESCRIPTOR_HANDLE* new_descriptors = (D3D12_CPU_DESCRIPTOR_HANDLE*)PyMem_Realloc(descriptors, sizeof(D3D12_CPU_DESCRIPTOR_HANDLE) * descriptors_counter);
		if (!new_descriptors)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (descriptors)
				PyMem_Free(descriptors);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_CPU_DESCRIPTOR_HANDLE's array");
		}
		descriptors = new_descriptors;
		descriptors[descriptors_counter - 1] = *descriptor;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	PYDX12_COM_CALL(OMSetRenderTargets, descriptors_counter, descriptors, FALSE, depth_stencil_descriptor);

	if (descriptors)
		PyMem_Free(descriptors);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_RSSetViewports(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_list_viewports;
	if (!PyArg_ParseTuple(args, "O", &py_list_viewports))
		return NULL;

	PyObject* py_iter = PyObject_GetIter(py_list_viewports);
	if (!py_iter)
	{
		return NULL;
	}

	D3D12_VIEWPORT* viewports = NULL;
	UINT viewports_counter = 0;

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		D3D12_VIEWPORT* viewport = pydx12_D3D12_VIEWPORT_check(py_item);
		if (!viewport)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (viewports)
				PyMem_Free(viewports);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of D3D12_VIEWPORT");
		}
		viewports_counter++;
		D3D12_VIEWPORT* new_viewports = (D3D12_VIEWPORT*)PyMem_Realloc(viewports, sizeof(D3D12_VIEWPORT) * viewports_counter);
		if (!new_viewports)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (viewports)
				PyMem_Free(viewports);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_VIEWPORT's array");
		}
		viewports = new_viewports;
		viewports[viewports_counter - 1] = *viewport;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	self->com_ptr->RSSetViewports(viewports_counter, viewports);

	if (viewports)
		PyMem_Free(viewports);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_RSSetScissorRects(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_rects;
	if (!PyArg_ParseTuple(args, "O", &py_rects))
		return NULL;

	PyObject* py_iter = PyObject_GetIter(py_rects);
	if (!py_iter)
	{
		return NULL;
	}

	D3D12_RECT* rects = NULL;
	UINT rects_counter = 0;

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		D3D12_RECT* rect = pydx12_D3D12_RECT_check(py_item);
		if (!rect)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (rects)
				PyMem_Free(rects);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of D3D12_RECT");
		}
		rects_counter++;
		D3D12_RECT* new_rects = (D3D12_RECT*)PyMem_Realloc(rects, sizeof(D3D12_RECT) * rects_counter);
		if (!new_rects)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (rects)
				PyMem_Free(rects);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_RECT's array");
		}
		rects = new_rects;
		rects[rects_counter - 1] = *rect;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	self->com_ptr->RSSetScissorRects(rects_counter, rects);

	if (rects)
		PyMem_Free(rects);

	Py_RETURN_NONE;
}



PYDX12_METHODS(ID3D12GraphicsCommandList) = {
	{"Close", (PyCFunction)pydx12_ID3D12GraphicsCommandList_Close, METH_NOARGS, "Indicates that recording to the command list has finished"},
	{"Dispatch", (PyCFunction)pydx12_ID3D12GraphicsCommandList_Dispatch, METH_NOARGS, "Executes a command list from a thread group"},
	{"Reset", (PyCFunction)pydx12_ID3D12GraphicsCommandList_Reset, METH_VARARGS, "Resets a command list back to its initial state as if a new command list was just created"},
	{"CopyResource", (PyCFunction)pydx12_ID3D12GraphicsCommandList_CopyResource, METH_VARARGS, "Copies the entire contents of the source resource to the destination resource"},
	{"CopyTextureRegion", (PyCFunction)pydx12_ID3D12GraphicsCommandList_CopyTextureRegion, METH_VARARGS, "This method uses the GPU to copy texture data between two locations"},
	{"ResourceBarrier", (PyCFunction)pydx12_ID3D12GraphicsCommandList_ResourceBarrier, METH_VARARGS, "Notifies the driver that it needs to synchronize multiple accesses to resources"},
	{"ClearRenderTargetView", (PyCFunction)pydx12_ID3D12GraphicsCommandList_ClearRenderTargetView, METH_VARARGS, "Sets all the elements in a render target to one value"},
	{"DrawInstanced", (PyCFunction)pydx12_ID3D12GraphicsCommandList_DrawInstanced, METH_VARARGS, "Draws non-indexed, instanced primitives"},
	{"IASetPrimitiveTopology", (PyCFunction)pydx12_ID3D12GraphicsCommandList_IASetPrimitiveTopology, METH_VARARGS, "Bind information about the primitive type, and data order that describes input data for the input assembler stage"},
	{"SetGraphicsRootSignature", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetGraphicsRootSignature, METH_VARARGS, "Sets the layout of the graphics root signature"},
	{"IASetVertexBuffers", (PyCFunction)pydx12_ID3D12GraphicsCommandList_IASetVertexBuffers, METH_VARARGS, "Sets a CPU descriptor handle for the vertex buffers"},
	{"OMSetRenderTargets", (PyCFunction)pydx12_ID3D12GraphicsCommandList_OMSetRenderTargets, METH_VARARGS, "Sets CPU descriptor handles for the render targets and depth stencil"},
	{"RSSetViewports", (PyCFunction)pydx12_ID3D12GraphicsCommandList_RSSetViewports, METH_VARARGS, "Bind an array of viewports to the rasterizer stage of the pipeline"},
	{"RSSetScissorRects", (PyCFunction)pydx12_ID3D12GraphicsCommandList_RSSetScissorRects, METH_VARARGS, "Binds an array of scissor rectangles to the rasterizer stage"},
	{NULL}  /* Sentinel */
};

static PyObject* pydx12_ID3D12CommandQueue_ExecuteCommandLists(pydx12_ID3D12CommandQueue* self, PyObject* args)
{
	PyObject* py_list_command_lists;
	if (!PyArg_ParseTuple(args, "O", &py_list_command_lists))
		return NULL;

	PyObject* py_iter = PyObject_GetIter(py_list_command_lists);
	if (!py_iter)
	{
		return NULL;
	}

	ID3D12CommandList** command_lists = NULL;
	UINT command_lists_counter = 0;

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		ID3D12GraphicsCommandList* command_list = pydx12_ID3D12GraphicsCommandList_check(py_item);
		if (!command_list)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (command_lists)
				PyMem_Free(command_lists);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of ID3D12GraphicsCommandList");
		}
		command_lists_counter++;
		ID3D12CommandList** new_command_lists = (ID3D12CommandList**)PyMem_Realloc(command_lists, sizeof(ID3D12CommandList*) * command_lists_counter);
		if (!new_command_lists)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (command_lists)
				PyMem_Free(command_lists);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for ID3D12GraphicsCommandList's array");
		}
		command_lists = new_command_lists;
		command_lists[command_lists_counter - 1] = command_list;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	self->com_ptr->ExecuteCommandLists(command_lists_counter, command_lists);

	if (command_lists)
		PyMem_Free(command_lists);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12CommandQueue_Signal(pydx12_ID3D12CommandQueue* self, PyObject* args)
{
	PyObject* py_fence;
	UINT64 value;
	if (!PyArg_ParseTuple(args, "OK", &py_fence, &value))
		return NULL;

	PYDX12_ARG_CHECK(ID3D12Fence, fence);

	PYDX12_COM_CALL_HRESULT(ID3D12CommandQueue, Signal, fence, value);

	Py_RETURN_NONE;
}

PYDX12_METHODS(ID3D12CommandQueue) = {
	{"ExecuteCommandLists", (PyCFunction)pydx12_ID3D12CommandQueue_ExecuteCommandLists, METH_VARARGS, "Submits an array of command lists for execution"},
	{"Signal", (PyCFunction)pydx12_ID3D12CommandQueue_Signal, METH_VARARGS, "Updates a fence to a specified value"},
	{NULL}  /* Sentinel */
};

int pydx12_init_queue(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D12_COMMAND_QUEUE_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_BOX);
	PYDX12_REGISTER_STRUCT(D3D12_RECT);

	pydx12_ID3D12CommandQueueType.tp_methods = pydx12_ID3D12CommandQueue_methods;
	PYDX12_REGISTER_COM(ID3D12CommandQueue, ID3D12Pageable);

	PYDX12_REGISTER_COM(ID3D12CommandAllocator, ID3D12Pageable);
	PYDX12_REGISTER_COM(ID3D12CommandList, ID3D12DeviceChild);

	pydx12_ID3D12GraphicsCommandListType.tp_methods = pydx12_ID3D12GraphicsCommandList_methods;
	PYDX12_REGISTER_COM(ID3D12GraphicsCommandList, ID3D12CommandList);

	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_DIRECT);
	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_BUNDLE);
	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_COMPUTE);
	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_COPY);
	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_VIDEO_DECODE);
	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_VIDEO_PROCESS);
	PYDX12_ENUM(D3D12_COMMAND_LIST_TYPE_VIDEO_ENCODE);

	PYDX12_ENUM(D3D12_COMMAND_QUEUE_FLAG_NONE);
	PYDX12_ENUM(D3D12_COMMAND_QUEUE_FLAG_DISABLE_GPU_TIMEOUT);

	return 0;
}