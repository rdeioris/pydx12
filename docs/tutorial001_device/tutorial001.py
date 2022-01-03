from pydx12 import D3D12CreateDevice
from utils import get_best_adapter

device = D3D12CreateDevice(get_best_adapter())

print('GPU number of nodes:', device.GetNodeCount())