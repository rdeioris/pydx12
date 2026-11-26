from PIL import Image

from pydx12 import *
from utils import get_best_adapter, UploadBuffer, Texture

D3D12GetDebugInterface().EnableDebugLayer()

device = D3D12CreateDevice(get_best_adapter())

info = ID3D12InfoQueue(device)

image = Image.open('python-logo.png').convert('RGBA')
width, height = image.size
buffer = UploadBuffer(device, width * height * 4)
buffer.upload(image.tobytes())

texture = Texture(device, width, height)
print(texture.resource.GetDesc().to_dict())

# command queues execute the work recorded in command lists; COPY queues can only copy data
command_queue_desc = D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_COPY)
queue = device.CreateCommandQueue(command_queue_desc)

# out parameters are returned: (GPU timestamp, CPU timestamp) and the GPU ticks per second
gpu_timestamp, cpu_timestamp = queue.GetClockCalibration()
print('GPU timestamp:', gpu_timestamp, 'CPU timestamp:', cpu_timestamp)
print('GPU timestamp frequency:', queue.GetTimestampFrequency())

print('debug layer messages:', info.GetNumStoredMessages())
