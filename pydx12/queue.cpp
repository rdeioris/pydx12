#include "pydx12.h"

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

static PyObject* pydx12_ID3D12GraphicsCommandList_Reset(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
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

static PyObject* pydx12_ID3D12GraphicsCommandList_Dispatch(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
{
	UINT ThreadGroupCountX;
	UINT ThreadGroupCountY;
	UINT ThreadGroupCountZ;
	if (!PyArg_ParseTuple(args, "III", &ThreadGroupCountX, &ThreadGroupCountY, &ThreadGroupCountZ))
		return NULL;

	PYDX12_COM_CALL(Dispatch, ThreadGroupCountX, ThreadGroupCountY, ThreadGroupCountZ);
	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_Close(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
{
	if (self->com_ptr->Close() != S_OK)
	{
		return PyErr_Format(PyExc_ValueError, "unable to Close ID3D12GraphicsCommandList");
	}

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_CopyResource(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
{
	PyObject* py_dst_resource;
	PyObject* py_src_resource;
	if (!PyArg_ParseTuple(args, "OO", &py_dst_resource, &py_src_resource))
		return NULL;

	ID3D12Resource* dst_resource = pydx12_check<ID3D12Resource>(py_dst_resource);
	if (!dst_resource)
		return PyErr_Format(PyExc_TypeError, "first argument must be a ID3D12Resource");

	ID3D12Resource* src_resource = pydx12_check<ID3D12Resource>(py_src_resource);
	if (!src_resource)
		return PyErr_Format(PyExc_TypeError, "second argument must be a ID3D12Resource");

	self->com_ptr->CopyResource(dst_resource, src_resource);
	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_CopyTextureRegion(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
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

static PyObject* pydx12_ID3D12GraphicsCommandList_ResourceBarrier(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
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

	PYDX12_ARG_ITER_CHECK_NONE(D3D12_RECT, rects, false);

	PYDX12_COM_CALL(ClearRenderTargetView, *render_target_view, color_rgba, rects_counter, rects);

	if (rects)
		PyMem_Free(rects);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_ClearDepthStencilView(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_depth_stencil_view;
	D3D12_CLEAR_FLAGS clear_flags;
	FLOAT depth;
	UINT8 stencil;
	PyObject* py_rects = NULL;
	if (!PyArg_ParseTuple(args, "OLfB|O", &py_depth_stencil_view, &clear_flags, &depth, &stencil, &py_rects))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, depth_stencil_view);

	PYDX12_ARG_ITER_CHECK_NONE(D3D12_RECT, rects, false);

	PYDX12_COM_CALL(ClearDepthStencilView, *depth_stencil_view, clear_flags, depth, stencil, rects_counter, rects);

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

static PyObject* pydx12_ID3D12GraphicsCommandList_DrawIndexedInstanced(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT index_count_per_instance;
	UINT instance_count;
	UINT start_index_location;
	INT base_vertex_location;
	UINT start_instance_location;
	if (!PyArg_ParseTuple(args, "IIIiI", &index_count_per_instance, &instance_count, &start_index_location, &base_vertex_location, &start_instance_location))
		return NULL;

	PYDX12_COM_CALL(DrawIndexedInstanced, index_count_per_instance, instance_count, start_index_location, base_vertex_location, start_instance_location);

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

	PYDX12_ARG_CHECK_NONE(ID3D12RootSignature, root_signature);
	PYDX12_COM_CALL(SetGraphicsRootSignature, root_signature);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetComputeRootSignature(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_root_signature;
	if (!PyArg_ParseTuple(args, "O", &py_root_signature))
		return NULL;

	PYDX12_ARG_CHECK_NONE(ID3D12RootSignature, root_signature);
	PYDX12_COM_CALL(SetComputeRootSignature, root_signature);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_IASetVertexBuffers(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT start_slot;
	PyObject* py_views;
	if (!PyArg_ParseTuple(args, "IO", &start_slot, &py_views))
		return NULL;

	PYDX12_ARG_ITER_CHECK(D3D12_VERTEX_BUFFER_VIEW, views, false);

	PYDX12_COM_CALL(IASetVertexBuffers, start_slot, views_counter, views);

	if (views)
		PyMem_Free(views);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_IASetIndexBuffer(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_view;
	if (!PyArg_ParseTuple(args, "O", &py_view))
		return NULL;


	PYDX12_ARG_CHECK(D3D12_INDEX_BUFFER_VIEW, view);

	PYDX12_COM_CALL(IASetIndexBuffer, view);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_OMSetRenderTargets(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_render_target_descriptors;
	PyObject* py_depth_stencil_descriptor = NULL;
	if (!PyArg_ParseTuple(args, "O|O", &py_render_target_descriptors, &py_depth_stencil_descriptor))
		return NULL;

	PYDX12_ARG_ITER_CHECK(D3D12_CPU_DESCRIPTOR_HANDLE, render_target_descriptors, false);

	PYDX12_ARG_CHECK_NONE(D3D12_CPU_DESCRIPTOR_HANDLE, depth_stencil_descriptor);

	PYDX12_COM_CALL(OMSetRenderTargets, render_target_descriptors_counter, render_target_descriptors, FALSE, depth_stencil_descriptor);

	if (render_target_descriptors)
		PyMem_Free(render_target_descriptors);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_RSSetViewports(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_viewports;
	if (!PyArg_ParseTuple(args, "O", &py_viewports))
		return NULL;

	PYDX12_ARG_ITER_CHECK(D3D12_VIEWPORT, viewports, false);

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


	PYDX12_ARG_ITER_CHECK(D3D12_RECT, rects, false);

	self->com_ptr->RSSetScissorRects(rects_counter, rects);

	if (rects)
		PyMem_Free(rects);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetGraphicsRoot32BitConstant(pydx12_COM<ID3D12GraphicsCommandList>* self, PyObject* args)
{
	UINT root_parameter_index;
	PyObject* py_src_data;
	UINT dest_offset = 0;
	if (!PyArg_ParseTuple(args, "IO|I", &root_parameter_index, &py_src_data, &dest_offset))
		return NULL;

	UINT src_data = 0;
	if (PyLong_Check(py_src_data))
	{
		src_data = PyLong_AsUnsignedLong(py_src_data);
	}
	else if (PyFloat_Check(py_src_data))
	{
		float float_value = (float)PyFloat_AsDouble(py_src_data);
		UINT* float_as_uint_ptr = (UINT*)&float_value;
		src_data = *float_as_uint_ptr;
	}
	else if (PyObject_CheckBuffer(py_src_data))
	{
		Py_buffer view;
		if (PyObject_GetBuffer(py_src_data, &view, 0))
		{
			return NULL;
		}
		if (view.len < 4)
		{
			PyBuffer_Release(&view);
			return PyErr_Format(PyExc_ValueError, "expected a buffer of at least 4 bytes");
		}
		memcpy(&src_data, view.buf, 4);
		PyBuffer_Release(&view);
	}

	PYDX12_COM_CALL(SetGraphicsRoot32BitConstant, root_parameter_index, src_data, dest_offset);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetGraphicsRoot32BitConstants(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT root_parameter_index;
	PyObject* py_src_data;
	UINT dest_offset = 0;
	if (!PyArg_ParseTuple(args, "IO|I", &root_parameter_index, &py_src_data, &dest_offset))
		return NULL;

	if (PyObject_CheckBuffer(py_src_data))
	{
		Py_buffer view;
		if (PyObject_GetBuffer(py_src_data, &view, 0))
		{
			return NULL;
		}
		if (view.len % 4 != 0)
		{
			PyBuffer_Release(&view);
			return PyErr_Format(PyExc_ValueError, "expected a buffer size multiple of 4 bytes");
		}

		PYDX12_COM_CALL(SetGraphicsRoot32BitConstants, root_parameter_index, (UINT)(view.len / 4), view.buf, dest_offset);
		PyBuffer_Release(&view);
		Py_RETURN_NONE;
	}

	PyObject* py_iter = PyObject_GetIter(py_src_data);
	if (!py_iter)
	{
		return NULL;
	}
	Py_DECREF(py_iter);

	return PyErr_Format(PyExc_ValueError, "unsupported 32bit constant values");
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetComputeRootDescriptorTable(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT root_parameter_index;
	PyObject* py_base_descriptor;
	if (!PyArg_ParseTuple(args, "IO", &root_parameter_index, &py_base_descriptor))
		return NULL;

	PYDX12_ARG_CHECK(D3D12_GPU_DESCRIPTOR_HANDLE, base_descriptor);

	PYDX12_COM_CALL(SetComputeRootDescriptorTable, root_parameter_index, *base_descriptor);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT root_parameter_index;
	D3D12_GPU_VIRTUAL_ADDRESS py_buffer_location;
	if (!PyArg_ParseTuple(args, "IK", &root_parameter_index, &py_buffer_location))
		return NULL;

	PYDX12_COM_CALL(SetGraphicsRootConstantBufferView, root_parameter_index, py_buffer_location);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetGraphicsRootShaderResourceView(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	UINT root_parameter_index;
	D3D12_GPU_VIRTUAL_ADDRESS py_buffer_location;
	if (!PyArg_ParseTuple(args, "IK", &root_parameter_index, &py_buffer_location))
		return NULL;

	PYDX12_COM_CALL(SetGraphicsRootShaderResourceView, root_parameter_index, py_buffer_location);

	Py_RETURN_NONE;
}

static PyObject* pydx12_ID3D12GraphicsCommandList_SetDescriptorHeaps(pydx12_ID3D12GraphicsCommandList* self, PyObject* args)
{
	PyObject* py_descriptor_heaps;
	if (!PyArg_ParseTuple(args, "O", &py_descriptor_heaps))
		return NULL;

	PyObject* py_iter = PyObject_GetIter(py_descriptor_heaps);
	if (!py_iter)
	{
		return NULL;
	}

	ID3D12DescriptorHeap** descriptor_heaps = NULL;
	UINT descriptor_heaps_counter = 0;

	while (PyObject* py_item = PyIter_Next(py_iter))
	{
		ID3D12DescriptorHeap* descriptor_heap = pydx12_ID3D12DescriptorHeap_check(py_item);
		if (!descriptor_heap)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (descriptor_heaps)
				PyMem_Free(descriptor_heaps);
			return PyErr_Format(PyExc_TypeError, "argument must be an iterable of ID3D12DescriptorHeap");
		}
		descriptor_heaps_counter++;
		ID3D12DescriptorHeap** new_descriptor_heaps = (ID3D12DescriptorHeap**)PyMem_Realloc(descriptor_heaps, sizeof(ID3D12DescriptorHeap*) * descriptor_heaps_counter);
		if (!new_descriptor_heaps)
		{
			Py_DECREF(py_item);
			Py_DECREF(py_iter);
			if (descriptor_heaps)
				PyMem_Free(descriptor_heaps);
			return PyErr_Format(PyExc_TypeError, "unable to allocate memory for D3D12_RECT's array");
		}
		descriptor_heaps = new_descriptor_heaps;
		descriptor_heaps[descriptor_heaps_counter - 1] = descriptor_heap;
		Py_DECREF(py_item);
	}
	Py_DECREF(py_iter);

	self->com_ptr->SetDescriptorHeaps(descriptor_heaps_counter, descriptor_heaps);

	if (descriptor_heaps)
		PyMem_Free(descriptor_heaps);

	Py_RETURN_NONE;
}

PYDX12_METHODS(ID3D12GraphicsCommandList) = {
	{"Close", (PyCFunction)pydx12_ID3D12GraphicsCommandList_Close, METH_NOARGS, "Indicates that recording to the command list has finished"},
	{"Dispatch", (PyCFunction)pydx12_ID3D12GraphicsCommandList_Dispatch, METH_VARARGS, "Executes a command list from a thread group"},
	{"Reset", (PyCFunction)pydx12_ID3D12GraphicsCommandList_Reset, METH_VARARGS, "Resets a command list back to its initial state as if a new command list was just created"},
	{"CopyResource", (PyCFunction)pydx12_ID3D12GraphicsCommandList_CopyResource, METH_VARARGS, "Copies the entire contents of the source resource to the destination resource"},
	{"CopyTextureRegion", (PyCFunction)pydx12_ID3D12GraphicsCommandList_CopyTextureRegion, METH_VARARGS, "This method uses the GPU to copy texture data between two locations"},
	{"ResourceBarrier", (PyCFunction)pydx12_ID3D12GraphicsCommandList_ResourceBarrier, METH_VARARGS, "Notifies the driver that it needs to synchronize multiple accesses to resources"},
	{"ClearRenderTargetView", (PyCFunction)pydx12_ID3D12GraphicsCommandList_ClearRenderTargetView, METH_VARARGS, "Sets all the elements in a render target to one value"},
	{"ClearDepthStencilView", (PyCFunction)pydx12_ID3D12GraphicsCommandList_ClearDepthStencilView, METH_VARARGS, "Clears the depth-stencil resource"},
	{"DrawInstanced", (PyCFunction)pydx12_ID3D12GraphicsCommandList_DrawInstanced, METH_VARARGS, "Draws non-indexed, instanced primitives"},
	{"DrawIndexedInstanced", (PyCFunction)pydx12_ID3D12GraphicsCommandList_DrawIndexedInstanced, METH_VARARGS, "Draws indexed, instanced primitives"},
	{"IASetPrimitiveTopology", (PyCFunction)pydx12_ID3D12GraphicsCommandList_IASetPrimitiveTopology, METH_VARARGS, "Bind information about the primitive type, and data order that describes input data for the input assembler stage"},
	{"SetGraphicsRootSignature", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetGraphicsRootSignature, METH_VARARGS, "Sets the layout of the graphics root signature"},
	{"SetComputeRootSignature", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetComputeRootSignature, METH_VARARGS, "Sets the layout of the compute root signature"},
	{"IASetVertexBuffers", (PyCFunction)pydx12_ID3D12GraphicsCommandList_IASetVertexBuffers, METH_VARARGS, "Sets a CPU descriptor handle for the vertex buffers"},
	{"IASetIndexBuffer", (PyCFunction)pydx12_ID3D12GraphicsCommandList_IASetIndexBuffer, METH_VARARGS, "Sets the view for the index buffer"},
	{"OMSetRenderTargets", (PyCFunction)pydx12_ID3D12GraphicsCommandList_OMSetRenderTargets, METH_VARARGS, "Sets CPU descriptor handles for the render targets and depth stencil"},
	{"RSSetViewports", (PyCFunction)pydx12_ID3D12GraphicsCommandList_RSSetViewports, METH_VARARGS, "Bind an array of viewports to the rasterizer stage of the pipeline"},
	{"RSSetScissorRects", (PyCFunction)pydx12_ID3D12GraphicsCommandList_RSSetScissorRects, METH_VARARGS, "Binds an array of scissor rectangles to the rasterizer stage"},
	{"SetGraphicsRoot32BitConstant", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetGraphicsRoot32BitConstant, METH_VARARGS, "Sets a constant in the graphics root signature"},
	{"SetGraphicsRoot32BitConstants", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetGraphicsRoot32BitConstants, METH_VARARGS, "Sets a group of constants in the graphics root signature"},
	{"SetComputeRootDescriptorTable", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetComputeRootDescriptorTable, METH_VARARGS, "Sets a descriptor table into the compute root signature"},
	{"SetGraphicsRootConstantBufferView", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetGraphicsRootConstantBufferView, METH_VARARGS, "Sets a CPU descriptor handle for the constant buffer in the graphics root signature"},
	{"SetGraphicsRootShaderResourceView", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetGraphicsRootShaderResourceView, METH_VARARGS, "Sets a CPU descriptor handle for the shader resource in the graphics root signature"},
	{"SetDescriptorHeaps", (PyCFunction)pydx12_ID3D12GraphicsCommandList_SetDescriptorHeaps, METH_VARARGS, "Changes the currently bound descriptor heaps that are associated with a command list"},
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
		ID3D12GraphicsCommandList* command_list = pydx12_check<ID3D12GraphicsCommandList>(py_item);
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

static PyObject* pydx12_ID3D12CommandQueue_GetClockCalibration(pydx12_ID3D12CommandQueue* self)
{
	UINT64 gpu_timestamp;
	UINT64 cpu_timestamp;
	PYDX12_COM_CALL_HRESULT(ID3D12CommandQueue, GetClockCalibration, &gpu_timestamp, &cpu_timestamp);
	return Py_BuildValue("(KK)", gpu_timestamp, cpu_timestamp);
}

static PyObject* pydx12_ID3D12CommandQueue_GetTimestampFrequency(pydx12_ID3D12CommandQueue* self)
{
	UINT64 frequency;
	PYDX12_COM_CALL_HRESULT(ID3D12CommandQueue, GetTimestampFrequency, &frequency);
	return PyLong_FromUnsignedLongLong(frequency);
}

PYDX12_METHODS(ID3D12CommandQueue) = {
	{"ExecuteCommandLists", (PyCFunction)pydx12_ID3D12CommandQueue_ExecuteCommandLists, METH_VARARGS, "Submits an array of command lists for execution"},
	{"Signal", (PyCFunction)pydx12_ID3D12CommandQueue_Signal, METH_VARARGS, "Updates a fence to a specified value"},
	{"GetClockCalibration", (PyCFunction)pydx12_ID3D12CommandQueue_GetClockCalibration, METH_NOARGS, "This method samples the CPU and GPU timestamp counters at the same moment in time"},
	{"GetTimestampFrequency", (PyCFunction)pydx12_ID3D12CommandQueue_GetTimestampFrequency, METH_NOARGS, "This method is used to determine the rate at which the GPU timestamp counter increments"},
	{NULL}  /* Sentinel */
};

int pydx12_init_queue(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D12_COMMAND_QUEUE_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_BOX);
	PYDX12_REGISTER_STRUCT(D3D12_RECT);

	pydx12_ID3D12CommandQueue_Type.tp_methods = pydx12_ID3D12CommandQueue_methods;
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

	PYDX12_ENUM(D3D12_CLEAR_FLAG_DEPTH);
	PYDX12_ENUM(D3D12_CLEAR_FLAG_STENCIL);

	return 0;
}