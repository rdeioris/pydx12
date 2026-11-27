"""Work graphs: the GPU schedules its own work, drawing the Mandelbrot set by adaptive subdivision.

A work graph is a set of shaders (nodes) that send records to each other. The GPU runs a node as soon as
records for it exist: no CPU round trips, no barriers between passes, no buffers sized for the worst case.

This graph draws the set with the Mariani-Silver algorithm, 3x3 supersampled (3840x2160 samples averaged
down to the 1280x720 window):

- Root (thread launch, the entry): turns each 256x256 tile corner sent by the CPU into a Tile record.
- Tile (broadcasting, recursive, dynamic grid): one thread per sample on the tile's border. The thread
  groups fold their lowest and highest iteration counts into the shared input record, and the last group
  to finish (FinishedCrossGroupSharing) decides: if the whole border has the same count, the tile is
  flat and goes to Fill; otherwise it splits into four and sends the quarters back to itself, down to 8x8
  tiles, which compute their inside directly.
- Fill (broadcasting, dynamic grid): paints a flat tile with one color, launching as many thread groups
  as the tile needs (SV_DispatchGrid in the record).

The black inside of the set, where every sample would cost the maximum number of iterations, and the wide
color bands are filled without being iterated. B switches to a plain compute shader that iterates every
sample, and the title compares the two with GPU timestamps: the work graph wins where the picture is
expensive (the whole set, seahorse valley) and loses where it is cheap anyway. A flat border with a
different island inside is the known limit of the algorithm: a tiny copy of the set can be painted over.

Mouse: drag to pan, wheel to zoom. Keys: T shows the tiles (filled ones in blue), B brute force compute,
Space auto zoom, Escape quits.

Needs Shader Model 6.8 and work graphs tier 1.0: NVIDIA RTX 30 or newer, AMD RX 7000 or newer, a recent
driver and a recent Windows 11 (the D3D12 runtime in the box has work graphs since 24H2).

Usage: python examples/workgraph.py [--iterations 4096] [--view X Y SCALE] [--overlay] [--brute]
                                    [--frames N] [--screenshot out.png] [--debug]
"""
import argparse
import ctypes
import math
import time
import tkinter

import numpy

import pydx12 as dx

WIDTH, HEIGHT = 1280, 720
SS = 3  # samples per pixel along each axis: the set is rendered at 3840x2160 and averaged down
SAMPLES_W, SAMPLES_H = WIDTH * SS, HEIGHT * SS
TILE = 256  # root tiles, in samples, sent by the CPU
LEAF = 8    # tiles this small compute all their samples
DEPTH = int(math.log2(TILE // LEAF))  # how many times a tile can split
TARGET = (-0.743643887037151, 0.131825904205330)  # the auto zoom dives into seahorse valley
MIN_SCALE = 1e-6  # complex plane units per pixel where float32 runs out of precision

SHADERS = r'''
#define TILE %(tile)d
#define LEAF %(leaf)d

#define SS %(ss)d

RWTexture2D<unorm float4> Samples : register(u0);  // SS x SS samples per pixel
RWTexture2D<unorm float4> Output : register(u1);
RWByteAddressBuffer Stats : register(u2);          // samples evaluated, tiles, flat tiles

cbuffer View : register(b0)
{
    float2 center;
    float scale;           // complex plane units per sample
    uint maxIterations;
    uint2 screen;          // in samples
    uint overlay;
};

uint Iterate(uint2 pixel)
{
    float2 c = center + (float2(pixel) + 0.5 - float2(screen) * 0.5) * float2(scale, -scale);
    float2 z = 0;
    uint i = 0;
    for (; i < maxIterations && dot(z, z) < 4; i++)
        z = float2(z.x * z.x - z.y * z.y, 2 * z.x * z.y) + c;
    return i;
}

float3 Color(uint i)
{
    if (i >= maxIterations)
        return float3(0.01, 0.01, 0.02);
    float t = sqrt(float(i)) * 0.22;
    return (0.5 + 0.5 * cos(6.28318 * (t + float3(0.0, 0.1, 0.2)))) * saturate(i / 6.0);
}

// a tile launches one thread per border pixel; its thread groups share the record and fold their lowest
// and highest iteration counts into it, and the last group to finish decides what happens next
struct [NodeTrackRWInputSharing] TileRecord
{
    uint grid : SV_DispatchGrid;  // ceil(4 * (size - 1) / 64) thread groups
    uint2 origin;
    uint size;
    uint low;                     // starts at 0xffffffff
    uint high;                    // starts at 0
};

struct FillRecord
{
    uint2 grid : SV_DispatchGrid;  // one thread group per 8x8 pixels
    uint2 origin;
    uint size;
    uint iterations;
};

uint BorderGroups(uint size)
{
    return (4 * (size - 1) + 63) / 64;
}

// the entry: one thread per root tile sent by the CPU (entry nodes cannot share records across groups,
// so this one only turns the CPU's tile corners into Tile records)
struct RootRecord
{
    uint2 corner;
};

[Shader("node")]
[NodeLaunch("thread")]
void Root(ThreadNodeInputRecord<RootRecord> root, [MaxRecords(1)] [NodeID("Tile")] NodeOutput<TileRecord> tiles)
{
    ThreadNodeOutputRecords<TileRecord> tile = tiles.GetThreadNodeOutputRecords(1);
    tile.Get().grid = BorderGroups(TILE);
    tile.Get().origin = root.Get().corner;
    tile.Get().size = TILE;
    tile.Get().low = 0xffffffff;
    tile.Get().high = 0;
    tile.OutputComplete();
}

[Shader("node")]
[NodeLaunch("broadcasting")]
[NodeMaxDispatchGrid(%(border_groups)d, 1, 1)]
[NumThreads(64, 1, 1)]
[NodeMaxRecursionDepth(%(depth)d)]
void Tile(globallycoherent RWDispatchNodeInputRecord<TileRecord> input, uint k : SV_DispatchThreadID,
          uint thread : SV_GroupIndex,
          [MaxRecords(4)] [NodeID("Tile")] NodeOutput<TileRecord> quarters,
          [MaxRecords(1)] [NodeID("Fill")] NodeOutput<FillRecord> fill)
{
    uint2 origin = input.Get().origin;
    uint size = input.Get().size;

    // this thread's border pixel, clockwise from the top left corner
    uint side = size - 1, low = 0xffffffff, high = 0, evaluated = 0;
    if (k < 4 * side)
    {
        uint s = k / side, t = k %% side;
        uint2 p = origin + (s == 0 ? uint2(t, 0) : s == 1 ? uint2(side, t) :
                            s == 2 ? uint2(side - t, side) : uint2(0, side - t));
        uint n = Iterate(p);
        low = high = n;
        if (all(p < screen))
        {
            Samples[p] = float4(Color(n), 1);
            evaluated = 1;
        }
    }
    low = WaveActiveMin(low);
    high = WaveActiveMax(high);
    evaluated = WaveActiveSum(evaluated);
    if (WaveIsFirstLane())
    {
        InterlockedMin(input.Get().low, low);
        InterlockedMax(input.Get().high, high);
        Stats.InterlockedAdd(0, evaluated);
    }
    Barrier(UAV_MEMORY | NODE_INPUT_MEMORY, DEVICE_SCOPE | GROUP_SYNC);
    if (!input.FinishedCrossGroupSharing())
        return;  // not the last group: its part of the border is done

    // the last group: the whole border is known
    low = input.Get().low;
    high = input.Get().high;
    bool flat = low == high;
    bool split = !flat && size > LEAF;

    // flat: one record for Fill, which launches (size / 8)^2 thread groups
    GroupNodeOutputRecords<FillRecord> painting = fill.GetGroupNodeOutputRecords(flat ? 1 : 0);
    if (flat && thread == 0)
    {
        painting.Get().grid = size / 8;
        painting.Get().origin = origin;
        painting.Get().size = size;
        painting.Get().iterations = low;
    }
    painting.OutputComplete();

    // not flat: up to four quarters back to this node, skipping the ones outside the screen
    uint halfSize = size / 2, count = 0;
    for (uint q = 0; q < 4; q++)
        count += split && all(origin + uint2(q & 1, q >> 1) * halfSize < screen) ? 1 : 0;
    GroupNodeOutputRecords<TileRecord> children = quarters.GetGroupNodeOutputRecords(count);
    if (thread < 4)
    {
        uint2 corner = origin + uint2(thread & 1, thread >> 1) * halfSize;
        bool visible = split && all(corner < screen);
        uint index = WavePrefixCountBits(visible);
        if (visible)
        {
            children[index].grid = BorderGroups(halfSize);
            children[index].origin = corner;
            children[index].size = halfSize;
            children[index].low = 0xffffffff;
            children[index].high = 0;
        }
    }
    children.OutputComplete();

    // a leaf that is not flat computes its inside, one pixel per thread
    if (!flat && !split)
    {
        uint inside = size - 2;
        evaluated = 0;
        for (uint i = thread; i < inside * inside; i += 64)
        {
            uint2 p = origin + 1 + uint2(i %% inside, i / inside);
            if (all(p < screen))
            {
                Samples[p] = float4(Color(Iterate(p)), 1);
                evaluated++;
            }
        }
        evaluated = WaveActiveSum(evaluated);
        if (WaveIsFirstLane())
            Stats.InterlockedAdd(0, evaluated);
    }
    if (thread == 0)
    {
        Stats.InterlockedAdd(4, 1);
        Stats.InterlockedAdd(8, flat ? 1 : 0);
    }
}

[Shader("node")]
[NodeLaunch("broadcasting")]
[NodeMaxDispatchGrid(TILE / 8, TILE / 8, 1)]
[NumThreads(8, 8, 1)]
void Fill(DispatchNodeInputRecord<FillRecord> input, uint2 id : SV_DispatchThreadID)
{
    FillRecord tile = input.Get();
    uint2 p = tile.origin + id;
    if (any(p >= screen))
        return;
    float3 color = Color(tile.iterations);
    if (overlay)
    {
        color = lerp(color, float3(0.1, 0.3, 1.0), 0.45);
        if (id.x < SS || id.y < SS)
            color = 0.9;
    }
    Samples[p] = float4(color, 1);
}

#ifdef COMPUTE
// the same picture without a work graph: every sample iterated
[numthreads(8, 8, 1)]
void Brute(uint2 p : SV_DispatchThreadID)
{
    if (all(p < screen))
        Samples[p] = float4(Color(Iterate(p)), 1);
}

// average the SS x SS samples of each pixel
[numthreads(8, 8, 1)]
void Resolve(uint2 p : SV_DispatchThreadID)
{
    if (any(p * SS >= screen))
        return;
    float4 sum = 0;
    for (uint y = 0; y < SS; y++)
        for (uint x = 0; x < SS; x++)
            sum += Samples[p * SS + uint2(x, y)];
    Output[p] = sum / (SS * SS);
}
#endif
''' % {'tile': TILE, 'leaf': LEAF, 'depth': DEPTH, 'ss': SS, 'border_groups': (4 * (TILE - 1) + 63) // 64}


def compile_shader(source, target, entry=None):
    compiler = dx.DxcCreateInstance(dx.CLSID_DxcCompiler, dx.IDxcCompiler3)
    arguments = ['-T', target, '-O3'] + (['-E', entry, '-D', 'COMPUTE'] if entry else [])
    result = compiler.Compile(dx.DxcBuffer(Ptr=source.encode('utf-8')), arguments, None, dx.IDxcResult)
    if result.GetStatus() < 0:
        errors = result.GetOutput(dx.DXC_OUT_ERRORS, dx.IDxcBlobUtf8)[0]
        raise SystemExit(bytes(errors).decode('utf-8', 'replace') if errors else 'shader compilation failed')
    blob = result.GetOutput(dx.DXC_OUT_OBJECT, dx.IDxcBlob)[0]
    assert blob is not None
    return blob


def transition(resource, before, after):
    b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    b.Transition = dx.D3D12_RESOURCE_TRANSITION_BARRIER(pResource=resource, StateBefore=before, StateAfter=after,
                                                        Subresource=dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
    return b


class Renderer:
    def __init__(self, hwnd):
        factory = dx.CreateDXGIFactory2()
        adapter = factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)
        self.device = dx.D3D12CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_0, dx.ID3D12Device5)
        device = self.device
        options = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS21()
        device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS21, ctypes.byref(options), ctypes.sizeof(options))
        model = dx.D3D12_FEATURE_DATA_SHADER_MODEL(HighestShaderModel=dx.D3D_SHADER_MODEL_6_8)
        device.CheckFeatureSupport(dx.D3D12_FEATURE_SHADER_MODEL, ctypes.byref(model), ctypes.sizeof(model))
        if options.WorkGraphsTier < dx.D3D12_WORK_GRAPHS_TIER_1_0 or model.HighestShaderModel < dx.D3D_SHADER_MODEL_6_8:
            raise SystemExit('this GPU or driver has no work graphs support')
        print('%s: work graphs tier %d.%d' % ((adapter.GetDesc1().Description,) + divmod(options.WorkGraphsTier, 10)))

        self.queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
        self.allocator = device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
        self.cl = dx.ID3D12GraphicsCommandList10(
            device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, self.allocator))
        self.cl.Close()
        self.fence = device.CreateFence()
        self.fence_value = 0
        desc = dx.DXGI_SWAP_CHAIN_DESC1(Width=WIDTH, Height=HEIGHT, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                        BufferUsage=dx.DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=2,
                                        SwapEffect=dx.DXGI_SWAP_EFFECT_FLIP_DISCARD)
        desc.SampleDesc.Count = 1
        self.swap_chain = dx.IDXGISwapChain3(factory.CreateSwapChainForHwnd(self.queue, hwnd, desc))
        self.back_buffers = [self.swap_chain.GetBuffer(i) for i in range(2)]

        self.create_resources()
        self.create_programs()

    def buffer(self, size, heap=dx.D3D12_HEAP_TYPE_DEFAULT, state=dx.D3D12_RESOURCE_STATE_COMMON,
               flags=dx.D3D12_RESOURCE_FLAG_NONE):
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                                      DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR,
                                      Flags=flags)
        desc.SampleDesc.Count = 1
        return self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=heap), dx.D3D12_HEAP_FLAG_NONE,
                                                   desc, state)

    def create_resources(self):
        device = self.device
        self.heap = device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
            Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, NumDescriptors=2,
            Flags=dx.D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE))
        step = device.GetDescriptorHandleIncrementSize(dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)
        start = self.heap.GetCPUDescriptorHandleForHeapStart().ptr
        self.textures = []
        for i, (width, height) in enumerate(((SAMPLES_W, SAMPLES_H), (WIDTH, HEIGHT))):
            desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=width,
                                          Height=height, DepthOrArraySize=1, MipLevels=1,
                                          Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                          Flags=dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
            desc.SampleDesc.Count = 1
            texture = device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                                     dx.D3D12_HEAP_FLAG_NONE, desc,
                                                     dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)
            device.CreateUnorderedAccessView(texture, None, dx.D3D12_UNORDERED_ACCESS_VIEW_DESC(
                Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM, ViewDimension=dx.D3D12_UAV_DIMENSION_TEXTURE2D),
                dx.D3D12_CPU_DESCRIPTOR_HANDLE(start + i * step))
            self.textures.append(texture)
        self.samples, self.output = self.textures

        # statistics: cleared from a zeroed upload buffer and read back every frame
        self.stats = self.buffer(16, flags=dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)  # promoted to copy dest
        self.zeros = self.buffer(16, dx.D3D12_HEAP_TYPE_UPLOAD, dx.D3D12_RESOURCE_STATE_GENERIC_READ)
        ctypes.memset(self.zeros.Map(0), 0, 16)
        self.stats_readback = self.buffer(16, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)

        # two timestamps around the dispatch
        self.timestamps = device.CreateQueryHeap(dx.D3D12_QUERY_HEAP_DESC(Type=dx.D3D12_QUERY_HEAP_TYPE_TIMESTAMP,
                                                                          Count=2))
        self.timestamp_readback = self.buffer(16, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        self.ticks = self.queue.GetTimestampFrequency()

    def create_programs(self):
        device = self.device
        table = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE)
        table.DescriptorTable = dx.D3D12_ROOT_DESCRIPTOR_TABLE1(pDescriptorRanges=[dx.D3D12_DESCRIPTOR_RANGE1(
            RangeType=dx.D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=2, BaseShaderRegister=0)])
        constants = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS)
        constants.Constants = dx.D3D12_ROOT_CONSTANTS(ShaderRegister=0, Num32BitValues=8)
        stats = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_UAV,
                                         Descriptor=dx.D3D12_ROOT_DESCRIPTOR1(ShaderRegister=2))
        versioned = dx.D3D12_VERSIONED_ROOT_SIGNATURE_DESC(Version=dx.D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned.Desc_1_1 = dx.D3D12_ROOT_SIGNATURE_DESC1(pParameters=[constants, table, stats])
        self.root = device.CreateRootSignature(0, dx.D3D12SerializeVersionedRootSignature(versioned))

        # the work graph: a DXIL library, the global root signature and a program made of all its nodes
        library = compile_shader(SHADERS, 'lib_6_8')
        self.subobject_descs = [  # each subobject's pDesc points to a struct that must stay alive
            (dx.D3D12_STATE_SUBOBJECT_TYPE_DXIL_LIBRARY,
             dx.D3D12_DXIL_LIBRARY_DESC(DXILLibrary=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=library))),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_GLOBAL_ROOT_SIGNATURE,
             dx.D3D12_GLOBAL_ROOT_SIGNATURE(pGlobalRootSignature=self.root)),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_WORK_GRAPH,
             dx.D3D12_WORK_GRAPH_DESC(ProgramName='Mandelbrot',  # the nodes are found in the library
                                      Flags=dx.D3D12_WORK_GRAPH_FLAG_INCLUDE_ALL_AVAILABLE_NODES)),
        ]
        self.state_object = device.CreateStateObject(dx.D3D12_STATE_OBJECT_DESC(
            Type=dx.D3D12_STATE_OBJECT_TYPE_EXECUTABLE,
            pSubobjects=[dx.D3D12_STATE_SUBOBJECT(Type=kind, pDesc=ctypes.addressof(desc))
                         for kind, desc in self.subobject_descs]))

        # the graph needs backing memory for the records in flight; the runtime says how much
        graph = dx.ID3D12WorkGraphProperties(self.state_object)
        index = graph.GetWorkGraphIndex('Mandelbrot')
        self.entry = graph.GetEntrypointIndex(index, dx.D3D12_NODE_ID(Name='Root'))
        memory = graph.GetWorkGraphMemoryRequirements(index)
        self.backing = self.buffer(memory.MaxSizeInBytes, flags=dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
        print('work graph: %d nodes, %d entry point, %.1f MB of backing memory' % (
            graph.GetNumNodes(index), graph.GetNumEntrypoints(index), memory.MaxSizeInBytes / 2**20))
        self.program = dx.D3D12_SET_PROGRAM_DESC(Type=dx.D3D12_PROGRAM_TYPE_WORK_GRAPH)
        self.program.WorkGraph = dx.D3D12_SET_WORK_GRAPH_DESC(
            ProgramIdentifier=dx.ID3D12StateObjectProperties1(self.state_object).GetProgramIdentifier('Mandelbrot'),
            Flags=dx.D3D12_SET_WORK_GRAPH_FLAG_INITIALIZE,  # only the first time the memory is used
            BackingMemory=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE(StartAddress=self.backing.GetGPUVirtualAddress(),
                                                             SizeInBytes=memory.MaxSizeInBytes))

        # the corners of the root tiles, sent to Root with every DispatchGraph
        self.records = numpy.array([(x, y) for y in range(0, SAMPLES_H, TILE) for x in range(0, SAMPLES_W, TILE)],
                                   numpy.uint32)

        # brute force and the resolve: ordinary compute pipelines on the same root signature
        self.brute, self.resolve = [device.CreateComputePipelineState(dx.D3D12_COMPUTE_PIPELINE_STATE_DESC(
            pRootSignature=self.root,
            CS=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=compile_shader(SHADERS, 'cs_6_8', entry))))
            for entry in ('Brute', 'Resolve')]

    def wait(self):
        self.fence_value += 1
        self.queue.Signal(self.fence, self.fence_value)
        self.fence.SetEventOnCompletion(self.fence_value, None)

    def render(self, constants, brute):
        """Draw a frame and return (GPU milliseconds, pixels evaluated, tiles, uniform tiles)."""
        back_buffer = self.back_buffers[self.swap_chain.GetCurrentBackBufferIndex()]
        cl = self.cl
        self.allocator.Reset()
        cl.Reset(self.allocator)
        cl.CopyBufferRegion(self.stats, 0, self.zeros, 0, 16)
        cl.ResourceBarrier([transition(self.stats, dx.D3D12_RESOURCE_STATE_COPY_DEST,
                                       dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
        cl.SetComputeRootSignature(self.root)
        cl.SetDescriptorHeaps([self.heap])
        cl.SetComputeRoot32BitConstants(0, len(constants), constants, 0)
        cl.SetComputeRootDescriptorTable(1, self.heap.GetGPUDescriptorHandleForHeapStart())
        cl.SetComputeRootUnorderedAccessView(2, self.stats.GetGPUVirtualAddress())
        cl.EndQuery(self.timestamps, dx.D3D12_QUERY_TYPE_TIMESTAMP, 0)
        if brute:
            cl.SetPipelineState(self.brute)
            cl.Dispatch((SAMPLES_W + 7) // 8, (SAMPLES_H + 7) // 8, 1)
        else:
            cl.SetProgram(self.program)
            self.program.WorkGraph.Flags = dx.D3D12_SET_WORK_GRAPH_FLAG_NONE
            dispatch = dx.D3D12_DISPATCH_GRAPH_DESC(Mode=dx.D3D12_DISPATCH_MODE_NODE_CPU_INPUT)
            dispatch.NodeCPUInput = dx.D3D12_NODE_CPU_INPUT(  # the records are copied into the command list
                EntrypointIndex=self.entry, NumRecords=len(self.records), pRecords=self.records.ctypes.data,
                RecordStrideInBytes=self.records.strides[0])
            cl.DispatchGraph(dispatch)
        cl.EndQuery(self.timestamps, dx.D3D12_QUERY_TYPE_TIMESTAMP, 1)
        cl.ResolveQueryData(self.timestamps, dx.D3D12_QUERY_TYPE_TIMESTAMP, 0, 2, self.timestamp_readback, 0)
        uav = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_UAV)
        uav.UAV = dx.D3D12_RESOURCE_UAV_BARRIER(pResource=self.samples)
        cl.ResourceBarrier([uav])
        cl.SetPipelineState(self.resolve)
        cl.Dispatch((WIDTH + 7) // 8, (HEIGHT + 7) // 8, 1)

        cl.ResourceBarrier([
            transition(self.stats, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS, dx.D3D12_RESOURCE_STATE_COPY_SOURCE),
            transition(self.output, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS, dx.D3D12_RESOURCE_STATE_COPY_SOURCE),
            transition(back_buffer, dx.D3D12_RESOURCE_STATE_PRESENT, dx.D3D12_RESOURCE_STATE_COPY_DEST)])
        cl.CopyBufferRegion(self.stats_readback, 0, self.stats, 0, 16)
        cl.CopyResource(back_buffer, self.output)
        cl.ResourceBarrier([
            transition(self.stats, dx.D3D12_RESOURCE_STATE_COPY_SOURCE, dx.D3D12_RESOURCE_STATE_COPY_DEST),
            transition(self.output, dx.D3D12_RESOURCE_STATE_COPY_SOURCE, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
            transition(back_buffer, dx.D3D12_RESOURCE_STATE_COPY_DEST, dx.D3D12_RESOURCE_STATE_PRESENT)])
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        self.swap_chain.Present(1, 0)
        self.wait()

        start, end = numpy.frombuffer(ctypes.string_at(self.timestamp_readback.Map(0), 16), numpy.uint64)
        self.timestamp_readback.Unmap(0)
        evaluated, tiles, uniform, _ = numpy.frombuffer(ctypes.string_at(self.stats_readback.Map(0), 16), numpy.uint32)
        self.stats_readback.Unmap(0)
        if brute:
            evaluated = SAMPLES_W * SAMPLES_H
        return (int(end) - int(start)) * 1000.0 / self.ticks, int(evaluated), int(tiles), int(uniform)

    def save(self, path):
        from PIL import Image
        footprints, _, _, total = self.device.GetCopyableFootprints(self.output.GetDesc(), 0, 1, 0)
        readback = self.buffer(total, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        cl = self.cl
        self.allocator.Reset()
        cl.Reset(self.allocator)
        cl.ResourceBarrier([transition(self.output, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                       dx.D3D12_RESOURCE_STATE_COPY_SOURCE)])
        dst = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=readback, Type=dx.D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT)
        dst.PlacedFootprint = footprints[0]
        src = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=self.output, Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX)
        cl.CopyTextureRegion(dst, 0, 0, 0, src, None)
        cl.ResourceBarrier([transition(self.output, dx.D3D12_RESOURCE_STATE_COPY_SOURCE,
                                       dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        self.wait()
        pitch = footprints[0].Footprint.RowPitch
        data = ctypes.string_at(readback.Map(0), total)
        readback.Unmap(0)
        rows = b''.join(data[y * pitch:y * pitch + WIDTH * 4] for y in range(HEIGHT))
        Image.frombytes('RGBA', (WIDTH, HEIGHT), rows).convert('RGB').save(path)
        print('saved', path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iterations', type=int, default=4096, help='maximum iterations per pixel')
    ap.add_argument('--view', type=float, nargs=3, metavar=('X', 'Y', 'SCALE'),
                    help='start still on this point, SCALE complex plane units per pixel')
    ap.add_argument('--overlay', action='store_true', help='start with the tiles shown (T toggles them)')
    ap.add_argument('--brute', action='store_true', help='start with the brute force compute shader (B)')
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames')
    ap.add_argument('--screenshot', help='save the last frame to this PNG')
    ap.add_argument('--debug', action='store_true', help='enable the D3D12 debug layer and report its errors')
    args = ap.parse_args()
    if args.debug:
        dx.D3D12GetDebugInterface().EnableDebugLayer()

    root = tkinter.Tk()
    root.title('pydx12: work graphs')
    view = tkinter.Frame(root, width=WIDTH, height=HEIGHT)
    view.pack()
    root.resizable(False, False)
    root.update()
    renderer = Renderer(view.winfo_id())

    home = (-0.65, 0.0, 3.2 / HEIGHT)
    x, y, scale = args.view if args.view else home
    state: dict = {'x': x, 'y': y, 'scale': scale, 'drag': None, 'overlay': args.overlay, 'brute': args.brute,
                   'auto': not args.view, 'zoom_in': True, 'closed': False}

    def on_drag(event):
        if state['drag']:
            state['x'] -= (event.x - state['drag'][0]) * state['scale']
            state['y'] += (event.y - state['drag'][1]) * state['scale']
            state['auto'] = False
        state['drag'] = (event.x, event.y)

    def on_wheel(event):
        # zoom around the point under the mouse
        px = state['x'] + (event.x - WIDTH / 2) * state['scale']
        py = state['y'] - (event.y - HEIGHT / 2) * state['scale']
        factor = 0.8 if event.delta > 0 else 1.25
        state['scale'] = min(home[2] * 2, max(MIN_SCALE, state['scale'] * factor))
        state['x'] = px - (event.x - WIDTH / 2) * state['scale']
        state['y'] = py + (event.y - HEIGHT / 2) * state['scale']
        state['auto'] = False

    def on_key(event):
        key = event.keysym.lower()
        if key == 't':
            state['overlay'] = not state['overlay']
        elif key == 'b':
            state['brute'] = not state['brute']
        elif key == 'space':
            state['auto'] = not state['auto']
        elif key == 'escape':
            state['closed'] = True

    view.bind('<ButtonPress-1>', lambda e: state.update(drag=(e.x, e.y)))
    view.bind('<B1-Motion>', on_drag)
    view.bind('<MouseWheel>', on_wheel)
    root.bind('<MouseWheel>', on_wheel)
    root.bind('<Key>', on_key)
    root.protocol('WM_DELETE_WINDOW', lambda: state.update(closed=True))

    timings: dict = {False: [], True: []}
    frames, last = 0, time.perf_counter()
    while not state['closed'] and (not args.frames or frames < args.frames):
        root.update()
        now = time.perf_counter()
        if state['auto']:
            # glide toward the target and zoom in to the limit of float32, then back out
            step = min(now - last, 0.1)
            state['x'] += (TARGET[0] - state['x']) * min(1.0, step * 1.5)
            state['y'] += (TARGET[1] - state['y']) * min(1.0, step * 1.5)
            state['scale'] *= math.exp((-0.6 if state['zoom_in'] else 0.6) * step)
            if state['scale'] < MIN_SCALE * 1.5:
                state['zoom_in'] = False
            elif state['scale'] > home[2]:
                state['zoom_in'] = True
        last = now
        constants = numpy.zeros(8, numpy.uint32)
        constants.view(numpy.float32)[0:3] = state['x'], state['y'], state['scale'] / SS
        constants[3:7] = args.iterations, SAMPLES_W, SAMPLES_H, state['overlay']
        milliseconds, evaluated, tiles, uniform = renderer.render(constants, state['brute'])
        timings[state['brute']].append(milliseconds)
        frames += 1
        if frames % 10 == 0:
            if state['brute']:
                title = 'brute force compute: %.2f ms, every sample iterated' % milliseconds
            else:
                title = 'work graph: %.2f ms, %.1f%% of the samples iterated, %d tiles (%d filled)' % (
                    milliseconds, evaluated * 100.0 / (SAMPLES_W * SAMPLES_H), tiles, uniform)
            root.title('pydx12: %s - zoom %.0fx - T tiles, B brute force, Space auto zoom' % (
                title, home[2] / state['scale']))
    if args.screenshot:
        renderer.save(args.screenshot)
    for brute, samples in timings.items():
        if samples:
            print('%s: %d frames, %.2f ms average on the GPU' % (
                'brute force compute' if brute else 'work graph', len(samples), sum(samples) / len(samples)))
    if not state['brute'] and frames:
        print('last frame: %d of %d samples iterated (%.1f%%), %d tiles, %d filled' % (
            evaluated, SAMPLES_W * SAMPLES_H, evaluated * 100.0 / (SAMPLES_W * SAMPLES_H), tiles, uniform))
    if args.debug:
        info = dx.ID3D12InfoQueue(renderer.device)
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
    root.destroy()


if __name__ == '__main__':
    main()
