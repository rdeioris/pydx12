"""DirectStorage: stream a compressed 8K texture from disk straight into GPU memory.

1. bake: a compute shader renders the Mandelbrot set into a 8192 x 8192 RGBA texture (256 MB); it is read
   back, split into 64 chunks of 128 rows and each chunk is compressed with GDeflate by DirectStorage's own
   codec, into a cache file
2. load with DirectStorage: one request per chunk reads it from the file, the GPU decompresses it and writes
   it into its region of a D3D12 texture; a fence tells when everything is there
3. load the classic way, for comparison: Python reads the file, the CPU decompresses, the data goes
   through an upload heap and a copy command
4. explore the fractal at full resolution in a window; R reloads it with DirectStorage, C with the CPU path

DirectStorage ships as a NuGet package (Microsoft.Direct3D.DirectStorage): pass the folder holding
dstorage.dll and dstoragecore.dll with --dstorage, or put them next to python.exe.

Usage: python examples/directstorage.py [--dstorage DIR] [--rebake] [--check] [--frames N]
"""
import argparse
import ctypes
import glob
import os
import struct
import tempfile
import time
import tkinter

import numpy

import pydx12 as dx

SIZE = 8192
CHUNK_ROWS = 128                      # 8192 * 4 bytes * 128 rows = 4 MB per request
ROW_BYTES = SIZE * 4                  # already a multiple of D3D12_TEXTURE_DATA_PITCH_ALIGNMENT
CHUNK_BYTES = ROW_BYTES * CHUNK_ROWS
NUM_CHUNKS = SIZE // CHUNK_ROWS
MAGIC = b'PYDX12G2'
VIEW_W, VIEW_H = 1280, 720
CENTER, SPAN = (-0.745, 0.0), 3.0   # the region of the complex plane covered by the texture
START = (-0.745, 0.11)              # the view opens on seahorse valley

MANDELBROT = """
RWTexture2D<unorm float4> Output : register(u0);

[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID)
{
    float2 c = float2(%(cx)f, %(cy)f) + (float2(id.xy) / %(size)d.0 - 0.5) * float2(%(span)f, -%(span)f);
    float2 z = 0;
    uint i;
    const uint N = 1024;
    for (i = 0; i < N && dot(z, z) < 256; i++)
        z = float2(z.x * z.x - z.y * z.y, 2 * z.x * z.y) + c;
    float3 color = float3(0.01, 0.01, 0.03);  // inside the set
    if (i < N)
    {
        float smoothed = i + 1 - log2(log2(dot(z, z)));  // continuous iteration count: no color bands
        float t = sqrt(smoothed) * 0.35;
        color = 0.5 + 0.5 * cos(6.28318 * (t + float3(0.0, 0.12, 0.28)));
        color *= saturate(smoothed / 8);  // fade the outer area to black
    }
    Output[id.xy] = float4(color, 1);
}
""" % {'cx': CENTER[0], 'cy': CENTER[1], 'size': SIZE, 'span': SPAN}


# ---- baking ------------------------------------------------------------------------------------
def render_fractal(gpu):
    """Render the Mandelbrot set with a compute shader and read the 256 MB back (a readback buffer)."""
    device = gpu.device
    shader = dx.D3DCompile(MANDELBROT, None, None, None, 'main', 'cs_5_0')
    uav = dx.D3D12_DESCRIPTOR_RANGE(RangeType=dx.D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=1)
    table = dx.D3D12_ROOT_PARAMETER(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE)
    table.DescriptorTable = dx.D3D12_ROOT_DESCRIPTOR_TABLE(pDescriptorRanges=[uav])
    root = device.CreateRootSignature(0, dx.D3D12SerializeRootSignature(
        dx.D3D12_ROOT_SIGNATURE_DESC(pParameters=[table]), dx.D3D_ROOT_SIGNATURE_VERSION_1))
    pso = device.CreateComputePipelineState(dx.D3D12_COMPUTE_PIPELINE_STATE_DESC(
        pRootSignature=root, CS=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=shader)))
    heap = device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
        Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, NumDescriptors=1,
        Flags=dx.D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE))
    texture = gpu.texture(dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
    device.CreateUnorderedAccessView(texture, None, dx.D3D12_UNORDERED_ACCESS_VIEW_DESC(
        Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM, ViewDimension=dx.D3D12_UAV_DIMENSION_TEXTURE2D),
        heap.GetCPUDescriptorHandleForHeapStart())
    readback = gpu.buffer(SIZE * SIZE * 4, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
    placed, whole = gpu.texture_copy_locations(texture, readback)

    def record(cl):
        cl.SetPipelineState(pso)
        cl.SetComputeRootSignature(root)
        cl.SetDescriptorHeaps([heap])
        cl.SetComputeRootDescriptorTable(0, heap.GetGPUDescriptorHandleForHeapStart())
        cl.ResourceBarrier([transition(texture, dx.D3D12_RESOURCE_STATE_COMMON,
                                       dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
        cl.Dispatch(SIZE // 8, SIZE // 8, 1)
        cl.ResourceBarrier([transition(texture, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                       dx.D3D12_RESOURCE_STATE_COPY_SOURCE)])
        cl.CopyTextureRegion(placed, 0, 0, 0, whole, None)
    gpu.run(record)
    return readback


def bake(path, gpu, codec):
    """Write the GDeflate compressed chunks: header, chunk table (offset, size) and data."""
    print('baking a %dx%d Mandelbrot texture (%d MB) into %s ...' % (SIZE, SIZE, SIZE * SIZE * 4 >> 20, path))
    start = time.perf_counter()
    readback = render_fractal(gpu)
    pixels = readback.Map(0)  # rows are tightly packed: 32768 bytes is already the footprint's row pitch
    print('  rendered on the GPU in %.2f s' % (time.perf_counter() - start))
    bound = codec.CompressBufferBound(CHUNK_BYTES)
    scratch = numpy.empty(bound, numpy.uint8)
    used = ctypes.c_size_t()
    chunks = []
    for i in range(NUM_CHUNKS):
        codec.CompressBuffer(pixels + i * CHUNK_BYTES, CHUNK_BYTES, dx.DSTORAGE_COMPRESSION_DEFAULT,
                             scratch.ctypes.data, bound, ctypes.byref(used))
        chunks.append(scratch[:used.value].tobytes())
    readback.Unmap(0)
    header = MAGIC + struct.pack('<4I', SIZE, SIZE, CHUNK_ROWS, NUM_CHUNKS)
    offset = len(header) + 16 * NUM_CHUNKS
    table = b''
    for chunk in chunks:
        table += struct.pack('<2Q', offset, len(chunk))
        offset += len(chunk)
    with open(path, 'wb') as f:
        f.write(header + table + b''.join(chunks))
    total = sum(len(c) for c in chunks)
    print('  done in %.1f s, %d MB -> %d MB (%.1f:1)' % (time.perf_counter() - start, SIZE * SIZE * 4 >> 20,
                                                        total >> 20, SIZE * SIZE * 4 / total))


def read_table(path):
    with open(path, 'rb') as f:
        header = f.read(len(MAGIC) + 16)
        if header[:len(MAGIC)] != MAGIC or struct.unpack('<4I', header[len(MAGIC):]) != (SIZE, SIZE, CHUNK_ROWS,
                                                                                         NUM_CHUNKS):
            return None
        return [struct.unpack('<2Q', f.read(16)) for _ in range(NUM_CHUNKS)]


# ---- D3D12 -------------------------------------------------------------------------------------
def transition(resource, before, after):
    b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    b.Transition = dx.D3D12_RESOURCE_TRANSITION_BARRIER(pResource=resource, StateBefore=before, StateAfter=after,
                                                        Subresource=dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
    return b


class Gpu:
    def __init__(self, hwnd):
        factory = dx.CreateDXGIFactory2()
        adapter = factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)
        print(adapter.GetDesc1().Description)
        self.device = dx.D3D12CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_0)
        self.queue = self.device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
        self.allocator = self.device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
        self.cl = self.device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, self.allocator)
        self.cl.Close()
        self.fence = self.device.CreateFence()
        self.fence_value = 0
        desc = dx.DXGI_SWAP_CHAIN_DESC1(Width=VIEW_W, Height=VIEW_H, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                        BufferUsage=dx.DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=2,
                                        SwapEffect=dx.DXGI_SWAP_EFFECT_FLIP_DISCARD)
        desc.SampleDesc.Count = 1
        self.swap_chain = dx.IDXGISwapChain3(factory.CreateSwapChainForHwnd(self.queue, hwnd, desc))
        self.back_buffers = [self.swap_chain.GetBuffer(i) for i in range(2)]

    def texture(self, flags=dx.D3D12_RESOURCE_FLAG_NONE):
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=SIZE, Height=SIZE,
                                      DepthOrArraySize=1, MipLevels=1, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                      Flags=flags)
        desc.SampleDesc.Count = 1
        # DirectStorage writes into resources in the COMMON state
        return self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                                   dx.D3D12_HEAP_FLAG_NONE, desc, dx.D3D12_RESOURCE_STATE_COMMON)

    def buffer(self, size, heap, state):
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                                      DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR)
        desc.SampleDesc.Count = 1
        return self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=heap), dx.D3D12_HEAP_FLAG_NONE,
                                                   desc, state)

    def wait(self):
        self.fence_value += 1
        self.queue.Signal(self.fence, self.fence_value)
        self.fence.SetEventOnCompletion(self.fence_value, None)

    def run(self, record):
        self.allocator.Reset()
        self.cl.Reset(self.allocator)
        record(self.cl)
        self.cl.Close()
        self.queue.ExecuteCommandLists([self.cl])
        self.wait()

    def texture_copy_locations(self, texture, buffer):
        footprints, _, _, total = self.device.GetCopyableFootprints(texture.GetDesc(), 0, 1, 0)
        placed = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=buffer, Type=dx.D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT)
        placed.PlacedFootprint = footprints[0]
        whole = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=texture, Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX)
        return placed, whole

    def present_view(self, texture, x, y):
        index = self.swap_chain.GetCurrentBackBufferIndex()
        back_buffer = self.back_buffers[index]

        def record(cl):
            cl.ResourceBarrier([transition(back_buffer, dx.D3D12_RESOURCE_STATE_PRESENT,
                                           dx.D3D12_RESOURCE_STATE_COPY_DEST)])
            # the texture is in COMMON: it is promoted to COPY_SOURCE implicitly and decays back afterwards
            cl.CopyTextureRegion(
                dx.D3D12_TEXTURE_COPY_LOCATION(pResource=back_buffer,
                                               Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX), 0, 0, 0,
                dx.D3D12_TEXTURE_COPY_LOCATION(pResource=texture, Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX),
                dx.D3D12_BOX(x, y, 0, x + VIEW_W, y + VIEW_H, 1))
            cl.ResourceBarrier([transition(back_buffer, dx.D3D12_RESOURCE_STATE_COPY_DEST,
                                           dx.D3D12_RESOURCE_STATE_PRESENT)])
        self.run(record)
        self.swap_chain.Present(1, 0)


# ---- the two loaders ---------------------------------------------------------------------------
class DirectStorageLoader:
    def __init__(self, gpu, path):
        self.gpu = gpu
        self.factory = dx.DStorageGetFactory()
        self.file = self.factory.OpenFile(path)
        self.table = read_table(path)
        self.queue = self.factory.CreateQueue(dx.DSTORAGE_QUEUE_DESC(
            SourceType=dx.DSTORAGE_REQUEST_SOURCE_FILE, Capacity=dx.DSTORAGE_MAX_QUEUE_CAPACITY,
            Priority=dx.DSTORAGE_PRIORITY_NORMAL, Name='8K texture', Device=gpu.device))
        support = dx.IDStorageQueue2(self.queue).GetCompressionSupport(dx.DSTORAGE_COMPRESSION_FORMAT_GDEFLATE)
        if support & dx.DSTORAGE_COMPRESSION_SUPPORT_GPU_OPTIMIZED:
            self.decompression = 'GPU (optimized)'
        elif support & dx.DSTORAGE_COMPRESSION_SUPPORT_GPU_FALLBACK:
            self.decompression = 'GPU (compute shader fallback)'
        else:
            self.decompression = 'CPU fallback'
        print('GDeflate decompression on the', self.decompression)

    def load(self):
        texture = self.gpu.texture()
        start = time.perf_counter()
        for i, (offset, size) in enumerate(self.table):
            request = dx.DSTORAGE_REQUEST(UncompressedSize=CHUNK_BYTES)
            request.Options.CompressionFormat = dx.DSTORAGE_COMPRESSION_FORMAT_GDEFLATE
            request.Options.SourceType = dx.DSTORAGE_REQUEST_SOURCE_FILE
            request.Options.DestinationType = dx.DSTORAGE_REQUEST_DESTINATION_TEXTURE_REGION
            request.Source.File = dx.DSTORAGE_SOURCE_FILE(Source=self.file, Offset=offset, Size=size)
            request.Destination.Texture = dx.DSTORAGE_DESTINATION_TEXTURE_REGION(
                Resource=texture, SubresourceIndex=0,
                Region=dx.D3D12_BOX(0, i * CHUNK_ROWS, 0, SIZE, (i + 1) * CHUNK_ROWS, 1))
            self.queue.EnqueueRequest(request)
        # the fence is signaled once every request before it has landed in GPU memory
        self.gpu.fence_value += 1
        self.queue.EnqueueSignal(self.gpu.fence, self.gpu.fence_value)
        self.queue.Submit()
        self.gpu.fence.SetEventOnCompletion(self.gpu.fence_value, None)
        elapsed = time.perf_counter() - start
        errors = self.queue.RetrieveErrorRecord()
        if errors.FailureCount:
            raise dx.DXError(errors.FirstFailure.HResult, function='DirectStorage request')
        return texture, elapsed


class CpuLoader:
    """The classic path: read the file, decompress on the CPU, upload, copy."""

    def __init__(self, gpu, path, codec):
        self.gpu, self.path, self.codec = gpu, path, codec
        self.table = read_table(path)
        self.upload = gpu.buffer(SIZE * SIZE * 4, dx.D3D12_HEAP_TYPE_UPLOAD, dx.D3D12_RESOURCE_STATE_GENERIC_READ)

    def load(self):
        texture = self.gpu.texture()
        start = time.perf_counter()
        with open(self.path, 'rb') as f:
            data = f.read()
        address = self.upload.Map(0)
        written = ctypes.c_size_t()
        for i, (offset, size) in enumerate(self.table):
            chunk = numpy.frombuffer(data, numpy.uint8, size, offset)
            # rows are 32768 bytes, already the footprint's row pitch: decompress in place in the upload heap
            self.codec.DecompressBuffer(chunk.ctypes.data, size, address + i * CHUNK_BYTES, CHUNK_BYTES,
                                        ctypes.byref(written))
        self.upload.Unmap(0)
        placed, whole = self.gpu.texture_copy_locations(texture, self.upload)
        self.gpu.run(lambda cl: cl.CopyTextureRegion(whole, 0, 0, 0, placed, None))
        return texture, time.perf_counter() - start


def check(gpu, texture, path, codec):
    """Read the whole texture back and compare it with the decompressed file."""
    readback = gpu.buffer(SIZE * SIZE * 4, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
    placed, whole = gpu.texture_copy_locations(texture, readback)
    gpu.run(lambda cl: cl.CopyTextureRegion(placed, 0, 0, 0, whole, None))
    gpu_pixels = numpy.ctypeslib.as_array((ctypes.c_ubyte * (SIZE * SIZE * 4)).from_address(readback.Map(0)))
    with open(path, 'rb') as f:
        data = f.read()
    expected = numpy.empty(CHUNK_BYTES, numpy.uint8)
    written = ctypes.c_size_t()
    for i, (offset, size) in enumerate(read_table(path)):
        chunk = numpy.frombuffer(data, numpy.uint8, size, offset)
        codec.DecompressBuffer(chunk.ctypes.data, size, expected.ctypes.data, CHUNK_BYTES, ctypes.byref(written))
        if not numpy.array_equal(gpu_pixels[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES], expected):
            raise SystemExit('chunk %d differs' % i)
    readback.Unmap(0)
    print('check: all %d MB on the GPU match the source data' % (SIZE * SIZE * 4 >> 20))


def report(name, seconds):
    return '%s %.0f ms (%.1f GB/s)' % (name, seconds * 1000, SIZE * SIZE * 4 / seconds / 1e9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dstorage', help='folder containing dstorage.dll and dstoragecore.dll')
    ap.add_argument('--cache', default=os.path.join(tempfile.gettempdir(), 'pydx12_directstorage_8k.gdeflate'))
    ap.add_argument('--rebake', action='store_true', help='generate and compress the texture again')
    ap.add_argument('--check', action='store_true', help='verify the loaded texture against the source data')
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames')
    ap.add_argument('--debug', action='store_true', help='enable the D3D12 debug layer and report its errors')
    args = ap.parse_args()
    if args.debug:
        dx.D3D12GetDebugInterface().EnableDebugLayer()

    folder = args.dstorage
    if folder is None:  # a checkout with the NuGet package extracted in .deps/
        found = glob.glob(os.path.join(os.path.dirname(__file__), '..', '.deps', 'directstorage-*', 'pkg', 'native',
                                       'bin', 'x64'))
        folder = sorted(found)[-1] if found else None
    if folder:
        os.add_dll_directory(os.path.abspath(folder))

    root = tkinter.Tk()
    root.title('pydx12: DirectStorage')
    view = tkinter.Frame(root, width=VIEW_W, height=VIEW_H)
    view.pack()
    root.resizable(False, False)
    root.update()

    gpu = Gpu(view.winfo_id())
    codec = dx.DStorageCreateCompressionCodec(dx.DSTORAGE_COMPRESSION_FORMAT_GDEFLATE, os.cpu_count() or 4,
                                              dx.IDStorageCompressionCodec)
    if args.rebake or not os.path.exists(args.cache) or read_table(args.cache) is None:
        bake(args.cache, gpu, codec)
    ds = DirectStorageLoader(gpu, args.cache)
    cpu = CpuLoader(gpu, args.cache, codec)

    ds.load()  # warm up: first use creates DirectStorage's worker threads and GPU decompression resources
    texture, ds_time = ds.load()
    print(report('DirectStorage, GDeflate on the %s:' % ds.decompression, ds_time))
    cpu_texture, cpu_time = cpu.load()
    print(report('Python read + CPU GDeflate + upload:', cpu_time))
    del cpu_texture
    if args.check:
        check(gpu, texture, args.cache, codec)

    start_x = int(((START[0] - CENTER[0]) / SPAN + 0.5) * SIZE) - VIEW_W // 2
    start_y = int((0.5 - (START[1] - CENTER[1]) / SPAN) * SIZE) - VIEW_H // 2
    state = {'x': start_x, 'y': start_y, 'drag': None, 'closed': False,
             'status': report('DirectStorage', ds_time) + ' | ' + report('CPU path', cpu_time)}

    def clamp():
        state['x'] = int(min(max(state['x'], 0), SIZE - VIEW_W))
        state['y'] = int(min(max(state['y'], 0), SIZE - VIEW_H))

    def on_press(event):
        state['drag'] = (event.x, event.y)

    def on_drag(event):
        px, py = state['drag']
        state['x'] -= event.x - px
        state['y'] -= event.y - py
        state['drag'] = (event.x, event.y)
        clamp()

    def on_key(event):
        nonlocal texture
        step = 256
        moves = {'Left': (-step, 0), 'Right': (step, 0), 'Up': (0, -step), 'Down': (0, step)}
        if event.keysym in moves:
            state['x'] += moves[event.keysym][0]
            state['y'] += moves[event.keysym][1]
            clamp()
        elif event.keysym in ('r', 'R'):
            texture, seconds = ds.load()
            state['status'] = report('reloaded with DirectStorage in', seconds)
        elif event.keysym in ('c', 'C'):
            texture, seconds = cpu.load()
            state['status'] = report('reloaded with the CPU path in', seconds)
        elif event.keysym == 'Escape':
            state['closed'] = True

    view.bind('<ButtonPress-1>', on_press)
    view.bind('<B1-Motion>', on_drag)
    root.bind('<Key>', on_key)
    root.protocol('WM_DELETE_WINDOW', lambda: state.update(closed=True))

    frames = 0
    clamp()
    while not state['closed'] and (not args.frames or frames < args.frames):
        root.update()
        root.title('pydx12: DirectStorage - 8192x8192 at (%d, %d) - %s - drag/arrows to pan, R/C to reload' % (
            state['x'], state['y'], state['status']))
        gpu.present_view(texture, state['x'], state['y'])
        frames += 1
    gpu.wait()
    root.destroy()
    if args.debug:
        info = dx.ID3D12InfoQueue(gpu.device)
        errors = 0
        for i in range(info.GetNumStoredMessages()):
            size = ctypes.c_size_t()
            info.GetMessage(i, None, ctypes.byref(size))
            message = ctypes.cast(ctypes.create_string_buffer(size.value), ctypes.POINTER(dx.D3D12_MESSAGE))
            info.GetMessage(i, message, ctypes.byref(size))
            if message[0].Severity <= dx.D3D12_MESSAGE_SEVERITY_ERROR:
                errors += 1
                print(message[0].pDescription)
        print('debug layer errors: %d' % errors)


if __name__ == '__main__':
    main()
