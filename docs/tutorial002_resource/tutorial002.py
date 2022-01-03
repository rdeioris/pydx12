from pydx12 import D3D12CreateDevice, D3D12_RESOURCE_DESC
from pydx12.api import (D3D12_CLEAR_VALUE, D3D12_HEAP_FLAG_NONE, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_DESC, D3D12_RESOURCE_DIMENSION_BUFFER,
                        D3D12_RESOURCE_DIMENSION_TEXTURE2D, D3D12_RESOURCE_STATE_GENERIC_READ, DXGI_FORMAT_UNKNOWN, D3D12_HEAP_PROPERTIES, D3D12GetDebugInterface, ID3D12InfoQueue, D3D12_TEXTURE_LAYOUT_ROW_MAJOR)
from utils import get_best_adapter

D3D12GetDebugInterface().EnableDebugLayer()

device = D3D12CreateDevice(get_best_adapter())

info = ID3D12InfoQueue(device)

buffer_desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_BUFFER)
buffer_desc.Width = 64
buffer_desc.Height = 1
buffer_desc.DepthOrArraySize = 1
buffer_desc.Format = DXGI_FORMAT_UNKNOWN
buffer_desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
buffer_desc.MipLevels = 1
buffer_desc.SampleDesc.Count = 1

try:
    buffer = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
        Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, buffer_desc, D3D12_RESOURCE_STATE_GENERIC_READ, None)
except:
    for index in range(0, info.GetNumStoredMessages()):
        print(info.GetMessage(index).pDescription)

print(buffer.GetDesc().get_fields())
print(buffer.GetDesc().to_dict())
data = buffer.GetDesc()
print(data.to_bytes())
print(data.to_bytearray())

d = buffer.GetDesc()
d2 = d.to_dict()
d = None
print(d2['SampleDesc'].to_dict())

buffer.upload(bytearray(64))
