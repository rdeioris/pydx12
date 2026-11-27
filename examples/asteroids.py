"""Mesh shaders: an asteroid belt around a star, built entirely on the GPU.

There are no vertex or index buffers. A DirectX 12 Ultimate mesh shader pipeline makes everything:

- amplification shader: each thread group takes 32 asteroids, places them on their orbit, culls the ones
  outside the view frustum or too small to see, picks a level of detail by projected size and launches
  mesh shader groups only for what survives
- mesh shader: each group builds one asteroid (or half of a detailed one) from an icosphere template in
  group shared memory: every rock gets its own lumpy shape, stretch, tumble and color from a hash of its
  index, and flat shaded facets from per-primitive normals
- pixel shader: lit by the star at the center
- a full screen pass draws the star (ray traced in the pixel shader, writing depth so asteroids pass in
  front of and behind it), its glow and a starfield; 4x MSAA

Pipeline statistics queries show how many asteroids the amplification shaders let through, and V cycles
the variable rate shading of the asteroids (1x1, 2x2, 4x4).

Mouse: drag to orbit, wheel to zoom. Keys: V shading rate, Space pause, Escape quits.

Usage: python examples/asteroids.py [--count 50000] [--frames N] [--screenshot out.png] [--debug]
"""
import argparse
import ctypes
import math
import time
import tkinter

import numpy

import pydx12 as dx

WIDTH, HEIGHT = 1280, 720
SAMPLES = 4
GROUP = 32

SHADERS = r'''
cbuffer Frame : register(b0)
{
    row_major float4x4 viewProj;
    row_major float4x4 invViewProj;
    float4 planes[6];
    float3 cameraPos; float time;
    float2 screen; uint count; float pad;
};
StructuredBuffer<float3> Directions : register(t0);  // icosphere vertices on the unit sphere
StructuredBuffer<uint> Triangles : register(t1);     // 3 x 8 bit indices: 320 fine, then 80 coarse

#define GROUP 32
#define STAR_RADIUS 6.0
static const float3 STAR_COLOR = float3(1.0, 0.78, 0.5);

// ---- one asteroid, all from a hash of its index --------------------------------------------------
uint Hash(uint x)
{
    x ^= x >> 16; x *= 0x7feb352d; x ^= x >> 15; x *= 0x846ca68b; x ^= x >> 16;
    return x;
}
float Rand(inout uint state) { state = Hash(state); return state / 4294967296.0; }
float3 RandDir(inout uint state)
{
    float z = Rand(state) * 2 - 1, a = Rand(state) * 6.28318, r = sqrt(1 - z * z);
    return float3(r * cos(a), r * sin(a), z);
}

struct Asteroid
{
    float3 center; float size;
    float3 axis; float angle;
    float3 stretch; uint seed;
    float3 color;
};

Asteroid MakeAsteroid(uint index)
{
    uint s = index * 9781 + 1;
    Asteroid a;
    float radius = 30 + 85 * pow(Rand(s), 0.85);
    radius += 4 * sin(radius * 0.7);                       // ripples in the belt density
    float speed = 1.1 * pow(30 / radius, 1.5);              // Kepler: the inner belt is faster
    float angle = Rand(s) * 6.28318 + time * speed * 0.2;
    float height = (Rand(s) + Rand(s) + Rand(s) - 1.5) * 3.0 * radius / 60;
    a.center = float3(cos(angle) * radius, height, sin(angle) * radius);
    a.size = 0.05 + 1.1 * pow(Rand(s), 9);                 // mostly pebbles, a few big rocks
    a.axis = RandDir(s);
    a.angle = Rand(s) * 6.28318 + time * (Rand(s) - 0.5) * 2;
    a.stretch = float3(1 + Rand(s) * 0.6, 0.7 + Rand(s) * 0.3, 0.8 + Rand(s) * 0.4);
    a.seed = Hash(s);
    float tone = 0.55 + 0.45 * Rand(s);
    a.color = Rand(s) < 0.12 ? float3(0.55, 0.65, 0.75) * tone          // icy
                             : lerp(float3(0.42, 0.36, 0.3), float3(0.55, 0.45, 0.35), Rand(s)) * tone;
    return a;
}

float3 Rotate(float3 v, float3 axis, float angle)
{
    float c = cos(angle), s = sin(angle);
    return v * c + cross(axis, v) * s + axis * dot(axis, v) * (1 - c);
}

float Lumps(float3 d, uint seed)
{
    uint s = seed;
    float n = 0, amplitude = 0.22, frequency = 2.3;
    for (int octave = 0; octave < 3; octave++)
    {
        n += sin(dot(d, RandDir(s)) * frequency + Rand(s) * 6.28318) * amplitude;
        amplitude *= 0.5;
        frequency *= 2.1;
    }
    return 1 + n;
}

// ---- amplification shader: cull and choose the level of detail ---------------------------------
struct Payload { uint asteroid[GROUP * 2]; uint meshlet[GROUP * 2]; };
groupshared Payload payload;
groupshared uint emitted;

[numthreads(GROUP, 1, 1)]
void AS(uint thread : SV_GroupThreadID, uint group : SV_GroupID)
{
    if (thread == 0)
        emitted = 0;
    GroupMemoryBarrierWithGroupSync();
    uint index = group * GROUP + thread;
    if (index < count)
    {
        Asteroid a = MakeAsteroid(index);
        float bound = a.size * 1.9;
        bool visible = true;
        for (int i = 0; i < 6; i++)
            visible = visible && dot(planes[i].xyz, a.center) + planes[i].w > -bound;
        float projected = a.size / distance(a.center, cameraPos);  // roughly the size on screen
        visible = visible && projected > 0.0006;
        if (visible)
        {
            bool detailed = projected > 0.012;
            uint slot;
            InterlockedAdd(emitted, detailed ? 2 : 1, slot);
            payload.asteroid[slot] = index;
            payload.meshlet[slot] = detailed ? 0 : 2;
            if (detailed)
            {
                payload.asteroid[slot + 1] = index;
                payload.meshlet[slot + 1] = 1;
            }
        }
    }
    GroupMemoryBarrierWithGroupSync();
    DispatchMesh(emitted, 1, 1, payload);
}

// ---- mesh shader: build the rock -----------------------------------------------------------------
struct Vertex { float4 position : SV_Position; float3 world : POSITION; };
struct Primitive { float3 normal : NORMAL; float3 color : COLOR; };
groupshared float3 positions[162];

[numthreads(128, 1, 1)]
[outputtopology("triangle")]
void MS(uint thread : SV_GroupThreadID, uint group : SV_GroupID, in payload Payload p,
        out vertices Vertex verts[162], out indices uint3 tris[160], out primitives Primitive prims[160])
{
    uint meshlet = p.meshlet[group];
    bool coarse = meshlet == 2;                   // 42 vertices / 80 triangles, else half of 162 / 320
    uint vertexCount = coarse ? 42 : 162;
    uint triangleCount = coarse ? 80 : 160;
    uint firstTriangle = coarse ? 320 : meshlet * 160;
    SetMeshOutputCounts(vertexCount, triangleCount);

    Asteroid a = MakeAsteroid(p.asteroid[group]);
    for (uint v = thread; v < vertexCount; v += 128)
    {
        float3 d = Directions[v];
        float3 local = d * Lumps(d, a.seed) * a.stretch * a.size;
        float3 world = a.center + Rotate(local, a.axis, a.angle);
        positions[v] = world;
        verts[v].position = mul(float4(world, 1), viewProj);
        verts[v].world = world;
    }
    GroupMemoryBarrierWithGroupSync();
    for (uint t = thread; t < triangleCount; t += 128)
    {
        uint packed = Triangles[firstTriangle + t];
        uint3 i = uint3(packed & 255, (packed >> 8) & 255, (packed >> 16) & 255);
        tris[t] = i;
        float3 n = normalize(cross(positions[i.y] - positions[i.x], positions[i.z] - positions[i.x]));
        float3 middle = (positions[i.x] + positions[i.y] + positions[i.z]) / 3;
        prims[t].normal = dot(n, middle - a.center) < 0 ? -n : n;  // always pointing out of the rock
        prims[t].color = a.color;
    }
}

float3 Finish(float3 c)
{
    c = c / (1 + c);              // Reinhard tone mapping
    return pow(c, 1 / 2.2);       // the swapchain is not sRGB
}

float4 PS(Vertex v, Primitive p) : SV_Target
{
    float3 toStar = normalize(-v.world);
    float distanceFade = 4000 / dot(v.world, v.world);            // light falls off with distance
    float3 light = STAR_COLOR * 3.0 * saturate(dot(p.normal, toStar)) * saturate(distanceFade);
    float3 view = normalize(cameraPos - v.world);
    float rim = pow(1 - saturate(dot(p.normal, view)), 4) * saturate(dot(-view, toStar) + 0.3);
    float3 c = p.color * (light + 0.025 + rim * STAR_COLOR * 0.6);
    return float4(Finish(c), 1);
}

// ---- background: star, glow, stars ---------------------------------------------------------------
float4 BackgroundVS(uint id : SV_VertexID) : SV_Position
{
    float2 uv = float2((id << 1) & 2, id & 2);
    return float4(uv * float2(2, -2) + float2(-1, 1), 0, 1);
}

float Starfield(float3 d)
{
    float3 cell = floor(d * 280);
    uint h = Hash(asuint(cell.x) ^ Hash(asuint(cell.y) ^ Hash(asuint(cell.z))));
    if ((h & 1023) > 5)
        return 0;
    float3 jitter = float3(Hash(h) & 255, Hash(h + 1) & 255, Hash(h + 2) & 255) / 255.0;
    float d2 = dot(d * 280 - cell - jitter, d * 280 - cell - jitter);
    return exp(-d2 * 30) * (0.4 + (h >> 24) / 128.0);
}

float4 BackgroundPS(float4 position : SV_Position, out float depth : SV_Depth) : SV_Target
{
    float2 ndc = position.xy / screen * float2(2, -2) + float2(-1, 1);
    float4 near = mul(float4(ndc, 0, 1), invViewProj);
    float4 far = mul(float4(ndc, 1, 1), invViewProj);
    float3 origin = near.xyz / near.w;
    float3 dir = normalize(far.xyz / far.w - origin);

    float b = dot(origin, dir);
    float closest = length(origin - b * dir);                        // how near the ray passes the star
    float3 c = STAR_COLOR * 0.9 * pow(STAR_RADIUS / max(closest, STAR_RADIUS), 2.2);  // glow
    c += float3(0.8, 0.85, 1.0) * Starfield(dir);
    c += float3(0.02, 0.012, 0.03) * (0.5 + 0.5 * sin(dir.x * 3 + sin(dir.y * 5) * 2 + dir.z * 2));  // faint nebula
    depth = 1;
    float h = b * b - (dot(origin, origin) - STAR_RADIUS * STAR_RADIUS);
    if (h > 0 && -b - sqrt(h) > 0)
    {
        float3 hit = origin + dir * (-b - sqrt(h));
        float3 n = normalize(hit);
        float limb = saturate(dot(n, -dir));
        float granules = 0.85 + 0.15 * sin(n.x * 40 + sin(n.y * 37 + time) * 3) * sin(n.z * 33 + time * 0.7);
        c = lerp(float3(1.0, 0.45, 0.1), float3(1.0, 0.95, 0.8), pow(limb, 0.6)) * 6 * granules;
        float4 clip = mul(float4(hit, 1), viewProj);
        depth = clip.z / clip.w;
    }
    return float4(Finish(c), 1);
}
'''


# ---- icosphere template: 42 vertices / 80 triangles, refined to 162 / 320 --------------------------
def icosphere():
    t = (1 + 5 ** 0.5) / 2
    vertices = [numpy.array(v, float) / numpy.linalg.norm(v) for v in
                [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                 (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    cache = {}

    def midpoint(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            m = vertices[a] + vertices[b]
            vertices.append(m / numpy.linalg.norm(m))
            cache[key] = len(vertices) - 1
        return cache[key]

    def subdivide(tris):
        out = []
        for a, b, c in tris:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        return out

    coarse = subdivide(faces)       # vertices 0..41
    fine = subdivide(coarse)        # vertices 0..161: the coarse ones come first
    assert len(vertices) == 162 and len(coarse) == 80 and len(fine) == 320
    packed = numpy.array([a | (b << 8) | (c << 16) for a, b, c in fine + coarse], numpy.uint32)
    return numpy.array(vertices, numpy.float32), packed


# ---- math (row vectors, right handed, depth 0..1) ------------------------------------------------
def look_at(eye, target, up=(0, 1, 0)):
    f = target - eye
    f /= numpy.linalg.norm(f)
    s = numpy.cross(f, up)
    s /= numpy.linalg.norm(s)
    u = numpy.cross(s, f)
    m = numpy.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = s, u, -f
    m[3, :3] = -s @ eye, -u @ eye, f @ eye
    return m


def perspective(fov_y, aspect, near, far):
    f = 1 / math.tan(fov_y / 2)
    return numpy.array([[f / aspect, 0, 0, 0], [0, f, 0, 0], [0, 0, far / (near - far), -1],
                        [0, 0, near * far / (near - far), 0]])


def frustum_planes(m):
    """The 6 planes (inward normals) of the clip volume of a row-vector view-projection matrix."""
    c = [m[:, i] for i in range(4)]
    planes = numpy.array([c[3] + c[0], c[3] - c[0], c[3] + c[1], c[3] - c[1], c[2], c[3] - c[2]])
    return planes / numpy.linalg.norm(planes[:, :3], axis=1, keepdims=True)


# ---- D3D12 helpers ---------------------------------------------------------------------------------
def pipeline_stream(*subobjects):
    """Pack (type, desc) pairs into a pipeline state stream, like d3dx12.h's CD3DX12_PIPELINE_STATE_STREAM:
    every subobject is its type followed by its desc, aligned to the size of a pointer."""
    blob = bytearray()
    for kind, desc in subobjects:
        class Subobject(ctypes.Structure):
            _fields_ = [('type', ctypes.c_int), ('desc', type(desc))]
        sub = Subobject(kind, desc)
        data = ctypes.string_at(ctypes.addressof(sub), ctypes.sizeof(sub))
        blob += data + bytes(-len(data) % 8)
    stream = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    desc = dx.D3D12_PIPELINE_STATE_STREAM_DESC(SizeInBytes=len(blob),
                                               pPipelineStateSubobjectStream=ctypes.addressof(stream))
    return desc, stream


def compile_shader(source, entry, target):
    compiler = dx.DxcCreateInstance(dx.CLSID_DxcCompiler, dx.IDxcCompiler3)
    data = source.encode('utf-8')
    result = compiler.Compile(dx.DxcBuffer(Ptr=data), ['-T', target, '-E', entry, '-O3'], None, dx.IDxcResult)
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
    def __init__(self, hwnd, count):
        self.count = count
        factory = dx.CreateDXGIFactory2()
        adapter = factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)
        self.device = dx.D3D12CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_1, dx.ID3D12Device2)
        device = self.device
        options7 = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS7()
        device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS7, ctypes.byref(options7), ctypes.sizeof(options7))
        if options7.MeshShaderTier < dx.D3D12_MESH_SHADER_TIER_1:
            raise SystemExit('this GPU has no mesh shader support')
        options6 = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS6()
        device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS6, ctypes.byref(options6), ctypes.sizeof(options6))
        self.vrs = options6.VariableShadingRateTier >= dx.D3D12_VARIABLE_SHADING_RATE_TIER_1
        self.vrs_4x4 = self.vrs and bool(options6.AdditionalShadingRatesSupported)  # 2x4, 4x2 and 4x4
        options9 = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS9()
        device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS9, ctypes.byref(options9), ctypes.sizeof(options9))
        self.stats = bool(options9.MeshShaderPipelineStatsSupported)
        print('%s: mesh shaders, VRS %s, mesh shader statistics %s' % (
            adapter.GetDesc1().Description, 'yes' if self.vrs else 'no', 'yes' if self.stats else 'no'))

        self.queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
        self.allocator = device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
        self.cl = dx.ID3D12GraphicsCommandList6(
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

        self.create_targets()
        self.create_resources()
        self.create_pipelines()

    def buffer(self, size, heap=dx.D3D12_HEAP_TYPE_UPLOAD, state=dx.D3D12_RESOURCE_STATE_GENERIC_READ):
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                                      DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR)
        desc.SampleDesc.Count = 1
        return self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=heap), dx.D3D12_HEAP_FLAG_NONE,
                                                   desc, state)

    def upload(self, array):
        resource = self.buffer(array.nbytes)
        ctypes.memmove(resource.Map(0), array.ctypes.data, array.nbytes)
        resource.Unmap(0)
        return resource

    def create_targets(self):
        device = self.device
        self.rtv_heap = device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
            Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_RTV, NumDescriptors=1))
        self.dsv_heap = device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
            Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_DSV, NumDescriptors=1))
        self.rtv = self.rtv_heap.GetCPUDescriptorHandleForHeapStart()
        self.dsv = self.dsv_heap.GetCPUDescriptorHandleForHeapStart()

        def texture(fmt, flags, state, clear):
            desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=WIDTH, Height=HEIGHT,
                                          DepthOrArraySize=1, MipLevels=1, Format=fmt, Flags=flags)
            desc.SampleDesc.Count = SAMPLES
            return device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                                  dx.D3D12_HEAP_FLAG_NONE, desc, state, clear)

        clear_color = dx.D3D12_CLEAR_VALUE(Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM)
        self.color = texture(dx.DXGI_FORMAT_R8G8B8A8_UNORM, dx.D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET,
                             dx.D3D12_RESOURCE_STATE_RENDER_TARGET, clear_color)
        clear_depth = dx.D3D12_CLEAR_VALUE(Format=dx.DXGI_FORMAT_D32_FLOAT)
        clear_depth.DepthStencil.Depth = 1.0
        self.depth = texture(dx.DXGI_FORMAT_D32_FLOAT, dx.D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL,
                             dx.D3D12_RESOURCE_STATE_DEPTH_WRITE, clear_depth)
        device.CreateRenderTargetView(self.color, None, self.rtv)
        device.CreateDepthStencilView(self.depth, None, self.dsv)

    def create_resources(self):
        directions, triangles = icosphere()
        self.directions = self.upload(directions)
        self.triangles = self.upload(triangles)
        self.constants = self.buffer(256)
        self.constants_address = self.constants.Map(0)  # stays mapped: written every frame
        if self.stats:
            self.query_heap = self.device.CreateQueryHeap(dx.D3D12_QUERY_HEAP_DESC(
                Type=dx.D3D12_QUERY_HEAP_TYPE_PIPELINE_STATISTICS1, Count=1))
            self.query_readback = self.buffer(ctypes.sizeof(dx.D3D12_QUERY_DATA_PIPELINE_STATISTICS1),
                                              dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)

    def create_pipelines(self):
        device = self.device
        parameters = [dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_CBV,
                                               Descriptor=dx.D3D12_ROOT_DESCRIPTOR1(ShaderRegister=0))]
        parameters += [dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_SRV,
                                                Descriptor=dx.D3D12_ROOT_DESCRIPTOR1(ShaderRegister=r))
                       for r in (0, 1)]
        versioned = dx.D3D12_VERSIONED_ROOT_SIGNATURE_DESC(Version=dx.D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned.Desc_1_1 = dx.D3D12_ROOT_SIGNATURE_DESC1(pParameters=parameters)
        self.root = device.CreateRootSignature(0, dx.D3D12SerializeVersionedRootSignature(versioned))

        rasterizer = dx.D3D12_RASTERIZER_DESC(FillMode=dx.D3D12_FILL_MODE_SOLID, CullMode=dx.D3D12_CULL_MODE_NONE,
                                              DepthClipEnable=1, MultisampleEnable=1)
        blend = dx.D3D12_BLEND_DESC()
        blend.RenderTarget[0].RenderTargetWriteMask = dx.D3D12_COLOR_WRITE_ENABLE_ALL
        formats = dx.D3D12_RT_FORMAT_ARRAY(RTFormats=(dx.DXGI_FORMAT_R8G8B8A8_UNORM,), NumRenderTargets=1)
        samples = dx.DXGI_SAMPLE_DESC(Count=SAMPLES)

        def depth_test(func):
            return dx.D3D12_DEPTH_STENCIL_DESC(DepthEnable=1, DepthWriteMask=dx.D3D12_DEPTH_WRITE_MASK_ALL,
                                               DepthFunc=func)

        def common():
            return [(dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_ROOT_SIGNATURE, ctypes.c_void_p(self.root.value)),
                    (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_RASTERIZER, rasterizer),
                    (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_BLEND, blend),
                    (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_RENDER_TARGET_FORMATS, formats),
                    (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_DEPTH_STENCIL_FORMAT, ctypes.c_int(dx.DXGI_FORMAT_D32_FLOAT)),
                    (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_SAMPLE_DESC, samples),
                    (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_SAMPLE_MASK, ctypes.c_uint(0xFFFFFFFF))]

        # the mesh shader pipeline: amplification + mesh + pixel shaders, no input assembler at all
        self.shaders = [compile_shader(SHADERS, entry, target) for entry, target in
                        (('AS', 'as_6_5'), ('MS', 'ms_6_5'), ('PS', 'ps_6_5'),
                         ('BackgroundVS', 'vs_6_5'), ('BackgroundPS', 'ps_6_5'))]
        amplification, mesh, pixel, background_vs, background_ps = (
            dx.D3D12_SHADER_BYTECODE(pShaderBytecode=blob) for blob in self.shaders)
        desc, stream = pipeline_stream(*common(),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_AS, amplification),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_MS, mesh),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_PS, pixel),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_DEPTH_STENCIL,
                                        depth_test(dx.D3D12_COMPARISON_FUNC_LESS)))
        self.mesh_pso = device.CreatePipelineState(desc)
        # the background is a classic full screen triangle, built with the same kind of stream
        desc, stream = pipeline_stream(*common(),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_VS, background_vs),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_PS, background_ps),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_PRIMITIVE_TOPOLOGY,
                                        ctypes.c_int(dx.D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE)),
                                       (dx.D3D12_PIPELINE_STATE_SUBOBJECT_TYPE_DEPTH_STENCIL,
                                        depth_test(dx.D3D12_COMPARISON_FUNC_ALWAYS)))
        self.background_pso = device.CreatePipelineState(desc)

    def wait(self):
        self.fence_value += 1
        self.queue.Signal(self.fence, self.fence_value)
        self.fence.SetEventOnCompletion(self.fence_value, None)

    def render(self, constants, shading_rate):
        ctypes.memmove(self.constants_address, constants.ctypes.data, constants.nbytes)
        back_buffer = self.back_buffers[self.swap_chain.GetCurrentBackBufferIndex()]
        cl = self.cl
        self.allocator.Reset()
        cl.Reset(self.allocator)
        cl.SetGraphicsRootSignature(self.root)
        cl.SetGraphicsRootConstantBufferView(0, self.constants.GetGPUVirtualAddress())
        cl.SetGraphicsRootShaderResourceView(1, self.directions.GetGPUVirtualAddress())
        cl.SetGraphicsRootShaderResourceView(2, self.triangles.GetGPUVirtualAddress())
        cl.RSSetViewports([dx.D3D12_VIEWPORT(Width=WIDTH, Height=HEIGHT, MaxDepth=1)])
        cl.RSSetScissorRects([dx.D3D12_RECT(right=WIDTH, bottom=HEIGHT)])
        cl.OMSetRenderTargets(1, [self.rtv], False, self.dsv)
        cl.ClearDepthStencilView(self.dsv, dx.D3D12_CLEAR_FLAG_DEPTH, 1.0, 0)

        cl.SetPipelineState(self.background_pso)
        cl.IASetPrimitiveTopology(dx.D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
        cl.DrawInstanced(3, 1, 0, 0)

        cl.SetPipelineState(self.mesh_pso)
        if self.vrs:
            cl.RSSetShadingRate(shading_rate)
        if self.stats:
            cl.BeginQuery(self.query_heap, dx.D3D12_QUERY_TYPE_PIPELINE_STATISTICS1, 0)
        cl.DispatchMesh((self.count + GROUP - 1) // GROUP, 1, 1)
        if self.stats:
            cl.EndQuery(self.query_heap, dx.D3D12_QUERY_TYPE_PIPELINE_STATISTICS1, 0)
            cl.ResolveQueryData(self.query_heap, dx.D3D12_QUERY_TYPE_PIPELINE_STATISTICS1, 0, 1,
                                self.query_readback, 0)
        if self.vrs:
            cl.RSSetShadingRate(dx.D3D12_SHADING_RATE_1X1)

        # resolve the 4x MSAA image into the back buffer
        cl.ResourceBarrier([
            transition(self.color, dx.D3D12_RESOURCE_STATE_RENDER_TARGET, dx.D3D12_RESOURCE_STATE_RESOLVE_SOURCE),
            transition(back_buffer, dx.D3D12_RESOURCE_STATE_PRESENT, dx.D3D12_RESOURCE_STATE_RESOLVE_DEST)])
        cl.ResolveSubresource(back_buffer, 0, self.color, 0, dx.DXGI_FORMAT_R8G8B8A8_UNORM)
        cl.ResourceBarrier([
            transition(self.color, dx.D3D12_RESOURCE_STATE_RESOLVE_SOURCE, dx.D3D12_RESOURCE_STATE_RENDER_TARGET),
            transition(back_buffer, dx.D3D12_RESOURCE_STATE_RESOLVE_DEST, dx.D3D12_RESOURCE_STATE_PRESENT)])
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        self.swap_chain.Present(1, 0)
        self.wait()

    def statistics(self):
        if not self.stats:
            return None
        data = dx.D3D12_QUERY_DATA_PIPELINE_STATISTICS1.from_buffer_copy(ctypes.string_at(
            self.query_readback.Map(0), ctypes.sizeof(dx.D3D12_QUERY_DATA_PIPELINE_STATISTICS1)))
        self.query_readback.Unmap(0)
        return data

    def save(self, path):
        from PIL import Image
        back_buffer = self.back_buffers[(self.swap_chain.GetCurrentBackBufferIndex() + 1) % 2]  # last presented
        footprints, _, _, total = self.device.GetCopyableFootprints(back_buffer.GetDesc(), 0, 1, 0)
        readback = self.buffer(total, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        cl = self.cl
        self.allocator.Reset()
        cl.Reset(self.allocator)
        cl.ResourceBarrier([transition(back_buffer, dx.D3D12_RESOURCE_STATE_PRESENT,
                                       dx.D3D12_RESOURCE_STATE_COPY_SOURCE)])
        dst = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=readback, Type=dx.D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT)
        dst.PlacedFootprint = footprints[0]
        src = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=back_buffer, Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX)
        cl.CopyTextureRegion(dst, 0, 0, 0, src, None)
        cl.ResourceBarrier([transition(back_buffer, dx.D3D12_RESOURCE_STATE_COPY_SOURCE,
                                       dx.D3D12_RESOURCE_STATE_PRESENT)])
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
    ap.add_argument('--count', type=int, default=50000, help='number of asteroids')
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames')
    ap.add_argument('--screenshot', help='save the last frame to this PNG')
    ap.add_argument('--shading-rate', choices=('1x1', '2x2', '4x4'), default='1x1',
                    help='variable rate shading of the asteroids (V cycles it)')
    ap.add_argument('--debug', action='store_true', help='enable the D3D12 debug layer and report its errors')
    args = ap.parse_args()
    if args.debug:
        dx.D3D12GetDebugInterface().EnableDebugLayer()

    root = tkinter.Tk()
    root.title('pydx12: mesh shaders')
    view = tkinter.Frame(root, width=WIDTH, height=HEIGHT)
    view.pack()
    root.resizable(False, False)
    root.update()
    renderer = Renderer(view.winfo_id(), args.count)

    rates = [(dx.D3D12_SHADING_RATE_1X1, '1x1'), (dx.D3D12_SHADING_RATE_2X2, '2x2')]
    if renderer.vrs_4x4:
        rates.append((dx.D3D12_SHADING_RATE_4X4, '4x4'))
    names = [name for _, name in rates]
    state: dict = {'yaw': 0.4, 'pitch': 0.07, 'distance': 92.0, 'drag': None,
                   'rate': names.index(args.shading_rate) if args.shading_rate in names else 0, 'paused': False,
                   'closed': False, 'time': 0.0}

    def on_drag(event):
        if state['drag']:
            state['yaw'] -= (event.x - state['drag'][0]) * 0.005
            state['pitch'] = min(1.4, max(-1.4, state['pitch'] + (event.y - state['drag'][1]) * 0.005))
        state['drag'] = (event.x, event.y)

    def on_key(event):
        if event.keysym in ('v', 'V'):
            state['rate'] = (state['rate'] + 1) % len(rates)
        elif event.keysym == 'space':
            state['paused'] = not state['paused']
        elif event.keysym == 'Escape':
            state['closed'] = True

    view.bind('<ButtonPress-1>', lambda e: state.update(drag=(e.x, e.y)))
    view.bind('<B1-Motion>', on_drag)
    root.bind('<MouseWheel>', lambda e: state.update(
        distance=min(400.0, max(20.0, state['distance'] * (0.9 if e.delta > 0 else 1.1)))))
    root.bind('<Key>', on_key)
    root.protocol('WM_DELETE_WINDOW', lambda: state.update(closed=True))

    projection = perspective(math.radians(55), WIDTH / HEIGHT, 0.1, 2000)
    frames, start, last = 0, time.perf_counter(), time.perf_counter()
    while not state['closed'] and (not args.frames or frames < args.frames):
        root.update()
        now = time.perf_counter()
        if not state['paused']:
            state['time'] += now - last
            state['yaw'] += (now - last) * 0.03
        last = now
        y, p, d = state['yaw'], state['pitch'], state['distance']
        eye = numpy.array([math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p)]) * d
        view_proj = look_at(eye, numpy.array([0.0, 0.0, 0.0])) @ projection
        constants = numpy.zeros(64, numpy.float32)
        constants[0:16] = view_proj.ravel()
        constants[16:32] = numpy.linalg.inv(view_proj).ravel()
        constants[32:56] = frustum_planes(view_proj).ravel()
        constants[56:59], constants[59] = eye, state['time']
        constants[60:62] = WIDTH, HEIGHT
        constants.view(numpy.uint32)[62] = args.count
        renderer.render(constants, rates[state['rate']][0])
        frames += 1
        if frames % 15 == 0:
            title = 'pydx12: mesh shaders - %d asteroids - %.0f fps - VRS %s' % (
                args.count, frames / (now - start), rates[state['rate']][1] if renderer.vrs else 'n/a')
            stats = renderer.statistics()
            if stats is not None:
                # each detailed asteroid is 2 mesh shader groups; MSPrimitives counts the triangles emitted
                title += ' - amplification groups %d, mesh groups %d, %.2fM triangles' % (
                    stats.ASInvocations // GROUP, stats.MSInvocations // 128, stats.MSPrimitives / 1e6)
            root.title(title + ' - drag, wheel, V, space')
    if args.screenshot:
        renderer.save(args.screenshot)
    renderer.wait()
    stats = renderer.statistics()
    print('%d frames, %.1f fps' % (frames, frames / (time.perf_counter() - start)))
    if stats is not None:
        print('last frame: %d amplification threads, %d mesh shader groups, %d triangles' % (
            stats.ASInvocations, stats.MSInvocations // 128, stats.MSPrimitives))
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
