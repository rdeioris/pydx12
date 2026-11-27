"""A real-time path tracer on DirectX Raytracing (DXR).

Everything is lit by light bouncing around the scene, traced on the GPU's raytracing hardware:

- global illumination: diffuse inter-reflections and color bleeding
- a warm sun with soft shadows, a sky dome and a glowing emissive sphere
- mirrors, rough gold, glass that refracts, a checkered floor
- both kinds of DXR geometry: triangle meshes (floor and boxes) and procedural spheres traced by an
  intersection shader
- a thin lens camera with depth of field, ACES tone mapping
- progressive rendering: samples accumulate while the camera is still, so the image converges

The ray generation shader runs the path tracing loop; closest hit and intersection shaders only report
what was hit. The state object holds one DXIL library and two hit groups (triangles, procedural spheres)
and the shader table has a ray generation record, a miss record and a record per hit group.

Mouse: drag to orbit, wheel to zoom, right click to focus there. Keys: [ ] aperture, Space auto orbit,
S saves a PNG, Escape quits.

Usage: python examples/pathtracer.py [--width 1280] [--height 720] [--spp 2] [--bounces 8]
                                     [--screenshot out.png --samples 1024]
"""
import argparse
import ctypes
import math
import time
import tkinter

import numpy

import pydx12 as dx

SHADERS = r'''
#define PI 3.14159265

RaytracingAccelerationStructure Scene : register(t0);
struct Vertex { float3 position; float3 normal; };
StructuredBuffer<Vertex> Vertices : register(t1);
StructuredBuffer<uint> Indices : register(t2);
StructuredBuffer<uint> TriangleMaterials : register(t3);
struct Sphere { float3 center; float radius; uint material; float3 pad; };
StructuredBuffer<Sphere> Spheres : register(t4);
struct Material { float3 albedo; float roughness; float3 emission; float ior; uint type; float3 pad; };
StructuredBuffer<Material> Materials : register(t5);
RWTexture2D<float4> Accumulation : register(u0);
RWTexture2D<float4> Output : register(u1);

cbuffer Camera : register(b0)
{
    float3 origin; uint frame;
    float3 forward; float aperture;
    float3 right; float focusDistance;   // right and up are scaled by the field of view
    float3 up; uint samplesPerFrame;
    float3 sunDirection; uint maxBounces;
};

#define DIFFUSE 0
#define METAL 1
#define GLASS 2
#define CHECKER 3
#define EMISSIVE 4

struct Payload { float3 normal; float t; uint material; uint hit; };
struct SphereAttributes { float3 normal; };

// ---- random numbers (PCG hash) -----------------------------------------------------------------
float Random(inout uint state)
{
    state = state * 747796405u + 2891336453u;
    uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
    return ((word >> 22u) ^ word) / 4294967296.0;
}

float3 RandomInSphere(inout uint state)
{
    float z = Random(state) * 2 - 1, a = Random(state) * 2 * PI, r = sqrt(1 - z * z);
    return float3(r * cos(a), r * sin(a), z) * pow(Random(state), 1.0 / 3.0);
}

float3 CosineHemisphere(float3 n, inout uint state)
{
    float a = Random(state) * 2 * PI, r = sqrt(Random(state));
    float3 t = normalize(abs(n.y) < 0.99 ? cross(n, float3(0, 1, 0)) : cross(n, float3(1, 0, 0)));
    float3 b = cross(n, t);
    return normalize(t * r * cos(a) + b * r * sin(a) + n * sqrt(1 - r * r));
}

// ---- lighting ------------------------------------------------------------------------------------
static const float3 SUN_COLOR = float3(1.0, 0.78, 0.55) * 2.6;
static const float SUN_COS = 0.9995;   // angular size of the sun disk (and of its soft shadows)

float3 Sky(float3 d, bool withSun)
{
    float h = saturate(d.y);
    float s = dot(d, sunDirection);
    float3 horizon = lerp(float3(0.5, 0.58, 0.72), float3(1.3, 0.75, 0.42), pow(saturate(s * 0.5 + 0.5), 3));
    float3 sky = lerp(horizon, float3(0.1, 0.24, 0.62), pow(h, 0.4));
    sky = lerp(float3(0.2, 0.17, 0.15), sky, smoothstep(-0.05, 0.02, d.y));  // below the horizon
    sky += SUN_COLOR * 0.35 * pow(saturate(s), 48);                           // glow around the sun
    if (withSun && s > SUN_COS)
        sky += SUN_COLOR * 400;
    return sky;
}

float3 SunSample(inout uint state)
{
    // a random direction inside the sun's disk
    float3 t = normalize(cross(sunDirection, float3(0, 1, 0)));
    float3 b = cross(sunDirection, t);
    float a = Random(state) * 2 * PI, r = sqrt(Random(state)) * sqrt(1 - SUN_COS * SUN_COS);
    return normalize(sunDirection + t * r * cos(a) + b * r * sin(a));
}

bool Occluded(float3 position, float3 direction, float distance)
{
    RayDesc ray;
    ray.Origin = position;
    ray.Direction = direction;
    ray.TMin = 1e-3;
    ray.TMax = distance;
    Payload payload;
    payload.hit = 1;  // the miss shader clears it
    TraceRay(Scene, RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH | RAY_FLAG_SKIP_CLOSEST_HIT_SHADER, 0xFF, 0, 0, 0,
             ray, payload);
    return payload.hit != 0;
}

// direct light from the lamp, Spheres[0]: sample the cone of directions it covers
float3 LampLight(float3 position, float3 normal, float3 albedo, inout uint state)
{
    Sphere lamp = Spheres[0];
    float3 toCenter = lamp.center - position;
    float distance2 = dot(toCenter, toCenter);
    float sinMax2 = lamp.radius * lamp.radius / distance2;
    if (sinMax2 >= 1)
        return 0;
    float cosMax = sqrt(1 - sinMax2);
    float3 w = toCenter / sqrt(distance2);
    float3 t = normalize(abs(w.y) < 0.99 ? cross(w, float3(0, 1, 0)) : cross(w, float3(1, 0, 0)));
    float3 b = cross(w, t);
    float cosTheta = 1 - Random(state) * (1 - cosMax);
    float sinTheta = sqrt(1 - cosTheta * cosTheta), phi = Random(state) * 2 * PI;
    float3 direction = normalize(t * sinTheta * cos(phi) + b * sinTheta * sin(phi) + w * cosTheta);
    float cosine = dot(normal, direction);
    if (cosine <= 0)
        return 0;
    // distance to the lamp's surface along that direction
    float projected = dot(toCenter, direction);
    float hit = projected - sqrt(max(0, lamp.radius * lamp.radius - (distance2 - projected * projected)));
    if (Occluded(position, direction, hit * 0.999))
        return 0;
    // radiance * brdf (albedo / pi) * cosine / pdf, with pdf = 1 / (2 pi (1 - cosMax))
    return Materials[lamp.material].emission * albedo * cosine * 2 * (1 - cosMax);
}

float3 Aces(float3 x)
{
    return saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
}

// ---- path tracing ---------------------------------------------------------------------------------
float3 Trace(float3 rayOrigin, float3 rayDirection, inout uint state)
{
    float3 radiance = 0, throughput = 1;
    bool specular = true;  // camera rays and mirror bounces may see the sun disk directly
    for (uint bounce = 0; bounce < maxBounces; bounce++)
    {
        RayDesc ray;
        ray.Origin = rayOrigin;
        ray.Direction = rayDirection;
        ray.TMin = 1e-3;
        ray.TMax = 1e4;
        Payload payload;
        TraceRay(Scene, RAY_FLAG_NONE, 0xFF, 0, 0, 0, ray, payload);
        if (!payload.hit)
        {
            radiance += throughput * Sky(rayDirection, specular);
            break;
        }

        float3 position = rayOrigin + rayDirection * payload.t;
        bool front = dot(rayDirection, payload.normal) < 0;
        float3 normal = front ? payload.normal : -payload.normal;
        Material m = Materials[payload.material];
        if (m.type == EMISSIVE)
        {
            // after a diffuse bounce the lamp was already sampled directly (LampLight)
            if (specular)
                radiance += throughput * m.emission;
            break;
        }

        if (m.type == CHECKER)
        {
            // clear coat: some light reflects off the polished surface, more at grazing angles
            float cosine = saturate(dot(-rayDirection, normal));
            float coat = 0.04 + 0.96 * pow(1 - cosine, 5);
            if (Random(state) < coat)
            {
                rayDirection = normalize(reflect(rayDirection, normal) + 0.03 * RandomInSphere(state));
                rayOrigin = position;
                specular = true;
                continue;
            }
        }
        if (m.type == DIFFUSE || m.type == CHECKER)
        {
            float3 albedo = m.albedo;
            if (m.type == CHECKER)
            {
                int2 cell = int2(floor(position.xz * 1.0));
                albedo = ((cell.x + cell.y) & 1) ? m.albedo : m.albedo * 0.18;
            }
            // next event estimation: sample the sun directly, the bounce below won't see it
            float3 toSun = SunSample(state);
            float cosine = dot(normal, toSun);
            if (cosine > 0 && !Occluded(position, toSun, 1e4))
                radiance += throughput * albedo * SUN_COLOR * cosine;
            radiance += throughput * LampLight(position, normal, albedo, state);
            rayDirection = CosineHemisphere(normal, state);
            throughput *= albedo;
            specular = false;
        }
        else if (m.type == METAL)
        {
            float3 reflected = reflect(rayDirection, normal) + m.roughness * RandomInSphere(state);
            if (dot(reflected, normal) <= 0)
                break;
            rayDirection = normalize(reflected);
            throughput *= m.albedo;
            specular = m.roughness < 0.05;
        }
        else  // GLASS
        {
            float eta = front ? 1.0 / m.ior : m.ior;
            float cosine = min(dot(-rayDirection, normal), 1.0);
            float sine = sqrt(1 - cosine * cosine);
            float r0 = (1 - eta) / (1 + eta);
            float fresnel = r0 * r0 + (1 - r0 * r0) * pow(1 - cosine, 5);
            if (eta * sine > 1 || Random(state) < fresnel)
                rayDirection = reflect(rayDirection, normal);
            else
                rayDirection = refract(rayDirection, normal, eta);
            if (!front)  // absorption inside the glass (Beer's law) tints thick parts
                throughput *= exp(-(1 - m.albedo) * payload.t);
            specular = true;
        }
        rayOrigin = position;

        // russian roulette: dim paths stop early, survivors are boosted to stay unbiased
        if (bounce > 2)
        {
            float p = max(throughput.r, max(throughput.g, throughput.b));
            if (Random(state) > p)
                break;
            throughput /= p;
        }
    }
    return min(radiance, 10.0);  // clamp the rare very bright paths (fireflies)
}

[shader("raygeneration")]
void RayGen()
{
    uint2 pixel = DispatchRaysIndex().xy;
    uint2 size = DispatchRaysDimensions().xy;
    uint state = (pixel.x * 1973u + pixel.y * 9277u + frame * 26699u) | 1u;

    float3 color = 0;
    for (uint s = 0; s < samplesPerFrame; s++)
    {
        float2 jitter = float2(Random(state), Random(state));
        float2 ndc = ((pixel + jitter) / size) * 2 - 1;
        float3 direction = normalize(forward + ndc.x * right - ndc.y * up);
        // thin lens: start from a random point of the aperture, aim at the focal plane
        float3 focus = origin + direction * (focusDistance / dot(direction, forward));
        float a = Random(state) * 2 * PI, r = sqrt(Random(state)) * aperture;
        float3 lens = origin + normalize(right) * r * cos(a) + normalize(up) * r * sin(a);
        color += Trace(lens, normalize(focus - lens), state);
    }

    float4 sum = float4(color, samplesPerFrame);
    if (frame > 0)
        sum += Accumulation[pixel];
    Accumulation[pixel] = sum;
    float3 average = sum.rgb / sum.a;
    Output[pixel] = float4(pow(Aces(average * 0.55), 1 / 2.2), 1);
}

[shader("miss")]
void Miss(inout Payload payload)
{
    payload.hit = 0;
}

[shader("closesthit")]
void ClosestHitTriangle(inout Payload payload, BuiltInTriangleIntersectionAttributes attributes)
{
    uint first = PrimitiveIndex() * 3;
    float3 n0 = Vertices[Indices[first]].normal;
    float3 n1 = Vertices[Indices[first + 1]].normal;
    float3 n2 = Vertices[Indices[first + 2]].normal;
    float2 b = attributes.barycentrics;
    payload.normal = normalize(n0 * (1 - b.x - b.y) + n1 * b.x + n2 * b.y);
    payload.t = RayTCurrent();
    payload.material = TriangleMaterials[PrimitiveIndex()];
    payload.hit = 1;
}

[shader("intersection")]
void IntersectSphere()
{
    Sphere sphere = Spheres[PrimitiveIndex()];
    float3 o = ObjectRayOrigin() - sphere.center;
    float3 d = ObjectRayDirection();
    float a = dot(d, d), b = dot(o, d), c = dot(o, o) - sphere.radius * sphere.radius;
    float discriminant = b * b - a * c;
    if (discriminant < 0)
        return;
    float root = sqrt(discriminant);
    float t = (-b - root) / a;
    if (t < RayTMin() || t > RayTCurrent())
        t = (-b + root) / a;  // the ray starts inside (glass)
    if (t < RayTMin() || t > RayTCurrent())
        return;
    SphereAttributes attributes;
    attributes.normal = (o + t * d) / sphere.radius;
    ReportHit(t, 0, attributes);
}

[shader("closesthit")]
void ClosestHitSphere(inout Payload payload, SphereAttributes attributes)
{
    payload.normal = attributes.normal;
    payload.t = RayTCurrent();
    payload.material = Spheres[PrimitiveIndex()].material;
    payload.hit = 1;
}
'''

# ---- the scene ---------------------------------------------------------------------------------
DIFFUSE, METAL, GLASS, CHECKER, EMISSIVE = range(5)
MATERIAL = numpy.dtype([('albedo', '3f4'), ('roughness', 'f4'), ('emission', '3f4'), ('ior', 'f4'),
                        ('type', 'u4'), ('pad', '3f4')])
SPHERE = numpy.dtype([('center', '3f4'), ('radius', 'f4'), ('material', 'u4'), ('pad', '3f4')])
VERTEX = numpy.dtype([('position', '3f4'), ('normal', '3f4')])


def build_scene():
    materials = []

    def material(kind, albedo=(1, 1, 1), roughness=0.0, emission=(0, 0, 0), ior=1.5):
        materials.append((albedo, roughness, emission, ior, kind, (0, 0, 0)))
        return len(materials) - 1

    floor = material(CHECKER, (0.7, 0.68, 0.65))
    white = material(DIFFUSE, (0.8, 0.8, 0.78))
    teal = material(DIFFUSE, (0.12, 0.55, 0.55))
    red = material(DIFFUSE, (0.75, 0.12, 0.1))
    steel = material(METAL, (0.8, 0.82, 0.85), roughness=0.18)
    gold = material(METAL, (1.0, 0.76, 0.33), roughness=0.22)
    mirror = material(METAL, (0.95, 0.95, 0.95), roughness=0.0)
    glass = material(GLASS, (0.92, 0.97, 1.0), ior=1.5)
    lamp = material(EMISSIVE, emission=(16.0, 7.0, 2.2))

    # triangle meshes, already in world space: the floor and three rotated boxes
    vertices: list = []
    indices: list = []
    tri_materials: list = []

    def quad(corners, normal, mat):
        base = len(vertices)
        vertices.extend((c, normal) for c in corners)
        indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])
        tri_materials.extend([mat, mat])

    quad([(-30, 0, -30), (-30, 0, 30), (30, 0, 30), (30, 0, -30)], (0, 1, 0), floor)

    def box(center, size, angle, mat):
        c, s = math.cos(angle), math.sin(angle)

        def world(p):
            x, y, z = p
            return (center[0] + x * c - z * s, center[1] + y, center[2] + x * s + z * c)

        def turn(n):
            return (n[0] * c - n[2] * s, n[1], n[0] * s + n[2] * c)

        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        faces = [((1, 0, 0), [(hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz)]),
                 ((-1, 0, 0), [(-hx, -hy, hz), (-hx, hy, hz), (-hx, hy, -hz), (-hx, -hy, -hz)]),
                 ((0, 1, 0), [(-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz), (hx, hy, -hz)]),
                 ((0, -1, 0), [(-hx, -hy, hz), (-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz)]),
                 ((0, 0, 1), [(hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz), (-hx, -hy, hz)]),
                 ((0, 0, -1), [(-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz)])]
        for normal, corners in faces:
            quad([world(p) for p in corners], turn(normal), mat)

    box((-3.2, 1.4, -2.6), (1.4, 2.8, 1.4), 0.5, red)
    box((3.4, 0.6, -2.0), (1.2, 1.2, 1.2), -0.35, steel)
    box((-1.0, 0.35, 2.4), (0.7, 0.7, 0.7), 0.9, white)

    # procedural spheres: the stars of the show plus a scatter of small ones
    spheres = [((1.25, 0.38, 1.25), 0.38, lamp),  # first: the shaders sample it as a light
               ((0.0, 1.0, 0.0), 1.0, glass),
               ((-2.2, 0.8, 0.9), 0.8, gold),
               ((2.2, 1.0, -0.4), 1.0, mirror),
               ((-0.8, 0.55, -1.9), 0.55, teal)]
    rng = numpy.random.default_rng(7)
    palette = [(0.9, 0.35, 0.2), (0.25, 0.5, 0.9), (0.95, 0.85, 0.3), (0.4, 0.8, 0.4), (0.85, 0.85, 0.85)]
    for i in range(26):
        angle = i * 2.4 + rng.uniform(-0.3, 0.3)
        distance = 2.9 + rng.uniform(0, 2.6)
        radius = rng.uniform(0.15, 0.3)
        center = (math.cos(angle) * distance, radius, math.sin(angle) * distance)
        if any(math.dist(center, s[0]) < s[1] + radius + 0.1 for s in spheres):
            continue
        roll = rng.uniform()
        color = palette[i % len(palette)]
        if roll < 0.55:
            mat = material(DIFFUSE, color)
        elif roll < 0.8:
            mat = material(METAL, color, roughness=rng.uniform(0, 0.3))
        else:
            mat = material(GLASS, (0.95, 0.95, 0.95))
        spheres.append((center, radius, mat))

    vertex_data = numpy.array(vertices, VERTEX)
    sphere_data = numpy.array([(c, r, m, (0, 0, 0)) for c, r, m in spheres], SPHERE)
    material_data = numpy.array(materials, MATERIAL)
    return (vertex_data, numpy.array(indices, numpy.uint32), numpy.array(tri_materials, numpy.uint32),
            sphere_data, material_data)


# ---- small D3D12 helpers -----------------------------------------------------------------------
def buffer(device, size, heap=dx.D3D12_HEAP_TYPE_UPLOAD, state=dx.D3D12_RESOURCE_STATE_GENERIC_READ,
           flags=dx.D3D12_RESOURCE_FLAG_NONE):
    desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=max(size, 1), Height=1,
                                  DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR,
                                  Flags=flags)
    desc.SampleDesc.Count = 1
    return device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=heap), dx.D3D12_HEAP_FLAG_NONE, desc, state)


def upload(device, data):
    """Static scene data lives in an upload heap: the GPU reads it directly."""
    data = bytes(memoryview(data).cast('B'))
    resource = buffer(device, len(data))
    ctypes.memmove(resource.Map(0), data, len(data))
    resource.Unmap(0)
    return resource


def transition(resource, before, after):
    b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
    b.Transition = dx.D3D12_RESOURCE_TRANSITION_BARRIER(pResource=resource, StateBefore=before, StateAfter=after,
                                                        Subresource=dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
    return b


def uav_barrier(resource):
    b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_UAV)
    b.UAV.pResource = resource
    return b


def build_acceleration_structure(device, command_list, inputs):
    info = device.GetRaytracingAccelerationStructurePrebuildInfo(inputs)
    result = buffer(device, info.ResultDataMaxSizeInBytes, dx.D3D12_HEAP_TYPE_DEFAULT,
                    dx.D3D12_RESOURCE_STATE_RAYTRACING_ACCELERATION_STRUCTURE,
                    dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
    scratch = buffer(device, info.ScratchDataSizeInBytes, dx.D3D12_HEAP_TYPE_DEFAULT,
                     dx.D3D12_RESOURCE_STATE_COMMON, dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
    command_list.BuildRaytracingAccelerationStructure(dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_DESC(
        DestAccelerationStructureData=result.GetGPUVirtualAddress(), Inputs=inputs,
        ScratchAccelerationStructureData=scratch.GetGPUVirtualAddress()))
    command_list.ResourceBarrier([uav_barrier(result)])
    return result, scratch


def compile_library(source):
    compiler = dx.DxcCreateInstance(dx.CLSID_DxcCompiler, dx.IDxcCompiler3)
    data = source.encode('utf-8')
    result = compiler.Compile(dx.DxcBuffer(Ptr=data), ['-T', 'lib_6_3', '-O3'], None, dx.IDxcResult)
    if result.GetStatus() < 0:
        errors = result.GetOutput(dx.DXC_OUT_ERRORS, dx.IDxcBlobUtf8)[0]
        raise SystemExit(bytes(errors).decode('utf-8', 'replace') if errors else 'shader compilation failed')
    blob = result.GetOutput(dx.DXC_OUT_OBJECT, dx.IDxcBlob)[0]
    assert blob is not None
    return blob


class Renderer:
    def __init__(self, width, height, hwnd):
        self.width, self.height = width, height
        factory = dx.CreateDXGIFactory2()
        adapter = factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)
        self.device = dx.D3D12CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_1, dx.ID3D12Device5)
        options = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS5()
        self.device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS5, ctypes.byref(options),
                                        ctypes.sizeof(options))
        if options.RaytracingTier < dx.D3D12_RAYTRACING_TIER_1_0:
            raise SystemExit('this GPU has no DirectX Raytracing support')
        print('%s, raytracing tier %d.%d' % ((adapter.GetDesc1().Description,) + divmod(options.RaytracingTier, 10)))

        device = self.device
        self.queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
        self.allocators = [device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT) for _ in range(2)]
        self.command_list = dx.ID3D12GraphicsCommandList4(
            device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, self.allocators[0]))
        self.fence = device.CreateFence()
        self.fence_values = [0, 0]
        self.fence_counter = 0

        sc_desc = dx.DXGI_SWAP_CHAIN_DESC1(Width=width, Height=height, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                           BufferUsage=dx.DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=2,
                                           SwapEffect=dx.DXGI_SWAP_EFFECT_FLIP_DISCARD)
        sc_desc.SampleDesc.Count = 1
        self.swap_chain = dx.IDXGISwapChain3(factory.CreateSwapChainForHwnd(self.queue, hwnd, sc_desc))
        self.back_buffers = [self.swap_chain.GetBuffer(i) for i in range(2)]

        self.build_scene_and_acceleration_structures()
        self.build_pipeline()
        self.create_outputs()

    # -- acceleration structures --------------------------------------------------------------------
    def build_scene_and_acceleration_structures(self):
        device, cl = self.device, self.command_list
        vertices, indices, tri_materials, spheres, materials = build_scene()
        self.num_spheres = len(spheres)
        self.vertex_buffer = upload(device, vertices)
        self.index_buffer = upload(device, indices)
        self.tri_material_buffer = upload(device, tri_materials)
        self.sphere_buffer = upload(device, spheres)
        self.material_buffer = upload(device, materials)
        aabbs = numpy.concatenate([spheres['center'] - spheres['radius'][:, None],
                                   spheres['center'] + spheres['radius'][:, None]], axis=1).astype(numpy.float32)
        self.aabb_buffer = upload(device, aabbs)

        triangles = dx.D3D12_RAYTRACING_GEOMETRY_DESC(Type=dx.D3D12_RAYTRACING_GEOMETRY_TYPE_TRIANGLES,
                                                      Flags=dx.D3D12_RAYTRACING_GEOMETRY_FLAG_OPAQUE)
        triangles.Triangles = dx.D3D12_RAYTRACING_GEOMETRY_TRIANGLES_DESC(
            IndexFormat=dx.DXGI_FORMAT_R32_UINT, IndexCount=len(indices),
            IndexBuffer=self.index_buffer.GetGPUVirtualAddress(),
            VertexFormat=dx.DXGI_FORMAT_R32G32B32_FLOAT, VertexCount=len(vertices),
            VertexBuffer=dx.D3D12_GPU_VIRTUAL_ADDRESS_AND_STRIDE(
                StartAddress=self.vertex_buffer.GetGPUVirtualAddress(), StrideInBytes=vertices.dtype.itemsize))
        procedural = dx.D3D12_RAYTRACING_GEOMETRY_DESC(Type=dx.D3D12_RAYTRACING_GEOMETRY_TYPE_PROCEDURAL_PRIMITIVE_AABBS,
                                                       Flags=dx.D3D12_RAYTRACING_GEOMETRY_FLAG_OPAQUE)
        procedural.AABBs = dx.D3D12_RAYTRACING_GEOMETRY_AABBS_DESC(
            AABBCount=len(aabbs), AABBs=dx.D3D12_GPU_VIRTUAL_ADDRESS_AND_STRIDE(
                StartAddress=self.aabb_buffer.GetGPUVirtualAddress(), StrideInBytes=24))
        self.geometries = (triangles, procedural)  # referenced by the build inputs

        cl.Close()
        self.allocators[0].Reset()
        cl.Reset(self.allocators[0])
        self.blases = []
        for geometry in self.geometries:
            inputs = dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
                Type=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL,
                Flags=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_TRACE,
                NumDescs=1, DescsLayout=dx.D3D12_ELEMENTS_LAYOUT_ARRAY)
            inputs.pGeometryDescs = ctypes.pointer(geometry)
            self.blases.append(build_acceleration_structure(device, cl, inputs))

        # two instances with identity transforms; hit group 0 is for triangles, 1 for spheres
        instances = (dx.D3D12_RAYTRACING_INSTANCE_DESC * 2)()
        for i, (blas, _) in enumerate(self.blases):
            instances[i].Transform[0][0] = instances[i].Transform[1][1] = instances[i].Transform[2][2] = 1.0
            instances[i].InstanceMask = 0xFF
            instances[i].InstanceContributionToHitGroupIndex = i
            instances[i].AccelerationStructure = blas.GetGPUVirtualAddress()
        self.instance_buffer = upload(device, instances)
        tlas_inputs = dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
            Type=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL,
            Flags=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_TRACE,
            NumDescs=2, DescsLayout=dx.D3D12_ELEMENTS_LAYOUT_ARRAY)
        tlas_inputs.InstanceDescs = self.instance_buffer.GetGPUVirtualAddress()
        self.tlas, self.tlas_scratch = build_acceleration_structure(device, cl, tlas_inputs)
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        self.wait_idle()

    # -- pipeline -----------------------------------------------------------------------------------
    def build_pipeline(self):
        device = self.device
        library = compile_library(SHADERS)

        uavs = dx.D3D12_DESCRIPTOR_RANGE1(RangeType=dx.D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=2,
                                          BaseShaderRegister=0)
        table = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE)
        table.DescriptorTable = dx.D3D12_ROOT_DESCRIPTOR_TABLE1(pDescriptorRanges=[uavs])
        constants = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS)
        constants.Constants = dx.D3D12_ROOT_CONSTANTS(ShaderRegister=0, Num32BitValues=20)
        parameters = [table, constants] + [
            dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_SRV,
                                     Descriptor=dx.D3D12_ROOT_DESCRIPTOR1(ShaderRegister=register))
            for register in range(6)]  # t0 scene, t1..t5 scene data
        versioned = dx.D3D12_VERSIONED_ROOT_SIGNATURE_DESC(Version=dx.D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned.Desc_1_1 = dx.D3D12_ROOT_SIGNATURE_DESC1(pParameters=parameters)
        self.root_signature = device.CreateRootSignature(0, dx.D3D12SerializeVersionedRootSignature(versioned))

        # the state object; each subobject's pDesc points to a struct that must stay alive
        self.subobject_descs = [
            (dx.D3D12_STATE_SUBOBJECT_TYPE_DXIL_LIBRARY,
             dx.D3D12_DXIL_LIBRARY_DESC(DXILLibrary=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=library))),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_HIT_GROUP,
             dx.D3D12_HIT_GROUP_DESC(HitGroupExport='TriangleHitGroup', Type=dx.D3D12_HIT_GROUP_TYPE_TRIANGLES,
                                     ClosestHitShaderImport='ClosestHitTriangle')),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_HIT_GROUP,
             dx.D3D12_HIT_GROUP_DESC(HitGroupExport='SphereHitGroup',
                                     Type=dx.D3D12_HIT_GROUP_TYPE_PROCEDURAL_PRIMITIVE,
                                     ClosestHitShaderImport='ClosestHitSphere',
                                     IntersectionShaderImport='IntersectSphere')),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_SHADER_CONFIG,
             dx.D3D12_RAYTRACING_SHADER_CONFIG(MaxPayloadSizeInBytes=24, MaxAttributeSizeInBytes=12)),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_PIPELINE_CONFIG,
             dx.D3D12_RAYTRACING_PIPELINE_CONFIG(MaxTraceRecursionDepth=1)),  # the loop lives in raygen
            (dx.D3D12_STATE_SUBOBJECT_TYPE_GLOBAL_ROOT_SIGNATURE,
             dx.D3D12_GLOBAL_ROOT_SIGNATURE(pGlobalRootSignature=self.root_signature)),
        ]
        self.state_object = device.CreateStateObject(dx.D3D12_STATE_OBJECT_DESC(
            Type=dx.D3D12_STATE_OBJECT_TYPE_RAYTRACING_PIPELINE,
            pSubobjects=[dx.D3D12_STATE_SUBOBJECT(Type=kind, pDesc=ctypes.addressof(desc))
                         for kind, desc in self.subobject_descs]))

        # shader table: raygen | miss | triangle hit group | sphere hit group, one aligned record each
        properties = dx.ID3D12StateObjectProperties(self.state_object)
        record = dx.D3D12_RAYTRACING_SHADER_TABLE_BYTE_ALIGNMENT
        table_data = bytearray(record * 4)
        for slot, export in enumerate(('RayGen', 'Miss', 'TriangleHitGroup', 'SphereHitGroup')):
            address = properties.GetShaderIdentifier(export)
            assert address, 'no export named %s' % export
            identifier = ctypes.string_at(address, dx.D3D12_SHADER_IDENTIFIER_SIZE_IN_BYTES)
            table_data[slot * record:slot * record + len(identifier)] = identifier
        self.shader_table = upload(device, table_data)
        start = self.shader_table.GetGPUVirtualAddress()
        self.dispatch = dx.D3D12_DISPATCH_RAYS_DESC(
            RayGenerationShaderRecord=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE(StartAddress=start, SizeInBytes=record),
            MissShaderTable=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE_AND_STRIDE(
                StartAddress=start + record, SizeInBytes=record, StrideInBytes=record),
            HitGroupTable=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE_AND_STRIDE(
                StartAddress=start + record * 2, SizeInBytes=record * 2, StrideInBytes=record),
            Width=self.width, Height=self.height, Depth=1)

    def create_outputs(self):
        self.heap = self.device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
            Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, NumDescriptors=2,
            Flags=dx.D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE))
        step = self.device.GetDescriptorHandleIncrementSize(dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)
        start = self.heap.GetCPUDescriptorHandleForHeapStart().ptr
        self.textures = []
        for i, fmt in enumerate((dx.DXGI_FORMAT_R32G32B32A32_FLOAT, dx.DXGI_FORMAT_R8G8B8A8_UNORM)):
            desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=self.width,
                                          Height=self.height, DepthOrArraySize=1, MipLevels=1, Format=fmt,
                                          Flags=dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
            desc.SampleDesc.Count = 1
            texture = self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                                          dx.D3D12_HEAP_FLAG_NONE, desc,
                                                          dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)
            self.device.CreateUnorderedAccessView(texture, None, dx.D3D12_UNORDERED_ACCESS_VIEW_DESC(
                Format=fmt, ViewDimension=dx.D3D12_UAV_DIMENSION_TEXTURE2D),
                dx.D3D12_CPU_DESCRIPTOR_HANDLE(start + i * step))
            self.textures.append(texture)
        self.accumulation, self.output = self.textures

    # -- frames -------------------------------------------------------------------------------------
    def wait_idle(self):
        self.fence_counter += 1
        self.queue.Signal(self.fence, self.fence_counter)
        self.fence.SetEventOnCompletion(self.fence_counter, None)

    def render(self, camera_constants):
        index = self.swap_chain.GetCurrentBackBufferIndex()
        # wait for the frame that used this allocator two frames ago
        if self.fence.GetCompletedValue() < self.fence_values[index]:
            self.fence.SetEventOnCompletion(self.fence_values[index], None)
        allocator, cl, back_buffer = self.allocators[index], self.command_list, self.back_buffers[index]
        allocator.Reset()
        cl.Reset(allocator)
        cl.SetPipelineState1(self.state_object)
        cl.SetComputeRootSignature(self.root_signature)  # DXR uses the compute root signature
        cl.SetDescriptorHeaps([self.heap])
        cl.SetComputeRootDescriptorTable(0, self.heap.GetGPUDescriptorHandleForHeapStart())
        cl.SetComputeRoot32BitConstants(1, len(camera_constants), camera_constants, 0)
        for i, resource in enumerate((self.tlas, self.vertex_buffer, self.index_buffer, self.tri_material_buffer,
                                      self.sphere_buffer, self.material_buffer)):
            cl.SetComputeRootShaderResourceView(2 + i, resource.GetGPUVirtualAddress())
        cl.DispatchRays(self.dispatch)

        cl.ResourceBarrier([
            transition(self.output, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS, dx.D3D12_RESOURCE_STATE_COPY_SOURCE),
            transition(back_buffer, dx.D3D12_RESOURCE_STATE_PRESENT, dx.D3D12_RESOURCE_STATE_COPY_DEST)])
        cl.CopyResource(back_buffer, self.output)
        cl.ResourceBarrier([
            transition(self.output, dx.D3D12_RESOURCE_STATE_COPY_SOURCE, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
            transition(back_buffer, dx.D3D12_RESOURCE_STATE_COPY_DEST, dx.D3D12_RESOURCE_STATE_PRESENT)])
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        self.swap_chain.Present(0, 0)
        self.fence_counter += 1
        self.queue.Signal(self.fence, self.fence_counter)
        self.fence_values[index] = self.fence_counter

    def save(self, path):
        """Read the tone mapped output back and save it with Pillow."""
        from PIL import Image
        self.wait_idle()
        footprints, rows, row_sizes, total = self.device.GetCopyableFootprints(self.output.GetDesc(), 0, 1, 0)
        readback = buffer(self.device, total, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        allocator, cl = self.allocators[0], self.command_list
        allocator.Reset()
        cl.Reset(allocator)
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
        self.wait_idle()
        pitch = footprints[0].Footprint.RowPitch
        data = ctypes.string_at(readback.Map(0), total)
        readback.Unmap(0)
        rows_data = b''.join(data[y * pitch:y * pitch + self.width * 4] for y in range(self.height))
        Image.frombytes('RGBA', (self.width, self.height), rows_data).convert('RGB').save(path)
        print('saved', path)


class OrbitCamera:
    def __init__(self, width, height):
        self.aspect = width / height
        self.target = numpy.array([0.0, 0.8, 0.0])
        self.yaw, self.pitch, self.distance = 0.55, 0.2, 8.5
        self.fov = math.radians(40)
        self.aperture = 0.06
        self.focus = None  # focus distance; None = the orbit target

    def basis(self):
        offset = numpy.array([math.sin(self.yaw) * math.cos(self.pitch), math.sin(self.pitch),
                              math.cos(self.yaw) * math.cos(self.pitch)])
        eye = self.target + offset * self.distance
        forward = -offset
        right = numpy.cross(forward, (0, 1, 0))
        right /= numpy.linalg.norm(right)
        up = numpy.cross(right, forward)
        return eye, forward, right, up

    def constants(self, frame, spp, bounces, sun):
        eye, forward, right, up = self.basis()
        scale = math.tan(self.fov / 2)
        values = numpy.zeros(20, numpy.float32)
        values[0:3], values[4:7], values[8:11], values[12:15], values[16:19] = (
            eye, forward, right * scale * self.aspect, up * scale, sun)
        values[7], values[11] = self.aperture, self.focus or self.distance
        ints = values.view(numpy.uint32)
        ints[3], ints[15], ints[19] = frame, spp, bounces
        return (ctypes.c_uint32 * 20).from_buffer_copy(ints.tobytes())

    def ray(self, x, y, width, height):
        eye, forward, right, up = self.basis()
        scale = math.tan(self.fov / 2)
        d = forward + (x / width * 2 - 1) * right * scale * self.aspect - (y / height * 2 - 1) * up * scale
        return eye, d / numpy.linalg.norm(d)


def pick_distance(eye, direction, spheres):
    """Distance along the view axis to what is under the mouse (spheres or the floor), for the focus."""
    best = -eye[1] / direction[1] if direction[1] < 0 else None
    for center, radius in spheres:
        o = eye - center
        b = numpy.dot(o, direction)
        disc = b * b - (numpy.dot(o, o) - radius * radius)
        if disc >= 0:
            t = -b - math.sqrt(disc)
            if t > 0 and (best is None or t < best):
                best = t
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--spp', type=int, default=2, help='samples per pixel per frame')
    ap.add_argument('--bounces', type=int, default=8)
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames')
    ap.add_argument('--screenshot', help='render --samples samples per pixel, save this PNG and exit')
    ap.add_argument('--samples', type=int, default=1024)
    ap.add_argument('--debug', action='store_true', help='enable the D3D12 debug layer and report its errors')
    args = ap.parse_args()
    if args.debug:
        dx.D3D12GetDebugInterface().EnableDebugLayer()

    root = tkinter.Tk()
    root.title('pydx12: DXR path tracer')
    frame_widget = tkinter.Frame(root, width=args.width, height=args.height)
    frame_widget.pack()
    root.resizable(False, False)
    root.update()

    renderer = Renderer(args.width, args.height, frame_widget.winfo_id())
    camera = OrbitCamera(args.width, args.height)
    spheres = [(numpy.array(s['center'], float), float(s['radius'])) for s in build_scene()[3]]
    sun = numpy.array([-0.62, 0.33, -0.7])
    sun /= numpy.linalg.norm(sun)

    state: dict = {'frame': 0, 'drag': None, 'orbit': False, 'closed': False, 'save': False}

    def reset():
        state['frame'] = 0

    def on_press(event):
        state['drag'] = (event.x, event.y)

    def on_drag(event):
        if state['drag']:
            dx_, dy_ = event.x - state['drag'][0], event.y - state['drag'][1]
            camera.yaw -= dx_ * 0.006
            camera.pitch = min(1.35, max(0.03, camera.pitch + dy_ * 0.006))
            state['drag'] = (event.x, event.y)
            reset()

    def on_wheel(event):
        camera.distance = min(30, max(2.5, camera.distance * (0.9 if event.delta > 0 else 1.1)))
        camera.focus = None
        reset()

    def on_focus(event):
        eye, direction = camera.ray(event.x, event.y, args.width, args.height)
        t = pick_distance(eye, direction, spheres)
        if t:
            camera.focus = t * numpy.dot(direction, camera.basis()[1])
            reset()

    def on_key(event):
        if event.keysym == 'bracketleft':
            camera.aperture = max(0.0, camera.aperture - 0.02)
        elif event.keysym == 'bracketright':
            camera.aperture += 0.02
        elif event.keysym == 'space':
            state['orbit'] = not state['orbit']
        elif event.keysym in ('s', 'S'):
            state['save'] = True
            return
        elif event.keysym == 'Escape':
            state['closed'] = True
            return
        reset()

    frame_widget.bind('<ButtonPress-1>', on_press)
    frame_widget.bind('<B1-Motion>', on_drag)
    frame_widget.bind('<ButtonPress-3>', on_focus)
    root.bind('<MouseWheel>', on_wheel)
    root.bind('<Key>', on_key)
    root.protocol('WM_DELETE_WINDOW', lambda: state.update(closed=True))

    frames = 0
    start = last_title = time.perf_counter()
    while not state['closed']:
        root.update()
        if state['orbit']:
            camera.yaw += 0.004
            reset()
        renderer.render(camera.constants(state['frame'], args.spp, args.bounces, sun))
        state['frame'] += 1
        frames += 1
        samples = state['frame'] * args.spp
        now = time.perf_counter()
        if now - last_title > 0.5:
            root.title('pydx12: DXR path tracer - %d samples/pixel - %.0f fps - drag, wheel, right click, '
                       '[ ] aperture, space, S' % (samples, frames / (now - start)))
            last_title = now
        if state['save']:
            renderer.save('pathtracer_%d.png' % samples)
            state['save'] = False
        if args.screenshot and samples >= args.samples:
            renderer.save(args.screenshot)
            break
        if args.frames and frames >= args.frames:
            break
    renderer.wait_idle()
    print('%d frames, %.1f fps' % (frames, frames / (time.perf_counter() - start)))
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
