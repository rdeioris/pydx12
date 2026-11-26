from PIL import Image

from pydx12 import *
from utils import get_best_adapter, UploadBuffer, Texture

D3D12GetDebugInterface().EnableDebugLayer()

device = D3D12CreateDevice(get_best_adapter())

info = ID3D12InfoQueue(device)

image = Image.open('python-logo.png').convert('RGBA')
width, height = image.size

# the pixels go to a CPU visible upload buffer...
buffer = UploadBuffer(device, width * height * 4)
buffer.upload(image.tobytes())

# ...while the texture lives in GPU memory (DEFAULT heap) with an opaque layout:
# the next tutorials show how to copy the pixels into it
texture = Texture(device, width, height)
print(texture.resource.GetDesc().to_dict())

print('debug layer messages:', info.GetNumStoredMessages())
