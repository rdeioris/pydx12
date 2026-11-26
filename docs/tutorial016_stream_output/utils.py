"""Helpers shared by the windowed tutorials (009-017).

Everything here is plain tutorial code written against the raw pydx12 API:
pydx12 itself only exposes DirectX, so windows come from tkinter, timing
from time.perf_counter and so on.
"""
import argparse
import atexit
import ctypes
import time
import tkinter

import numpy

from pydx12 import *

FRAME_COUNT = 2  # swapchain back buffers


def parse_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--frames', type=int, default=0,
                        help='exit after N frames (default: run until the window is closed)')
    return parser.parse_args()


# ---------------------------------------------------------------------------
# device and debug layer
# ---------------------------------------------------------------------------

def enable_debug():
    D3D12GetDebugInterface().EnableDebugLayer()


def get_best_adapter():
    return CreateDXGIFactory2().EnumAdapterByGpuPreference(0, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)


def get_messages(info):
    """Yield (severity, text) for every message stored in an ID3D12InfoQueue."""
    for index in range(info.GetNumStoredMessages()):
        size = ctypes.c_size_t()
        info.GetMessage(index, None, ctypes.byref(size))  # first call: size of the message
        buf = ctypes.create_string_buffer(size.value)
        message = ctypes.cast(buf, ctypes.POINTER(D3D12_MESSAGE))
        info.GetMessage(index, message, ctypes.byref(size))
        yield message.contents.Severity, message.contents.pDescription


def count_errors(info):
    return sum(1 for severity, _ in get_messages(info) if severity <= D3D12_MESSAGE_SEVERITY_ERROR)


def setup_debug(device):
    """Print the debug layer messages at exit; returns the ID3D12InfoQueue."""
    info = ID3D12InfoQueue(device)

    def dump():
        for severity, text in get_messages(info):
            print('[D3D12]', text)
        print('debug layer errors:', count_errors(info))
    atexit.register(dump)
    return info


# ---------------------------------------------------------------------------
# resources
# ---------------------------------------------------------------------------

def buffer_desc(size, flags=D3D12_RESOURCE_FLAG_NONE):
    desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                               DepthOrArraySize=1, MipLevels=1, Format=DXGI_FORMAT_UNKNOWN,
                               Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR, Flags=flags)
    desc.SampleDesc.Count = 1
    return desc


def create_buffer(device, size, heap_type, state, flags=D3D12_RESOURCE_FLAG_NONE):
    return device.CreateCommittedResource(D3D12_HEAP_PROPERTIES(Type=heap_type), D3D12_HEAP_FLAG_NONE,
                                          buffer_desc(size, flags), state)


def write_resource(resource, data, offset=0):
    """Copy bytes (or any buffer: numpy arrays, ctypes objects...) into a mappable resource."""
    view = memoryview(data).cast('B')
    address = resource.Map(0, D3D12_RANGE(0, 0))  # we won't read from it
    ctypes.memmove(address + offset, (ctypes.c_ubyte * len(view)).from_buffer_copy(view), len(view))
    resource.Unmap(0)


def read_resource(resource, size):
    address = resource.Map(0, D3D12_RANGE(0, size))
    data = ctypes.string_at(address, size)
    resource.Unmap(0, D3D12_RANGE(0, 0))
    return data


def upload_buffer(device, data):
    """An upload-heap buffer filled with data (fine for small/dynamic data)."""
    size = memoryview(data).nbytes
    resource = create_buffer(device, size, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ)
    write_resource(resource, data)
    return resource


def transition(resource, before, after):
    barrier = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    barrier.Transition = D3D12_RESOURCE_TRANSITION_BARRIER(
        pResource=resource, StateBefore=before, StateAfter=after,
        Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
    return barrier


def uav_barrier(resource):
    barrier = D3D12_RESOURCE_BARRIER(Type=D3D12_RESOURCE_BARRIER_TYPE_UAV)
    barrier.UAV.pResource = resource
    return barrier


def cpu_handles(device, heap, heap_type, count):
    """CPU descriptor handles for the first `count` slots of a descriptor heap."""
    start = heap.GetCPUDescriptorHandleForHeapStart().ptr
    step = device.GetDescriptorHandleIncrementSize(heap_type)
    return [D3D12_CPU_DESCRIPTOR_HANDLE(start + i * step) for i in range(count)]


class Fence:
    """A fence plus a counter: signal() and wait until the GPU caught up."""

    def __init__(self, device):
        self.fence = device.CreateFence(0)
        self.value = 0

    def flush(self, queue):
        self.value += 1
        queue.Signal(self.fence, self.value)
        if self.fence.GetCompletedValue() < self.value:
            self.fence.SetEventOnCompletion(self.value, None)  # NULL event: blocks until reached


def execute_and_wait(device, queue, record, list_type=D3D12_COMMAND_LIST_TYPE_DIRECT):
    """Record a one-shot command list with record(command_list), run it and wait."""
    allocator = device.CreateCommandAllocator(list_type)
    command_list = device.CreateCommandList(0, list_type, allocator)
    record(command_list)
    command_list.Close()
    queue.ExecuteCommandLists([command_list])
    Fence(device).flush(queue)


def default_buffer(device, queue, data, final_state):
    """A default-heap (GPU only) buffer initialized through a temporary upload buffer."""
    size = memoryview(data).nbytes
    staging = upload_buffer(device, data)
    resource = create_buffer(device, size, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON)

    def record(command_list):
        command_list.CopyResource(resource, staging)
        command_list.ResourceBarrier([transition(resource, D3D12_RESOURCE_STATE_COPY_DEST, final_state)])
    execute_and_wait(device, queue, record)
    return resource


# ---------------------------------------------------------------------------
# window and swapchain
# ---------------------------------------------------------------------------

class App:
    """A tkinter window whose client area hosts a DXGI swapchain."""

    def __init__(self, title, width, height):
        self.title = title
        self.root = tkinter.Tk()
        self.root.title(title)
        self.frame = tkinter.Frame(self.root, width=width, height=height, bg='')
        self.frame.pack(fill=tkinter.BOTH, expand=True)
        self.root.update()
        self.hwnd = self.frame.winfo_id()
        self.width, self.height = width, height
        self.resized = False
        self.running = True
        self.fullscreen = False
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.frame.bind('<Configure>', self._on_configure)
        self.root.bind('<Escape>', lambda e: self.close())
        self._frames = 0
        self._last = time.perf_counter()

    def _on_configure(self, event):
        if event.width > 0 and event.height > 0 and (event.width, event.height) != (self.width, self.height):
            self.width, self.height = event.width, event.height
            self.resized = True

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)

    def close(self):
        self.running = False

    def pump(self):
        """Process window events; returns False once the window has been closed."""
        self.root.update()
        self._frames += 1
        now = time.perf_counter()
        if now - self._last >= 1:
            self.fps = self._frames / (now - self._last)
            self.root.title('%s - %.0f fps' % (self.title, self.fps))
            self._frames, self._last = 0, now
        return self.running

    def destroy(self):
        self.root.destroy()


class SwapChain:
    """Flip-model swapchain + one RTV per back buffer."""

    def __init__(self, device, queue, app, format=DXGI_FORMAT_R8G8B8A8_UNORM):
        self.device = device
        self.queue = queue
        self.format = format
        desc = DXGI_SWAP_CHAIN_DESC1(Width=app.width, Height=app.height, Format=format,
                                     BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=FRAME_COUNT,
                                     Scaling=DXGI_SCALING_STRETCH, SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD)
        desc.SampleDesc.Count = 1
        self.swapchain = IDXGISwapChain3(CreateDXGIFactory2().CreateSwapChainForHwnd(queue, app.hwnd, desc))
        self.rtv_heap = device.CreateDescriptorHeap(D3D12_DESCRIPTOR_HEAP_DESC(
            Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV, NumDescriptors=FRAME_COUNT))
        self.rtvs = cpu_handles(device, self.rtv_heap, D3D12_DESCRIPTOR_HEAP_TYPE_RTV, FRAME_COUNT)
        self.fence = Fence(device)
        self.width, self.height = app.width, app.height
        self._create_views()

    def _create_views(self):
        self.buffers = [self.swapchain.GetBuffer(i) for i in range(FRAME_COUNT)]
        for buffer, rtv in zip(self.buffers, self.rtvs):
            self.device.CreateRenderTargetView(buffer, None, rtv)

    def resize(self, width, height):
        self.fence.flush(self.queue)  # the GPU must not use the old buffers anymore
        self.buffers = []  # release every reference before ResizeBuffers
        self.swapchain.ResizeBuffers(FRAME_COUNT, width, height)
        self.width, self.height = width, height
        self._create_views()

    def current(self):
        """(back buffer resource, its RTV) for this frame.

        The returned wrapper does not hold a COM reference (addref=False and not owned):
        ResizeBuffers() fails while anybody still references the old buffers, and a
        `back_buffer` variable surviving from the previous frame would be enough.
        """
        index = self.swapchain.GetCurrentBackBufferIndex()
        return ID3D12Resource.from_address(self.buffers[index].value, addref=False), self.rtvs[index]

    def present(self, sync_interval=1):
        self.swapchain.Present(sync_interval, 0)
        self.fence.flush(self.queue)  # keep it simple: one frame in flight


# ---------------------------------------------------------------------------
# shaders, root signatures, vertex buffers
# ---------------------------------------------------------------------------

def compile_shader(source, entry, target, defines=None):
    """D3DCompile (FXC, shader model 5.x); defines is a dict of macros."""
    macros = None
    if defines:
        macros = [D3D_SHADER_MACRO(Name=k, Definition=str(v)) for k, v in defines.items()]
        macros.append(D3D_SHADER_MACRO())  # the array is NULL terminated
    return D3DCompile(source, None, macros, None, entry, target)


def create_root_signature(device, parameters=(), flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT):
    """Serialize and create a version 1.1 root signature from D3D12_ROOT_PARAMETER1 objects."""
    desc = D3D12_VERSIONED_ROOT_SIGNATURE_DESC(Version=D3D_ROOT_SIGNATURE_VERSION_1_1)
    desc.Desc_1_1 = D3D12_ROOT_SIGNATURE_DESC1(pParameters=list(parameters) or None, Flags=flags)
    return device.CreateRootSignature(0, D3D12SerializeVersionedRootSignature(desc))


def root_constants(register, count, visibility=D3D12_SHADER_VISIBILITY_ALL):
    """A root parameter holding `count` 32 bit constants visible as cbuffer b<register>."""
    param = D3D12_ROOT_PARAMETER1(ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS,
                                  ShaderVisibility=visibility)
    param.Constants.ShaderRegister = register
    param.Constants.Num32BitValues = count
    return param


def vertex_buffer_view(device, queue, data, stride):
    """Upload data into a default-heap vertex buffer; returns (resource, D3D12_VERTEX_BUFFER_VIEW)."""
    resource = default_buffer(device, queue, data, D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER)
    view = D3D12_VERTEX_BUFFER_VIEW(BufferLocation=resource.GetGPUVirtualAddress(),
                                    SizeInBytes=memoryview(data).nbytes, StrideInBytes=stride)
    return resource, view


def graphics_pipeline_desc(root_signature, vs, ps, input_elements, rtv_format=DXGI_FORMAT_R8G8B8A8_UNORM):
    """A D3D12_GRAPHICS_PIPELINE_STATE_DESC with sensible defaults (no blending, no culling, no depth)."""
    desc = D3D12_GRAPHICS_PIPELINE_STATE_DESC(
        pRootSignature=root_signature,
        VS=D3D12_SHADER_BYTECODE(pShaderBytecode=vs), PS=D3D12_SHADER_BYTECODE(pShaderBytecode=ps),
        SampleMask=0xFFFFFFFF, PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE,
        NumRenderTargets=1, RTVFormats=(rtv_format,))
    desc.InputLayout.pInputElementDescs = input_elements
    desc.RasterizerState.FillMode = D3D12_FILL_MODE_SOLID
    desc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE
    desc.RasterizerState.DepthClipEnable = True
    desc.BlendState.RenderTarget[0].RenderTargetWriteMask = D3D12_COLOR_WRITE_ENABLE_ALL
    desc.SampleDesc.Count = 1
    return desc


def viewport_and_scissor(width, height):
    return ([D3D12_VIEWPORT(Width=width, Height=height, MinDepth=0, MaxDepth=1)],
            [D3D12_RECT(left=0, top=0, right=width, bottom=height)])


# ---------------------------------------------------------------------------
# meshes and matrices
# ---------------------------------------------------------------------------

class Mesh:
    """Indexed geometry: one vertex buffer per attribute (slot 0, 1, ...) plus an index buffer.

    attributes is a list of float32 numpy arrays shaped (nvertices, ncomponents);
    matrix is the per-mesh 4x4 float32 matrix the renderer passes as root constants.
    """

    def __init__(self, device, queue, attributes, indices):
        self.buffers = []
        self.views = []
        for data in attributes:
            data = numpy.ascontiguousarray(data, dtype=numpy.float32)
            resource, view = vertex_buffer_view(device, queue, data, stride=data.shape[1] * 4)
            self.buffers.append(resource)
            self.views.append(view)
        indices = numpy.ascontiguousarray(indices)
        self.index_buffer = default_buffer(device, queue, indices, D3D12_RESOURCE_STATE_INDEX_BUFFER)
        self.index_buffer_view = D3D12_INDEX_BUFFER_VIEW(
            BufferLocation=self.index_buffer.GetGPUVirtualAddress(), SizeInBytes=indices.nbytes,
            Format=DXGI_FORMAT_R16_UINT if indices.dtype == numpy.uint16 else DXGI_FORMAT_R32_UINT)
        self.nindices = len(indices)
        self.matrix = numpy.identity(4, dtype=numpy.float32)

    def draw(self, command_list, matrix_parameter=0):
        command_list.SetGraphicsRoot32BitConstants(matrix_parameter, 16, self.matrix.astype(numpy.float32), 0)
        command_list.IASetVertexBuffers(0, self.views)
        command_list.IASetIndexBuffer(self.index_buffer_view)
        command_list.DrawIndexedInstanced(self.nindices, 1, 0, 0, 0)


def cube(size=1.0):
    """Positions, per-face colors and indices of a cube (counter clockwise faces seen from outside)."""
    positions, colors, indices = [], [], []
    faces = [((1, 0, 0), (0, 0, -1), (0, 1, 0)), ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
             ((0, 1, 0), (1, 0, 0), (0, 0, -1)), ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
             ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (-1, 0, 0), (0, 1, 0))]
    palette = [(1, 0, 0), (0, 1, 1), (0, 1, 0), (1, 0, 1), (0, 0, 1), (1, 1, 0)]
    for (normal, u, v), color in zip(faces, palette):
        n, u, v = numpy.array(normal), numpy.array(u), numpy.array(v)
        base = len(positions)
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            positions.append((n + su * u + sv * v) * size / 2)
            colors.append(color)
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return (numpy.array(positions, dtype=numpy.float32), numpy.array(colors, dtype=numpy.float32),
            numpy.array(indices, dtype=numpy.uint16))


# Row-vector matrices (like pyrr and DirectXMath): v' = v @ M, so M = model @ view @ projection.
# Right handed (the camera looks down -z) with depth mapped to [0, 1] as Direct3D expects.

def orthographic(width, height, near, far):
    m = numpy.zeros((4, 4), dtype=numpy.float32)
    m[0, 0], m[1, 1] = 2 / width, 2 / height
    m[2, 2], m[3, 2], m[3, 3] = 1 / (near - far), near / (near - far), 1
    return m


def perspective(fovy_degrees, aspect, near, far):
    """Right handed perspective projection with depth in [0, 1] (XMMatrixPerspectiveFovRH)."""
    f = 1 / numpy.tan(numpy.radians(fovy_degrees) / 2)
    m = numpy.zeros((4, 4), dtype=numpy.float32)
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = far / (near - far), -1
    m[3, 2] = near * far / (near - far)
    return m


# ---------------------------------------------------------------------------
# depth buffer and glTF loading
# ---------------------------------------------------------------------------

class DepthBuffer:
    """A D32 depth texture and its DSV (recreate it when the window is resized)."""

    def __init__(self, device, width, height, format=DXGI_FORMAT_D32_FLOAT):
        self.device = device
        self.format = format
        self.heap = device.CreateDescriptorHeap(D3D12_DESCRIPTOR_HEAP_DESC(Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV,
                                                                           NumDescriptors=1))
        self.dsv = self.heap.GetCPUDescriptorHandleForHeapStart()
        self.resize(width, height)

    def resize(self, width, height):
        desc = D3D12_RESOURCE_DESC(Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=width, Height=height,
                                   DepthOrArraySize=1, MipLevels=1, Format=self.format,
                                   Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL)
        desc.SampleDesc.Count = 1
        clear = D3D12_CLEAR_VALUE(Format=self.format)
        clear.DepthStencil.Depth = 1.0  # clearing to this value is the fast path
        self.resource = self.device.CreateCommittedResource(
            D3D12_HEAP_PROPERTIES(Type=D3D12_HEAP_TYPE_DEFAULT), D3D12_HEAP_FLAG_NONE, desc,
            D3D12_RESOURCE_STATE_DEPTH_WRITE, clear)
        self.device.CreateDepthStencilView(self.resource, None, self.dsv)


class GLTF:
    """Minimal glTF 2.0 reader (.gltf with embedded buffers or .glb): enough for static meshes."""
    COMPONENTS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    DTYPES = {5120: numpy.int8, 5121: numpy.uint8, 5122: numpy.int16, 5123: numpy.uint16,
              5125: numpy.uint32, 5126: numpy.float32}

    def __init__(self, path):
        import base64
        import json
        import os
        import struct
        with open(path, 'rb') as f:
            data = f.read()
        self.binary = None
        if data[:4] == b'glTF':  # binary container: header + JSON chunk + BIN chunk
            offset = 12
            while offset < len(data):
                length, kind = struct.unpack_from('<II', data, offset)
                chunk = data[offset + 8:offset + 8 + length]
                if kind == 0x4E4F534A:
                    self.asset = json.loads(chunk)
                elif kind == 0x004E4942:
                    self.binary = chunk
                offset += 8 + length
        else:
            self.asset = json.loads(data)
        self.buffers = []
        for buffer in self.asset['buffers']:
            uri = buffer.get('uri')
            if uri is None:
                self.buffers.append(self.binary)
            elif uri.startswith('data:'):
                self.buffers.append(base64.b64decode(uri.split(',', 1)[1]))
            else:
                with open(os.path.join(os.path.dirname(path), uri), 'rb') as f:
                    self.buffers.append(f.read())

    def accessor(self, index):
        accessor = self.asset['accessors'][index]
        view = self.asset['bufferViews'][accessor['bufferView']]
        dtype = numpy.dtype(self.DTYPES[accessor['componentType']])
        ncomponents = self.COMPONENTS[accessor['type']]
        start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', ncomponents * dtype.itemsize)
        raw = numpy.frombuffer(self.buffers[view['buffer']], dtype=numpy.uint8,
                               count=stride * (accessor['count'] - 1) + ncomponents * dtype.itemsize, offset=start)
        rows = numpy.lib.stride_tricks.as_strided(raw, (accessor['count'], ncomponents * dtype.itemsize),
                                                  (stride, 1))
        return numpy.ascontiguousarray(rows).view(dtype).reshape(accessor['count'], ncomponents)

    def mesh_transform(self, mesh_index):
        """World matrix (row-vector convention) of the first node using the mesh."""
        nodes = self.asset.get('nodes', [])
        parents = {child: i for i, node in enumerate(nodes) for child in node.get('children', [])}

        def local(node):
            if 'matrix' in node:  # glTF matrices are column major == our row-vector layout
                return numpy.array(node['matrix'], dtype=numpy.float32).reshape(4, 4)
            m = numpy.identity(4, dtype=numpy.float32)
            sx, sy, sz = node.get('scale', (1, 1, 1))
            m = m @ numpy.diag([sx, sy, sz, 1]).astype(numpy.float32)
            x, y, z, w = node.get('rotation', (0, 0, 0, 1))
            r = numpy.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0],
                             [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0],
                             [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0],
                             [0, 0, 0, 1]], dtype=numpy.float32)
            t = numpy.identity(4, dtype=numpy.float32)
            t[3, :3] = node.get('translation', (0, 0, 0))
            return m @ r @ t
        for i, node in enumerate(nodes):
            if node.get('mesh') == mesh_index:
                matrix = local(node)
                while i in parents:
                    i = parents[i]
                    matrix = matrix @ local(nodes[i])
                return matrix
        return numpy.identity(4, dtype=numpy.float32)

    def primitive(self, mesh_index=0):
        """(attributes dict name -> numpy array, indices, world matrix) of a mesh's first primitive."""
        primitive = self.asset['meshes'][mesh_index]['primitives'][0]
        attributes = {name: self.accessor(index) for name, index in primitive['attributes'].items()}
        if 'indices' in primitive:
            indices = self.accessor(primitive['indices']).ravel()
        else:
            indices = numpy.arange(len(attributes['POSITION']), dtype=numpy.uint32)
        if indices.dtype not in (numpy.uint16, numpy.uint32):
            indices = indices.astype(numpy.uint32)
        return attributes, indices, self.mesh_transform(mesh_index)
