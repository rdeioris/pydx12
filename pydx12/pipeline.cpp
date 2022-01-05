#include "pydx12.h"

PYDX12_IMPORT(D3D12_SHADER_BYTECODE);
PYDX12_IMPORT(DXGI_SAMPLE_DESC);

PYDX12_IMPORT_COM(ID3D12RootSignature);
PYDX12_IMPORT_COM(ID3D12Pageable);

PYDX12_TYPE_WITH_REFS(D3D12_INPUT_ELEMENT_DESC);
PYDX12_ADD_REFS(D3D12_INPUT_ELEMENT_DESC) { PYDX12_INCREF(D3D12_INPUT_ELEMENT_DESC, data->SemanticName); }
PYDX12_RELEASE_REFS(D3D12_INPUT_ELEMENT_DESC) { PYDX12_DECREF(D3D12_INPUT_ELEMENT_DESC, data->SemanticName); }
PYDX12_STRING_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, SemanticName, py_SemanticName);
PYDX12_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, SemanticIndex, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, Format, LongLong, DXGI_FORMAT);
PYDX12_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, InputSlot, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, AlignedByteOffset, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, InputSlotClass, LongLong, D3D12_INPUT_CLASSIFICATION);
PYDX12_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, InstanceDataStepRate, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_INPUT_ELEMENT_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, SemanticName),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, SemanticIndex),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, Format),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, InputSlot),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, AlignedByteOffset),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, InputSlotClass),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_ELEMENT_DESC, InstanceDataStepRate),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_WITH_REFS(D3D12_INPUT_LAYOUT_DESC);
PYDX12_ADD_REFS(D3D12_INPUT_LAYOUT_DESC) { printf("^ACQUIRING %p\n", data->pInputElementDescs); PYDX12_INCREF(D3D12_INPUT_LAYOUT_DESC, data->pInputElementDescs); }
PYDX12_RELEASE_REFS(D3D12_INPUT_LAYOUT_DESC) { printf("$RELEASING %p\n", data->pInputElementDescs); PYDX12_DECREF(D3D12_INPUT_LAYOUT_DESC, data->pInputElementDescs); }
PYDX12_STRUCT_ARRAY_GETTER_SETTER(D3D12_INPUT_LAYOUT_DESC, pInputElementDescs, D3D12_INPUT_ELEMENT_DESC, NumElements);
PYDX12_GETTER_SETTER(D3D12_INPUT_LAYOUT_DESC, NumElements, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_INPUT_LAYOUT_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_LAYOUT_DESC, pInputElementDescs),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_INPUT_LAYOUT_DESC, NumElements),
	{ NULL }  /* Sentinel */
};


PYDX12_TYPE_WITH_REFS(D3D12_COMPUTE_PIPELINE_STATE_DESC);
PYDX12_ADD_REFS(D3D12_COMPUTE_PIPELINE_STATE_DESC) { PYDX12_COM_ADD(pRootSignature); }
PYDX12_RELEASE_REFS(D3D12_COMPUTE_PIPELINE_STATE_DESC) { PYDX12_COM_RELEASE(pRootSignature); }
PYDX12_COM_GETTER_SETTER(D3D12_COMPUTE_PIPELINE_STATE_DESC, ID3D12RootSignature, pRootSignature);
PYDX12_STRUCT_GETTER_SETTER(D3D12_COMPUTE_PIPELINE_STATE_DESC, CS, D3D12_SHADER_BYTECODE);
PYDX12_GETTER_SETTER(D3D12_COMPUTE_PIPELINE_STATE_DESC, NodeMask, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_COMPUTE_PIPELINE_STATE_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMPUTE_PIPELINE_STATE_DESC, pRootSignature),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMPUTE_PIPELINE_STATE_DESC, CS),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_COMPUTE_PIPELINE_STATE_DESC, NodeMask),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_RASTERIZER_DESC);
PYDX12_GETTER_SETTER(D3D12_RASTERIZER_DESC, FillMode, LongLong, D3D12_FILL_MODE);
PYDX12_GETTER_SETTER(D3D12_RASTERIZER_DESC, CullMode, LongLong, D3D12_CULL_MODE);
PYDX12_BOOL_GETTER_SETTER(D3D12_RASTERIZER_DESC, FrontCounterClockwise);
PYDX12_GETTER_SETTER(D3D12_RASTERIZER_DESC, DepthBias, Long, INT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_RASTERIZER_DESC, DepthBiasClamp, FLOAT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_RASTERIZER_DESC, SlopeScaledDepthBias, FLOAT);
PYDX12_BOOL_GETTER_SETTER(D3D12_RASTERIZER_DESC, DepthClipEnable);
PYDX12_BOOL_GETTER_SETTER(D3D12_RASTERIZER_DESC, MultisampleEnable);
PYDX12_BOOL_GETTER_SETTER(D3D12_RASTERIZER_DESC, AntialiasedLineEnable);
PYDX12_GETTER_SETTER(D3D12_RASTERIZER_DESC, ForcedSampleCount, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_RASTERIZER_DESC, ConservativeRaster, LongLong, D3D12_CONSERVATIVE_RASTERIZATION_MODE);
PYDX12_GETSETTERS(D3D12_RASTERIZER_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, FillMode),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, CullMode),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, FrontCounterClockwise),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, DepthBias),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, DepthBiasClamp),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, SlopeScaledDepthBias),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, DepthClipEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, MultisampleEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, AntialiasedLineEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, ForcedSampleCount),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RASTERIZER_DESC, ConservativeRaster),
	{ NULL }  /* Sentinel */
};


PYDX12_TYPE_WITH_REFS(D3D12_CACHED_PIPELINE_STATE);
PYDX12_ADD_REFS(D3D12_CACHED_PIPELINE_STATE) { PYDX12_INCREF(D3D12_CACHED_PIPELINE_STATE, data->pCachedBlob); }
PYDX12_RELEASE_REFS(D3D12_CACHED_PIPELINE_STATE) { PYDX12_DECREF(D3D12_CACHED_PIPELINE_STATE, data->pCachedBlob); }
PYDX12_BUFFER_GETTER_SETTER(D3D12_CACHED_PIPELINE_STATE, pCachedBlob, CachedBlobSizeInBytes);
PYDX12_GETTER_SETTER(D3D12_CACHED_PIPELINE_STATE, CachedBlobSizeInBytes, UnsignedLongLong, SIZE_T);
PYDX12_GETSETTERS(D3D12_CACHED_PIPELINE_STATE) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_CACHED_PIPELINE_STATE, pCachedBlob),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_CACHED_PIPELINE_STATE, CachedBlobSizeInBytes),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_RENDER_TARGET_BLEND_DESC);
PYDX12_BOOL_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, BlendEnable);
PYDX12_BOOL_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, LogicOpEnable);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, SrcBlend, LongLong, D3D12_BLEND);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, DestBlend, LongLong, D3D12_BLEND);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, BlendOp, LongLong, D3D12_BLEND_OP);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, SrcBlendAlpha, LongLong, D3D12_BLEND);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, DestBlendAlpha, LongLong, D3D12_BLEND);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, BlendOpAlpha, LongLong, D3D12_BLEND_OP);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, LogicOp, LongLong, D3D12_LOGIC_OP);
PYDX12_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, RenderTargetWriteMask, UnsignedLong, UINT8);
PYDX12_GETSETTERS(D3D12_RENDER_TARGET_BLEND_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, BlendEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, LogicOpEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, SrcBlend),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, DestBlend),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, BlendOp),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, SrcBlendAlpha),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, DestBlendAlpha),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, BlendOpAlpha),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, LogicOp),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_RENDER_TARGET_BLEND_DESC, RenderTargetWriteMask),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_BLEND_DESC);
PYDX12_BOOL_GETTER_SETTER(D3D12_BLEND_DESC, AlphaToCoverageEnable);
PYDX12_BOOL_GETTER_SETTER(D3D12_BLEND_DESC, IndependentBlendEnable);
PYDX12_STRUCT_CARRAY_GETTER_SETTER(D3D12_BLEND_DESC, RenderTarget, D3D12_RENDER_TARGET_BLEND_DESC);
PYDX12_GETSETTERS(D3D12_BLEND_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BLEND_DESC, AlphaToCoverageEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BLEND_DESC, IndependentBlendEnable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_BLEND_DESC, RenderTarget),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_WITH_REFS(D3D12_GRAPHICS_PIPELINE_STATE_DESC);
PYDX12_ADD_REFS(D3D12_GRAPHICS_PIPELINE_STATE_DESC) { PYDX12_COM_ADD(pRootSignature); }
PYDX12_RELEASE_REFS(D3D12_GRAPHICS_PIPELINE_STATE_DESC) { PYDX12_COM_RELEASE(pRootSignature); }
PYDX12_COM_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, ID3D12RootSignature, pRootSignature);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, VS, D3D12_SHADER_BYTECODE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, PS, D3D12_SHADER_BYTECODE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, DS, D3D12_SHADER_BYTECODE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, HS, D3D12_SHADER_BYTECODE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, GS, D3D12_SHADER_BYTECODE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, BlendState, D3D12_BLEND_DESC);
PYDX12_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, SampleMask, UnsignedLong, UINT);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, RasterizerState, D3D12_RASTERIZER_DESC);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, InputLayout, D3D12_INPUT_LAYOUT_DESC);
PYDX12_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, PrimitiveTopologyType, LongLong, D3D12_PRIMITIVE_TOPOLOGY_TYPE);
PYDX12_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, NumRenderTargets, UnsignedLong, UINT);
PYDX12_ARRAY_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, RTVFormats, DXGI_FORMAT, 8, PyLong_FromLongLong, PyLong_AsLongLong);
PYDX12_STRUCT_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, SampleDesc, DXGI_SAMPLE_DESC);
PYDX12_GETSETTERS(D3D12_GRAPHICS_PIPELINE_STATE_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, pRootSignature),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, VS),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, PS),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, DS),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, HS),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, GS),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, BlendState),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, SampleMask),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, RasterizerState),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, InputLayout),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, PrimitiveTopologyType),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, NumRenderTargets),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, RTVFormats),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_GRAPHICS_PIPELINE_STATE_DESC, SampleDesc),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_VIEWPORT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_VIEWPORT, TopLeftX, FLOAT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_VIEWPORT, TopLeftY, FLOAT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_VIEWPORT, Width, FLOAT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_VIEWPORT, Height, FLOAT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_VIEWPORT, MinDepth, FLOAT);
PYDX12_FLOAT_GETTER_SETTER(D3D12_VIEWPORT, MaxDepth, FLOAT);
PYDX12_GETSETTERS(D3D12_VIEWPORT) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VIEWPORT, TopLeftX),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VIEWPORT, TopLeftY),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VIEWPORT, Width),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VIEWPORT, Height),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VIEWPORT, MinDepth),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VIEWPORT, MaxDepth),
	{ NULL }  /* Sentinel */
};


PYDX12_TYPE_COM(ID3D12PipelineState);

int pydx12_init_pipeline(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D12_INPUT_ELEMENT_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_COMPUTE_PIPELINE_STATE_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_RASTERIZER_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_RENDER_TARGET_BLEND_DESC);

	PYDX12_REGISTER_STRUCT(D3D12_CACHED_PIPELINE_STATE);

	PYDX12_REGISTER_STRUCT(D3D12_INPUT_LAYOUT_DESC);

	PYDX12_REGISTER_STRUCT(D3D12_BLEND_DESC);
	PYDX12_REGISTER_STRUCT(D3D12_GRAPHICS_PIPELINE_STATE_DESC);

	PYDX12_REGISTER_STRUCT(D3D12_VIEWPORT);

	PYDX12_REGISTER_COM(ID3D12PipelineState, ID3D12Pageable);

	PYDX12_ENUM(D3D12_PIPELINE_STATE_FLAG_NONE);
	PYDX12_ENUM(D3D12_PIPELINE_STATE_FLAG_TOOL_DEBUG);

	PYDX12_ENUM(D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA);
	PYDX12_ENUM(D3D12_INPUT_CLASSIFICATION_PER_INSTANCE_DATA);

	PYDX12_ENUM(D3D12_FILL_MODE_WIREFRAME);
	PYDX12_ENUM(D3D12_FILL_MODE_SOLID);

	PYDX12_ENUM(D3D12_CULL_MODE_NONE);
	PYDX12_ENUM(D3D12_CULL_MODE_FRONT);
	PYDX12_ENUM(D3D12_CULL_MODE_BACK);

	PYDX12_ENUM(D3D12_CONSERVATIVE_RASTERIZATION_MODE_OFF);
	PYDX12_ENUM(D3D12_CONSERVATIVE_RASTERIZATION_MODE_ON);

	PYDX12_ENUM(D3D12_DEPTH_WRITE_MASK_ZERO);
	PYDX12_ENUM(D3D12_DEPTH_WRITE_MASK_ALL);

	PYDX12_ENUM(D3D12_COMPARISON_FUNC_NEVER);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_LESS);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_EQUAL);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_LESS_EQUAL);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_GREATER);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_NOT_EQUAL);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_GREATER_EQUAL);
	PYDX12_ENUM(D3D12_COMPARISON_FUNC_ALWAYS);

	PYDX12_ENUM(D3D12_STENCIL_OP_KEEP);
	PYDX12_ENUM(D3D12_STENCIL_OP_ZERO);
	PYDX12_ENUM(D3D12_STENCIL_OP_REPLACE);
	PYDX12_ENUM(D3D12_STENCIL_OP_INCR_SAT);
	PYDX12_ENUM(D3D12_STENCIL_OP_DECR_SAT);
	PYDX12_ENUM(D3D12_STENCIL_OP_INVERT);
	PYDX12_ENUM(D3D12_STENCIL_OP_INCR);
	PYDX12_ENUM(D3D12_STENCIL_OP_DECR);

	PYDX12_ENUM(D3D12_BLEND_ZERO);
	PYDX12_ENUM(D3D12_BLEND_ONE);
	PYDX12_ENUM(D3D12_BLEND_SRC_COLOR);
	PYDX12_ENUM(D3D12_BLEND_INV_SRC_COLOR);
	PYDX12_ENUM(D3D12_BLEND_SRC_ALPHA);
	PYDX12_ENUM(D3D12_BLEND_INV_SRC_ALPHA);
	PYDX12_ENUM(D3D12_BLEND_DEST_ALPHA);
	PYDX12_ENUM(D3D12_BLEND_INV_DEST_ALPHA);
	PYDX12_ENUM(D3D12_BLEND_DEST_COLOR);
	PYDX12_ENUM(D3D12_BLEND_INV_DEST_COLOR);
	PYDX12_ENUM(D3D12_BLEND_SRC_ALPHA_SAT);
	PYDX12_ENUM(D3D12_BLEND_BLEND_FACTOR);
	PYDX12_ENUM(D3D12_BLEND_INV_BLEND_FACTOR);
	PYDX12_ENUM(D3D12_BLEND_SRC1_COLOR);
	PYDX12_ENUM(D3D12_BLEND_INV_SRC1_COLOR);
	PYDX12_ENUM(D3D12_BLEND_SRC1_ALPHA);
	PYDX12_ENUM(D3D12_BLEND_INV_SRC1_ALPHA);

	PYDX12_ENUM(D3D12_PRIMITIVE_TOPOLOGY_TYPE_UNDEFINED);
	PYDX12_ENUM(D3D12_PRIMITIVE_TOPOLOGY_TYPE_POINT);
	PYDX12_ENUM(D3D12_PRIMITIVE_TOPOLOGY_TYPE_LINE);
	PYDX12_ENUM(D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE);
	PYDX12_ENUM(D3D12_PRIMITIVE_TOPOLOGY_TYPE_PATCH);

	PYDX12_ENUM(D3D12_BLEND_OP_ADD);
	PYDX12_ENUM(D3D12_BLEND_OP_SUBTRACT);
	PYDX12_ENUM(D3D12_BLEND_OP_REV_SUBTRACT);
	PYDX12_ENUM(D3D12_BLEND_OP_MIN);
	PYDX12_ENUM(D3D12_BLEND_OP_MAX);

	PYDX12_ENUM(D3D12_LOGIC_OP_CLEAR);
	PYDX12_ENUM(D3D12_LOGIC_OP_SET);
	PYDX12_ENUM(D3D12_LOGIC_OP_COPY);
	PYDX12_ENUM(D3D12_LOGIC_OP_COPY_INVERTED);
	PYDX12_ENUM(D3D12_LOGIC_OP_NOOP);
	PYDX12_ENUM(D3D12_LOGIC_OP_INVERT);
	PYDX12_ENUM(D3D12_LOGIC_OP_AND);
	PYDX12_ENUM(D3D12_LOGIC_OP_NAND);
	PYDX12_ENUM(D3D12_LOGIC_OP_OR);
	PYDX12_ENUM(D3D12_LOGIC_OP_NOR);
	PYDX12_ENUM(D3D12_LOGIC_OP_XOR);
	PYDX12_ENUM(D3D12_LOGIC_OP_EQUIV);
	PYDX12_ENUM(D3D12_LOGIC_OP_AND_REVERSE);
	PYDX12_ENUM(D3D12_LOGIC_OP_AND_INVERTED);
	PYDX12_ENUM(D3D12_LOGIC_OP_OR_REVERSE);
	PYDX12_ENUM(D3D12_LOGIC_OP_OR_INVERTED);

	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_UNDEFINED);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_POINTLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_LINELIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_LINESTRIP);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_LINELIST_ADJ);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_LINESTRIP_ADJ);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST_ADJ);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP_ADJ);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_1_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_2_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_3_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_4_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_5_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_6_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_7_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_8_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_9_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_10_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_11_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_12_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_13_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_14_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_15_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_16_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_17_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_18_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_19_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_20_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_21_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_22_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_23_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_24_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_25_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_26_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_27_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_28_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_29_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_30_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_31_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D_PRIMITIVE_TOPOLOGY_32_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_UNDEFINED);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_POINTLIST);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_LINELIST);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_LINESTRIP);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_LINELIST_ADJ);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_LINESTRIP_ADJ);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_TRIANGLELIST_ADJ);
	PYDX12_ENUM(D3D10_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP_ADJ);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_POINTLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_LINELIST_ADJ);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP_ADJ);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST_ADJ);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP_ADJ);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_1_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_2_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_3_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_4_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_5_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_6_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_7_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_8_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_9_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_10_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_11_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_12_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_13_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_14_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_15_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_16_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_17_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_18_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_19_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_20_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_21_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_22_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_23_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_24_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_25_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_26_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_27_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_28_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_29_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_30_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_31_CONTROL_POINT_PATCHLIST);
	PYDX12_ENUM(D3D11_PRIMITIVE_TOPOLOGY_32_CONTROL_POINT_PATCHLIST);

	PYDX12_ENUM(D3D12_COLOR_WRITE_ENABLE_RED);
	PYDX12_ENUM(D3D12_COLOR_WRITE_ENABLE_GREEN);
	PYDX12_ENUM(D3D12_COLOR_WRITE_ENABLE_BLUE);
	PYDX12_ENUM(D3D12_COLOR_WRITE_ENABLE_ALPHA);
	PYDX12_ENUM(D3D12_COLOR_WRITE_ENABLE_ALL);

	return 0;
}