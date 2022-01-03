#include "pydx12.h"

PYDX12_IMPORT_COM(ID3D12DeviceChild);

PYDX12_TYPE(D3D12_ROOT_CONSTANTS)
PYDX12_GETTER_SETTER(D3D12_ROOT_CONSTANTS, ShaderRegister, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_ROOT_CONSTANTS, RegisterSpace, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_ROOT_CONSTANTS, Num32BitValues, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_ROOT_CONSTANTS) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_CONSTANTS, ShaderRegister),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_CONSTANTS, RegisterSpace),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_CONSTANTS, Num32BitValues),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_ROOT_DESCRIPTOR)
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR, ShaderRegister, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR, RegisterSpace, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_ROOT_DESCRIPTOR) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR, ShaderRegister),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR, RegisterSpace),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_ROOT_DESCRIPTOR1)
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR1, ShaderRegister, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR1, RegisterSpace, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR1, Flags, LongLong, D3D12_ROOT_DESCRIPTOR_FLAGS);
PYDX12_GETSETTERS(D3D12_ROOT_DESCRIPTOR1) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR1, ShaderRegister),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR1, RegisterSpace),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR1, Flags),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_DESCRIPTOR_RANGE)
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, RangeType, LongLong, D3D12_DESCRIPTOR_RANGE_TYPE);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, NumDescriptors, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, BaseShaderRegister, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, RegisterSpace, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, OffsetInDescriptorsFromTableStart, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_DESCRIPTOR_RANGE) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, RangeType),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, NumDescriptors),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, BaseShaderRegister),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, RegisterSpace),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE, OffsetInDescriptorsFromTableStart),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_DESCRIPTOR_RANGE1)
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, RangeType, LongLong, D3D12_DESCRIPTOR_RANGE_TYPE);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, NumDescriptors, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, BaseShaderRegister, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, RegisterSpace, UnsignedLong, UINT);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, Flags, LongLong, D3D12_DESCRIPTOR_RANGE_FLAGS);
PYDX12_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, OffsetInDescriptorsFromTableStart, UnsignedLong, UINT);
PYDX12_GETSETTERS(D3D12_DESCRIPTOR_RANGE1) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, RangeType),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, NumDescriptors),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, BaseShaderRegister),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, RegisterSpace),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, Flags),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_DESCRIPTOR_RANGE1, OffsetInDescriptorsFromTableStart),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_ROOT_DESCRIPTOR_TABLE)
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE, NumDescriptorRanges, UnsignedLong, UINT);
PYDX12_STRUCT_ARRAY_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE, pDescriptorRanges, D3D12_DESCRIPTOR_RANGE, NumDescriptorRanges);
PYDX12_GETSETTERS(D3D12_ROOT_DESCRIPTOR_TABLE) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE, NumDescriptorRanges),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE, pDescriptorRanges),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_ROOT_DESCRIPTOR_TABLE1)
PYDX12_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE1, NumDescriptorRanges, UnsignedLong, UINT);
PYDX12_STRUCT_ARRAY_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE1, pDescriptorRanges, D3D12_DESCRIPTOR_RANGE1, NumDescriptorRanges);
PYDX12_GETSETTERS(D3D12_ROOT_DESCRIPTOR_TABLE1) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE1, NumDescriptorRanges),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_DESCRIPTOR_TABLE1, pDescriptorRanges),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_ROOT_PARAMETER1)
PYDX12_GETTER_SETTER(D3D12_ROOT_PARAMETER1, ParameterType, LongLong, D3D12_ROOT_PARAMETER_TYPE);
PYDX12_STRUCT_GETTER_SETTER(D3D12_ROOT_PARAMETER1, Constants, D3D12_ROOT_CONSTANTS);
PYDX12_STRUCT_GETTER_SETTER(D3D12_ROOT_PARAMETER1, Descriptor, D3D12_ROOT_DESCRIPTOR1);
PYDX12_STRUCT_GETTER_SETTER(D3D12_ROOT_PARAMETER1, DescriptorTable, D3D12_ROOT_DESCRIPTOR_TABLE1);
PYDX12_GETTER_SETTER(D3D12_ROOT_PARAMETER1, ShaderVisibility, LongLong, D3D12_SHADER_VISIBILITY);
PYDX12_GETSETTERS(D3D12_ROOT_PARAMETER1) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_PARAMETER1, ParameterType),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_PARAMETER1, Constants),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_PARAMETER1, Descriptor),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_PARAMETER1, DescriptorTable),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_PARAMETER1, ShaderVisibility),
	{ NULL }  /* Sentinel */
};


PYDX12_TYPE(D3D12_ROOT_SIGNATURE_DESC1);
PYDX12_GETTER_SETTER(D3D12_ROOT_SIGNATURE_DESC1, NumParameters, UnsignedLong, UINT);
PYDX12_STRUCT_ARRAY_GETTER_SETTER(D3D12_ROOT_SIGNATURE_DESC1, pParameters, D3D12_ROOT_PARAMETER1, NumParameters);
PYDX12_GETTER_SETTER(D3D12_ROOT_SIGNATURE_DESC1, Flags, LongLong, D3D12_ROOT_SIGNATURE_FLAGS);
PYDX12_GETSETTERS(D3D12_ROOT_SIGNATURE_DESC1) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_SIGNATURE_DESC1, NumParameters),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_SIGNATURE_DESC1, pParameters),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_ROOT_SIGNATURE_DESC1, Flags),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE(D3D12_VERSIONED_ROOT_SIGNATURE_DESC);
PYDX12_GETTER_SETTER(D3D12_VERSIONED_ROOT_SIGNATURE_DESC, Version, LongLong, D3D_ROOT_SIGNATURE_VERSION);
PYDX12_STRUCT_GETTER_SETTER(D3D12_VERSIONED_ROOT_SIGNATURE_DESC, Desc_1_1, D3D12_ROOT_SIGNATURE_DESC1);
PYDX12_GETSETTERS(D3D12_VERSIONED_ROOT_SIGNATURE_DESC) = {
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VERSIONED_ROOT_SIGNATURE_DESC, Version),
	PYDX12_DECLARE_GETTER_SETTER(D3D12_VERSIONED_ROOT_SIGNATURE_DESC, Desc_1_1),
	{ NULL }  /* Sentinel */
};

PYDX12_TYPE_COM(ID3D12RootSignature);

int pydx12_init_signature(PyObject* m)
{
	PYDX12_REGISTER_STRUCT(D3D12_ROOT_CONSTANTS);
	PYDX12_REGISTER_STRUCT(D3D12_ROOT_PARAMETER1);
	PYDX12_REGISTER_STRUCT(D3D12_ROOT_DESCRIPTOR1);
	PYDX12_REGISTER_STRUCT(D3D12_DESCRIPTOR_RANGE);
	PYDX12_REGISTER_STRUCT(D3D12_DESCRIPTOR_RANGE1);
	PYDX12_REGISTER_STRUCT(D3D12_ROOT_DESCRIPTOR_TABLE);
	PYDX12_REGISTER_STRUCT(D3D12_ROOT_DESCRIPTOR_TABLE1);

	PYDX12_REGISTER_STRUCT(D3D12_ROOT_SIGNATURE_DESC1);

	PYDX12_REGISTER_STRUCT(D3D12_VERSIONED_ROOT_SIGNATURE_DESC);

	PYDX12_REGISTER_COM(ID3D12RootSignature, ID3D12DeviceChild);

	PYDX12_ENUM(D3D_ROOT_SIGNATURE_VERSION_1);
	PYDX12_ENUM(D3D_ROOT_SIGNATURE_VERSION_1_0);
	PYDX12_ENUM(D3D_ROOT_SIGNATURE_VERSION_1_1);

	PYDX12_ENUM(D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE);
	PYDX12_ENUM(D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS);
	PYDX12_ENUM(D3D12_ROOT_PARAMETER_TYPE_CBV);
	PYDX12_ENUM(D3D12_ROOT_PARAMETER_TYPE_SRV);
	PYDX12_ENUM(D3D12_ROOT_PARAMETER_TYPE_UAV);

	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_ALL);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_VERTEX);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_HULL);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_DOMAIN);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_GEOMETRY);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_PIXEL);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_AMPLIFICATION);
	PYDX12_ENUM(D3D12_SHADER_VISIBILITY_MESH);

	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_TYPE_SRV);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_TYPE_UAV);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_TYPE_CBV);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_TYPE_SAMPLER);

	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_NONE);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_VERTEX_SHADER_ROOT_ACCESS);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_HULL_SHADER_ROOT_ACCESS);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_DOMAIN_SHADER_ROOT_ACCESS);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_GEOMETRY_SHADER_ROOT_ACCESS);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_PIXEL_SHADER_ROOT_ACCESS);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_ALLOW_STREAM_OUTPUT);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_LOCAL_ROOT_SIGNATURE);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_AMPLIFICATION_SHADER_ROOT_ACCESS);
	PYDX12_ENUM(D3D12_ROOT_SIGNATURE_FLAG_DENY_MESH_SHADER_ROOT_ACCESS);

	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_FLAG_NONE);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_FLAG_DATA_VOLATILE);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_FLAG_DATA_STATIC_WHILE_SET_AT_EXECUTE);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_FLAG_DATA_STATIC);
	PYDX12_ENUM(D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_STATIC_KEEPING_BUFFER_BOUNDS_CHECKS);

	PYDX12_ENUM(D3D12_ROOT_DESCRIPTOR_FLAG_NONE);
	PYDX12_ENUM(D3D12_ROOT_DESCRIPTOR_FLAG_DATA_VOLATILE);
	PYDX12_ENUM(D3D12_ROOT_DESCRIPTOR_FLAG_DATA_STATIC_WHILE_SET_AT_EXECUTE);
	PYDX12_ENUM(D3D12_ROOT_DESCRIPTOR_FLAG_DATA_STATIC);

	return 0;
}