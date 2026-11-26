from pydx12 import D3D12CreateDevice
from utils import get_best_adapter

# a device is the D3D12 view of a GPU: everything (resources, queues, pipelines) is created from it
device = D3D12CreateDevice(get_best_adapter())

print('GPU number of nodes:', device.GetNodeCount())
