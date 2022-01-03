from pydx12 import *
from utils import get_best_adapter, UploadBuffer, Texture
from PIL import Image
import sys

D3D12GetDebugInterface().EnableDebugLayer()

device = D3D12CreateDevice(get_best_adapter())

info = ID3D12InfoQueue(device)

def d3d12_debug_hook(*args):
    global info
    for index in range(0, info.GetNumStoredMessages()):
        print(info.GetMessage(index).pDescription)
    print(args)

sys.excepthook = d3d12_debug_hook

image = Image.open('python-logo.png')
width, height = image.size
buffer = UploadBuffer(device, width * height * 4)
buffer.upload(image.tobytes())

texture = Texture(device, width, height)
print(texture.resource.GetDesc().to_dict())

command_queue_desc = D3D12_COMMAND_QUEUE_DESC(Type=D3D12_COMMAND_LIST_TYPE_COPY)
queue = device.CreateCommandQueue(command_queue_desc)

print(queue.GetClockCalibration(), queue.GetTimestampFrequency())