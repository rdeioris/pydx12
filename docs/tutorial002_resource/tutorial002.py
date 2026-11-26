from pydx12 import *
from utils import get_best_adapter, buffer_desc

D3D12GetDebugInterface().EnableDebugLayer()

device = D3D12CreateDevice(get_best_adapter())

info = ID3D12InfoQueue(device)

# a 64 bytes buffer living in an UPLOAD heap (CPU writable, GPU readable)
desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_BUFFER)
desc.Width = 64
desc.Height = 1
desc.DepthOrArraySize = 1
desc.Format = DXGI_FORMAT_UNKNOWN
desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR
desc.MipLevels = 1
desc.SampleDesc.Count = 1

buffer = device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(
    Type=D3D12_HEAP_TYPE_UPLOAD), D3D12_HEAP_FLAG_NONE, desc, D3D12_RESOURCE_STATE_GENERIC_READ, None)

# descriptions are plain ctypes structures: print them, convert them to dicts or to raw bytes
data = buffer.GetDesc()
print(data)
print(data.to_dict())
print(bytes(data))

d2 = buffer.GetDesc().to_dict()
print(d2['SampleDesc'])

# the same buffer description built by the helper in utils.py
# (GetDesc() also reports the Alignment chosen by the driver)
print(buffer_desc(64).to_dict())

# writing to an upload buffer: map it, copy the bytes, unmap it
import ctypes
address = buffer.Map(0, D3D12_RANGE(0, 0))
ctypes.memmove(address, bytes(range(64)), 64)
buffer.Unmap(0)

print('debug layer messages:', info.GetNumStoredMessages())
