"""Opacity micromaps (DXR 1.2): a ray traced forest where the hardware already knows where leaves are.

Foliage is the classic slow case for raytracing. Leaves are textured quads with an alpha mask, so every
ray that touches a quad has to run an any-hit shader that reads the texture and discards the transparent
part. A ray through a canopy can cross dozens of quads, and most of them are hits on empty space.

An opacity micromap stores the opacity of a triangle at a finer resolution: it splits the triangle into
4^level micro-triangles (in "bird curve" order) and marks each one opaque, transparent or unknown. Rays
that land on an opaque or transparent micro-triangle are resolved by the traversal itself; only the
unknown ones, on the edges of the leaves, still call the any-hit shader. The micromaps are built here
from the leaf texture: a micro-triangle is opaque or transparent only if every texel it touches is.

The scene: 100 trees, each a trunk with branches and a canopy of 650 leaf cards that share one texture
(and so two micromaps, one per triangle of the card), lit by a low sun with soft shadows, translucent
leaves, one bounce of sky light and progressive accumulation. Every any-hit invocation is counted per
pixel, and V shows the count as a heatmap. M switches the micromaps off (the instances keep the same
acceleration structures, with D3D12_RAYTRACING_INSTANCE_FLAG_DISABLE_OMMS), and the title compares GPU
time and any-hit invocations. --check renders the first frame both ways and compares them (the micromaps
must not change a single pixel), then times both, alternating frame by frame so they see the same GPU
clocks.

Mouse: drag to look around, wheel to walk. Keys: M micromaps, V view (shaded, heatmap, split), Space walk,
Escape quits.

Needs raytracing tier 1.2. The micromaps always remove the any-hit invocations (about 120 times fewer
here), but the time that saves depends on the hardware: NVIDIA RTX 40 and newer resolve micromaps in the
raytracing cores, while an RTX 3070 (DXR 1.2 driver, no micromap hardware) runs this scene in the same
time either way, its traversal doing the work this cheap any-hit shader would do. The heavier the any-hit
shader (real games sample mipmapped textures, run material code), the more the micromaps save.

Usage: python examples/micromaps.py [--trees 100] [--level 9] [--micromaps on|off]
                                    [--view shaded|heatmap|split] [--frames N] [--screenshot out.png]
                                    [--check] [--debug]
"""
import argparse
import ctypes
import math
import time
import tkinter

import numpy

import pydx12 as dx

WIDTH, HEIGHT = 1280, 720
TEX = 512        # leaf texture size
VARIANTS = 4     # different tree shapes, instanced around
SUN = numpy.array([-0.55, 0.32, 0.77])
SUN = SUN / numpy.linalg.norm(SUN)
VIEWS = ('shaded', 'heatmap', 'split')

SHADERS = r'''
#define PI 3.14159265
#define TEX %(tex)d

RaytracingAccelerationStructure Scene : register(t0);
Texture2D<float4> Leaf : register(t1);
StructuredBuffer<float4> TrunkNormals : register(t2);  // three per triangle (smooth)
StructuredBuffer<float4> LeafNormals : register(t3);   // one per triangle
RWTexture2D<float4> Accumulation : register(u0);
RWTexture2D<unorm float4> Output : register(u1);
RWTexture2D<uint> Heat : register(u2);                 // any-hit invocations of this frame, per pixel
RWByteAddressBuffer Stats : register(u3);              // any-hit invocations of this frame, total

cbuffer Camera : register(b0)
{
    float3 origin; uint frame;
    float3 forward; uint view;    // 0 shaded, 1 heatmap, 2 split
    float3 right; float heatScale;
    float3 up; uint pad0;
    float3 sunDirection; uint pad1;
};

#define TRUNK 1
#define LEAF 2
#define GROUND 3

struct Payload { float3 normal; float t; float2 uv; uint kind; uint pad; };

// ---- random numbers (PCG hash) -----------------------------------------------------------------
float Random(inout uint state)
{
    state = state * 747796405u + 2891336453u;
    uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
    return ((word >> 22u) ^ word) / 4294967296.0;
}

float3 CosineHemisphere(float3 n, inout uint state)
{
    float a = Random(state) * 2 * PI, r = sqrt(Random(state));
    float3 t = normalize(abs(n.y) < 0.99 ? cross(n, float3(0, 1, 0)) : cross(n, float3(1, 0, 0)));
    float3 b = cross(n, t);
    return normalize(t * r * cos(a) + b * r * sin(a) + n * sqrt(1 - r * r));
}

float Hash(float2 p)
{
    return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453);
}

float Noise(float2 p)
{
    float2 i = floor(p), f = frac(p);
    f = f * f * (3 - 2 * f);
    return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + 1), f.x), f.y);
}

// a leaf card is two triangles; their texture coordinates follow from the triangle's parity
float2 LeafUV(uint primitive, float2 barycentrics)
{
    return (primitive & 1) ? 1 - barycentrics : barycentrics;
}

float4 LeafTexel(float2 uv)
{
    return Leaf.Load(int3(min(uint2(uv * TEX), TEX - 1), 0));  // point sampled, like the micromaps
}

// ---- shaders ------------------------------------------------------------------------------------
[shader("miss")]
void Miss(inout Payload payload)
{
    payload.t = -1;
}

[shader("closesthit")]
void TrunkHit(inout Payload payload, BuiltInTriangleIntersectionAttributes attributes)
{
    uint base = InstanceID() + PrimitiveIndex() * 3;
    float3 b = float3(1 - attributes.barycentrics.x - attributes.barycentrics.y, attributes.barycentrics);
    float3 n = TrunkNormals[base].xyz * b.x + TrunkNormals[base + 1].xyz * b.y + TrunkNormals[base + 2].xyz * b.z;
    payload.normal = normalize(mul(ObjectToWorld3x4(), float4(n, 0)));
    payload.t = RayTCurrent();
    payload.kind = TRUNK;
}

[shader("closesthit")]
void LeafHit(inout Payload payload, BuiltInTriangleIntersectionAttributes attributes)
{
    float3 n = LeafNormals[InstanceID() + PrimitiveIndex()].xyz;
    payload.normal = normalize(mul(ObjectToWorld3x4(), float4(n, 0)));
    payload.t = RayTCurrent();
    payload.uv = LeafUV(PrimitiveIndex(), attributes.barycentrics);
    payload.kind = LEAF;
}

// the alpha test: with micromaps it only runs on micro-triangles marked unknown
[shader("anyhit")]
void LeafAnyHit(inout Payload payload, BuiltInTriangleIntersectionAttributes attributes)
{
    InterlockedAdd(Heat[DispatchRaysIndex().xy], 1);
    if (LeafTexel(LeafUV(PrimitiveIndex(), attributes.barycentrics)).a < 0.5)
        IgnoreHit();
}

Payload Trace(float3 from, float3 direction, float distance, uint flags)
{
    RayDesc ray;
    ray.Origin = from;
    ray.Direction = direction;
    ray.TMin = 0.001;
    ray.TMax = distance;
    Payload payload;
    payload.t = 1;  // stays positive when a shadow ray hits something (no closest hit shader runs)
    payload.kind = 0;
    payload.normal = 0;
    payload.uv = 0;
    payload.pad = 0;
    TraceRay(Scene, flags, 0xFF, 0, 1, 0, ray, payload);
    return payload;
}

bool Occluded(float3 from, float3 direction, float distance)
{
    if (direction.y < 0 && -from.y / direction.y < distance)
        return true;  // the ground
    return Trace(from, direction, distance,
                 RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH | RAY_FLAG_SKIP_CLOSEST_HIT_SHADER).t > 0;
}

float3 Sky(float3 direction)
{
    float h = saturate(direction.y);
    float3 sky = lerp(float3(0.85, 0.80, 0.70), float3(0.25, 0.45, 0.85), pow(h, 0.5));
    float sun = dot(direction, sunDirection);
    sky += float3(1.0, 0.75, 0.45) * pow(saturate(sun), 8) * 0.6;
    sky += float3(1.0, 0.9, 0.7) * smoothstep(0.9993, 0.9997, sun) * 40;
    return sky;
}

float3 Shade(float3 from, float3 direction, inout uint seed)
{
    const float far = 400;
    float ground = direction.y < 0 ? -from.y / direction.y : far;
    Payload hit = Trace(from, direction, min(ground, far), RAY_FLAG_NONE);
    float t = hit.t;
    if (t < 0)
    {
        if (ground >= far)
            return Sky(direction);
        t = ground;
        hit.kind = GROUND;
        hit.normal = float3(0, 1, 0);
    }
    float3 p = from + direction * t;
    float3 n = dot(hit.normal, direction) > 0 ? -hit.normal : hit.normal;

    float3 albedo;
    if (hit.kind == LEAF)
        albedo = pow(LeafTexel(hit.uv).rgb, 2.2);
    else if (hit.kind == TRUNK)
        albedo = float3(0.22, 0.15, 0.10) * (0.6 + 0.6 * Noise(float2(atan2(p.z, p.x) * 8, p.y * 12)));
    else
    {
        float grass = Noise(p.xz * 0.4) * 0.6 + Noise(p.xz * 3.1) * 0.4;
        albedo = lerp(float3(0.10, 0.16, 0.04), float3(0.22, 0.26, 0.08), grass);
    }

    // the sun, a little wider than a point for soft shadows; leaves also let light through
    float3 sunColor = float3(1.0, 0.86, 0.66) * 3.2;
    float3 jitter = float3(Random(seed), Random(seed), Random(seed)) * 2 - 1;
    float3 l = normalize(sunDirection + jitter * 0.015);
    float facing = dot(n, l);
    float3 light = 0;
    if (facing > 0 || hit.kind == LEAF)
    {
        if (!Occluded(p + l * 0.002, l, 1000))
            light = sunColor * (facing > 0 ? facing : -facing * (hit.kind == LEAF ? 0.6 : 0));
    }

    // one bounce of sky light: what the cosine weighted ray sees, or a little bounce light if blocked
    float3 bounce = CosineHemisphere(n, seed);
    float3 ambient = Occluded(p + n * 0.002, bounce, 12) ? float3(0.05, 0.06, 0.03) : Sky(bounce) * 0.9;
    float3 color = albedo * (light + ambient);

    float fog = 1 - exp(-t * 0.005);
    return lerp(color, Sky(normalize(float3(direction.x, 0.08, direction.z))) * 0.7, fog);
}

float3 Turbo(float x)
{
    const float4 r4 = float4(0.13572138, 4.61539260, -42.66032258, 132.13108234);
    const float4 g4 = float4(0.09140261, 2.19418839, 4.84296658, -14.18503333);
    const float4 b4 = float4(0.10667330, 12.64194608, -60.58204836, 110.36276771);
    const float2 r2 = float2(-152.94239396, 59.28637943);
    const float2 g2 = float2(4.27729857, 2.82956604);
    const float2 b2 = float2(-89.90310912, 27.34824973);
    x = saturate(x);
    float4 v4 = float4(1, x, x * x, x * x * x);
    float2 v2 = v4.zw * v4.z;
    return float3(dot(v4, r4) + dot(v2, r2), dot(v4, g4) + dot(v2, g2), dot(v4, b4) + dot(v2, b2));
}

float3 Tonemap(float3 x)  // ACES (Narkowicz) and gamma
{
    x = saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
    return pow(x, 1 / 2.2);
}

[shader("raygeneration")]
void RayGen()
{
    uint2 pixel = DispatchRaysIndex().xy, size = DispatchRaysDimensions().xy;
    uint seed = (pixel.x * 1973 + pixel.y * 9277 + frame * 26699) | 1;
    Heat[pixel] = 0;
    float2 jitter = frame == 0 ? 0.5 : float2(Random(seed), Random(seed));
    float2 ndc = (pixel + jitter) / size * 2 - 1;
    float3 color = Shade(origin, normalize(forward + ndc.x * right - ndc.y * up), seed);

    float4 sum = (frame == 0 ? 0 : Accumulation[pixel]) + float4(color, 1);
    Accumulation[pixel] = sum;
    uint hits = Heat[pixel];
    float3 shaded = Tonemap(sum.rgb / sum.a);
    // logarithmic: 1 any-hit invocation is dark blue, heatScale and more are red
    float3 heat = hits == 0 ? float3(0.02, 0.02, 0.05) : Turbo(0.15 + 0.85 * log2(1 + hits) / log2(1 + heatScale));
    Output[pixel] = float4(view == 0 || (view == 2 && pixel.x < size.x / 2) ? shaded : heat, 1);

    uint total = WaveActiveSum(hits);
    if (WaveIsFirstLane())
        Stats.InterlockedAdd(0, total);
}
''' % {'tex': TEX}


# ---- the leaf texture and the micromaps ----------------------------------------------------------
def leaf_texture(rng):
    """A twig with leaves, alpha tested: RGBA, TEX x TEX."""
    y, x = numpy.mgrid[0:TEX, 0:TEX] / TEX
    rgba = numpy.zeros((TEX, TEX, 4), numpy.float32)
    twig_x = 0.5 + 0.04 * numpy.sin(y * 5)
    twig = (numpy.abs(x - twig_x) < 0.004 + 0.006 * y) & (y > 0.08) & (y < 0.99)
    rgba[twig] = (0.30, 0.20, 0.11, 1)
    for i in range(40):
        base_y = 0.1 + 0.84 * (i / 39) + rng.uniform(-0.02, 0.02)
        side = 1 if i % 2 else -1
        base = numpy.array([0.5 + 0.04 * math.sin(base_y * 5), base_y])
        angle = side * rng.uniform(0.5, 1.1) * (1 - 0.4 * (1 - base_y))
        axis = numpy.array([math.sin(angle), -math.cos(angle)])  # up the texture is -y
        perp = numpy.array([-axis[1], axis[0]])
        length = rng.uniform(0.2, 0.3) * (0.7 + 0.3 * base_y)
        width = length * rng.uniform(0.3, 0.4)
        s = ((x - base[0]) * axis[0] + (y - base[1]) * axis[1]) / length
        t = ((x - base[0]) * perp[0] + (y - base[1]) * perp[1]) / width
        inside = (s > 0) & (s < 1) & (numpy.abs(t) < numpy.sin(numpy.pi * numpy.clip(s, 0, 1)) ** 0.7 * (1 - 0.35 * s))
        green = numpy.array([rng.uniform(0.16, 0.30), rng.uniform(0.38, 0.55), rng.uniform(0.06, 0.14)])
        if rng.random() < 0.18:
            green = numpy.array([rng.uniform(0.45, 0.6), rng.uniform(0.5, 0.6), 0.1])  # a few yellowing leaves
        shade = (0.8 + 0.3 * s)[..., None] * green
        shade = numpy.where((numpy.abs(t) < 0.06)[..., None], shade * 0.7, shade)  # the midrib
        rgba[inside, :3] = shade[inside]
        rgba[inside, 3] = 1
    return (numpy.clip(rgba, 0, 1) * 255).astype(numpy.uint8)


def bird_curve(level):
    """Corners (u, v) of every micro-triangle of a subdivision level, in micromap order: (4**level, 3, 2).

    u and v are the barycentrics of the triangle's second and third vertex, like the barycentrics a hit
    shader gets."""
    if level == 0:
        return numpy.array([[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]])
    index = numpy.arange(4 ** level, dtype=numpy.uint32)

    def even_bits(x):
        x = x & 0x55555555
        x = (x | (x >> 1)) & 0x33333333
        x = (x | (x >> 2)) & 0x0f0f0f0f
        x = (x | (x >> 4)) & 0x00ff00ff
        return (x | (x >> 8)) & 0x0000ffff

    def prefix_xor(x):
        x = x ^ ((x >> 1) & 0x7fff7fff)
        x = x ^ ((x >> 2) & 0x3fff3fff)
        x = x ^ ((x >> 4) & 0x0fff0fff)
        return x ^ ((x >> 8) & 0x00ff00ff)

    b0, b1 = even_bits(index), even_bits(index >> 1)
    fx, fy = prefix_xor(b0), prefix_xor(b0 & ~b1)
    t = fy ^ b1
    mask = numpy.uint32((1 << level) - 1)
    u = ((fx & ~t) | (b0 & ~t) | (~b0 & ~fx & t)) & mask
    v = (fy ^ b0) & mask
    w = ((~fx & ~t) | (b0 & ~t) | (~b0 & fx & t)) & mask
    upright = ((u ^ v ^ w) & 1).astype(bool)
    u = numpy.where(upright, u, u + 1).astype(numpy.float64)
    v = numpy.where(upright, v, v + 1).astype(numpy.float64)
    step = numpy.where(upright, 1.0, -1.0)
    corners = numpy.stack([numpy.stack([u, v], 1), numpy.stack([u + step, v], 1), numpy.stack([u, v + step], 1)], 1)
    return corners / (1 << level)


def micromap(opaque, level, parity):
    """The 4-state micromap of one triangle of a leaf card, packed 2 bits per micro-triangle."""
    corners = bird_curve(level)
    uv = corners if parity == 0 else 1 - corners  # LeafUV() in the shader
    texels = numpy.clip(numpy.floor(uv * TEX).astype(numpy.int64), 0, TEX - 1)
    x0, x1 = texels[..., 0].min(1), texels[..., 0].max(1)
    y0, y1 = texels[..., 1].min(1), texels[..., 1].max(1)
    # count the opaque texels in each micro-triangle's bounding box with a summed area table
    table = numpy.zeros((TEX + 1, TEX + 1), numpy.int64)
    table[1:, 1:] = opaque.astype(numpy.int64).cumsum(0).cumsum(1)
    count = table[y1 + 1, x1 + 1] - table[y0, x1 + 1] - table[y1 + 1, x0] + table[y0, x0]
    area = (x1 - x0 + 1) * (y1 - y0 + 1)
    states = numpy.full(len(corners), dx.D3D12_RAYTRACING_OPACITY_MICROMAP_STATE_UNKNOWN_OPAQUE, numpy.uint8)
    states[count == area] = dx.D3D12_RAYTRACING_OPACITY_MICROMAP_STATE_OPAQUE
    states[count == 0] = dx.D3D12_RAYTRACING_OPACITY_MICROMAP_STATE_TRANSPARENT
    packed = states.reshape(-1, 4) << numpy.array([0, 2, 4, 6], numpy.uint8)
    return numpy.bitwise_or.reduce(packed, axis=1).astype(numpy.uint8), numpy.bincount(states, minlength=4)


# ---- the trees -----------------------------------------------------------------------------------
def cylinder(p0, p1, r0, r1, segments=10):
    """Vertices, normals and triangles of an open cone from p0 to p1."""
    axis = p1 - p0
    axis_n = axis / numpy.linalg.norm(axis)
    side = numpy.cross(axis_n, [0.0, 0.0, 1.0] if abs(axis_n[2]) < 0.9 else [1.0, 0.0, 0.0])
    side /= numpy.linalg.norm(side)
    other = numpy.cross(axis_n, side)
    angles = numpy.linspace(0, 2 * math.pi, segments, endpoint=False)
    ring = numpy.cos(angles)[:, None] * side + numpy.sin(angles)[:, None] * other
    vertices = numpy.concatenate([p0 + ring * r0, p1 + ring * r1])
    normals = numpy.concatenate([ring, ring])
    i = numpy.arange(segments)
    j = (i + 1) % segments
    triangles = numpy.concatenate([numpy.stack([i, j, i + segments], 1),
                                   numpy.stack([j, j + segments, i + segments], 1)])
    return vertices, normals, triangles


def tree(rng):
    """A trunk with branches (vertices, normals, triangles) and leaf cards (vertices, triangles, normals)."""
    height = rng.uniform(7, 10)
    lean = numpy.array([rng.uniform(-0.4, 0.4), 0, rng.uniform(-0.4, 0.4)])
    top = numpy.array([0, height, 0]) + lean
    parts = [cylinder(numpy.zeros(3), top, 0.32, 0.07, 12)]
    tips = [top]
    for k in range(6):
        h = rng.uniform(0.4, 0.8)
        start = top * h
        a = rng.uniform(0, 2 * math.pi)
        direction = numpy.array([math.cos(a), rng.uniform(0.5, 1.1), math.sin(a)])
        end = start + direction / numpy.linalg.norm(direction) * rng.uniform(1.8, 3.2)
        parts.append(cylinder(start, end, 0.1, 0.03, 7))
        tips.append(end)
    vertices, normals, triangles, offset = [], [], [], 0
    for v, n, t in parts:
        vertices.append(v)
        normals.append(n)
        triangles.append(t + offset)
        offset += len(v)
    trunk = (numpy.concatenate(vertices), numpy.concatenate(normals), numpy.concatenate(triangles))

    # leaf cards around the branch tips and the top of the trunk
    cards = 650
    centers = []
    for _ in range(cards):
        tip = tips[rng.integers(len(tips))]
        offset_dir = rng.normal(size=3)
        offset_dir /= numpy.linalg.norm(offset_dir)
        centers.append(tip + offset_dir * rng.uniform(0.15, 1.0) ** 0.6 * 2.4 * numpy.array([1, 0.75, 1]))
    centers = numpy.array(centers)
    normal = rng.normal(size=(cards, 3))
    normal /= numpy.linalg.norm(normal, axis=1, keepdims=True)
    helper = numpy.where(numpy.abs(normal[:, 1:2]) < 0.9, [[0.0, 1.0, 0.0]], [[1.0, 0.0, 0.0]])
    across = numpy.cross(normal, helper)
    across /= numpy.linalg.norm(across, axis=1, keepdims=True)
    along = numpy.cross(across, normal)
    size = rng.uniform(0.9, 1.4, (cards, 1))

    def corner(u, v):  # texture coordinates (u, v): v grows downwards in the texture
        return centers + (u - 0.5) * across * size - (v - 0.5) * along * size
    leaf_vertices = numpy.stack([corner(0, 0), corner(1, 0), corner(0, 1), corner(1, 1)], 1).reshape(-1, 3)
    base = numpy.arange(cards)[:, None] * 4
    # triangle 0: uv (0,0) (1,0) (0,1); triangle 1: uv (1,1) (0,1) (1,0), see LeafUV() in the shader
    leaf_triangles = (base + numpy.array([[0, 1, 2], [3, 2, 1]]).reshape(1, 6)).reshape(-1, 3)
    leaf_normals = numpy.repeat(normal, 2, axis=0)
    return trunk, (leaf_vertices, leaf_triangles, leaf_normals)


# ---- D3D12 helpers -------------------------------------------------------------------------------
def compile_library(source):
    compiler = dx.DxcCreateInstance(dx.CLSID_DxcCompiler, dx.IDxcCompiler3)
    result = compiler.Compile(dx.DxcBuffer(Ptr=source.encode('utf-8')), ['-T', 'lib_6_6', '-O3'], None,
                              dx.IDxcResult)
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


def uav_barrier(resource):
    b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_UAV)
    b.UAV.pResource = resource
    return b


class Renderer:
    def __init__(self, hwnd, trees, level):
        factory = dx.CreateDXGIFactory2()
        adapter = factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE)
        self.device = dx.D3D12CreateDevice(adapter, dx.D3D_FEATURE_LEVEL_12_1, dx.ID3D12Device5)
        options = dx.D3D12_FEATURE_DATA_D3D12_OPTIONS5()
        self.device.CheckFeatureSupport(dx.D3D12_FEATURE_D3D12_OPTIONS5, ctypes.byref(options),
                                        ctypes.sizeof(options))
        if options.RaytracingTier < dx.D3D12_RAYTRACING_TIER_1_2:
            raise SystemExit('this GPU or driver has no opacity micromaps (raytracing tier 1.2)')
        print('%s, raytracing tier %d.%d' % ((adapter.GetDesc1().Description,) + divmod(options.RaytracingTier, 10)))
        device = self.device
        self.queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
        self.allocator = device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
        self.cl = dx.ID3D12GraphicsCommandList4(
            device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, self.allocator))
        self.fence = device.CreateFence()
        self.fence_value = 0
        desc = dx.DXGI_SWAP_CHAIN_DESC1(Width=WIDTH, Height=HEIGHT, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                        BufferUsage=dx.DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=2,
                                        SwapEffect=dx.DXGI_SWAP_EFFECT_FLIP_DISCARD)
        desc.SampleDesc.Count = 1
        self.swap_chain = dx.IDXGISwapChain3(factory.CreateSwapChainForHwnd(self.queue, hwnd, desc))
        self.back_buffers = [self.swap_chain.GetBuffer(i) for i in range(2)]
        self.keep: list = []  # upload buffers and scratch memory used while building

        self.create_outputs()
        self.build_scene(trees, level)
        self.build_pipeline()

    # -- resources ----------------------------------------------------------------------------------
    def buffer(self, size, heap=dx.D3D12_HEAP_TYPE_UPLOAD, state=dx.D3D12_RESOURCE_STATE_GENERIC_READ,
               flags=dx.D3D12_RESOURCE_FLAG_NONE):
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=max(size, 1), Height=1,
                                      DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR,
                                      Flags=flags)
        desc.SampleDesc.Count = 1
        return self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=heap), dx.D3D12_HEAP_FLAG_NONE,
                                                   desc, state)

    def upload(self, array):
        """Static data lives in an upload heap: the GPU reads it directly."""
        array = numpy.ascontiguousarray(array)
        resource = self.buffer(array.nbytes)
        ctypes.memmove(resource.Map(0), array.ctypes.data, array.nbytes)
        resource.Unmap(0)
        return resource

    def default_buffer(self, size, state=dx.D3D12_RESOURCE_STATE_RAYTRACING_ACCELERATION_STRUCTURE):
        return self.buffer(size, dx.D3D12_HEAP_TYPE_DEFAULT, state, dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)

    def wait(self):
        self.fence_value += 1
        self.queue.Signal(self.fence, self.fence_value)
        self.fence.SetEventOnCompletion(self.fence_value, None)

    def create_outputs(self):
        device = self.device
        self.heap = device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
            Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, NumDescriptors=4,
            Flags=dx.D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE))
        self.step = device.GetDescriptorHandleIncrementSize(dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)
        start = self.heap.GetCPUDescriptorHandleForHeapStart().ptr
        self.textures = []
        for i, fmt in enumerate((dx.DXGI_FORMAT_R32G32B32A32_FLOAT, dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                 dx.DXGI_FORMAT_R32_UINT)):
            desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=WIDTH,
                                          Height=HEIGHT, DepthOrArraySize=1, MipLevels=1, Format=fmt,
                                          Flags=dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS)
            desc.SampleDesc.Count = 1
            texture = device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                                     dx.D3D12_HEAP_FLAG_NONE, desc,
                                                     dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)
            device.CreateUnorderedAccessView(texture, None, dx.D3D12_UNORDERED_ACCESS_VIEW_DESC(
                Format=fmt, ViewDimension=dx.D3D12_UAV_DIMENSION_TEXTURE2D),
                dx.D3D12_CPU_DESCRIPTOR_HANDLE(start + i * self.step))
            self.textures.append(texture)
        self.accumulation, self.output, self.heat = self.textures
        self.stats = self.default_buffer(16, dx.D3D12_RESOURCE_STATE_COMMON)
        self.zeros = self.upload(numpy.zeros(4, numpy.uint32))
        self.stats_readback = self.buffer(16, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        self.timestamps = device.CreateQueryHeap(dx.D3D12_QUERY_HEAP_DESC(Type=dx.D3D12_QUERY_HEAP_TYPE_TIMESTAMP,
                                                                          Count=2))
        self.timestamp_readback = self.buffer(16, dx.D3D12_HEAP_TYPE_READBACK, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        self.ticks = self.queue.GetTimestampFrequency()

    def upload_texture(self, pixels):
        device, cl = self.device, self.cl
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_TEXTURE2D, Width=TEX, Height=TEX,
                                      DepthOrArraySize=1, MipLevels=1, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM)
        desc.SampleDesc.Count = 1
        texture = device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_DEFAULT),
                                                 dx.D3D12_HEAP_FLAG_NONE, desc, dx.D3D12_RESOURCE_STATE_COPY_DEST)
        footprints, _, _, total = device.GetCopyableFootprints(desc, 0, 1, 0)
        staging = self.buffer(total)
        pitch = footprints[0].Footprint.RowPitch
        address = staging.Map(0)
        for row in range(TEX):
            ctypes.memmove(address + row * pitch, pixels[row].ctypes.data, TEX * 4)
        staging.Unmap(0)
        dst = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=texture, Type=dx.D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX)
        src = dx.D3D12_TEXTURE_COPY_LOCATION(pResource=staging, Type=dx.D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT)
        src.PlacedFootprint = footprints[0]
        cl.CopyTextureRegion(dst, 0, 0, 0, src, None)
        cl.ResourceBarrier([transition(texture, dx.D3D12_RESOURCE_STATE_COPY_DEST,
                                       dx.D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE)])
        self.keep.append(staging)
        device.CreateShaderResourceView(texture, dx.D3D12_SHADER_RESOURCE_VIEW_DESC(
            Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM, ViewDimension=dx.D3D12_SRV_DIMENSION_TEXTURE2D,
            Shader4ComponentMapping=dx.D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING,
            Texture2D=dx.D3D12_TEX2D_SRV(MipLevels=1)),
            dx.D3D12_CPU_DESCRIPTOR_HANDLE(self.heap.GetCPUDescriptorHandleForHeapStart().ptr + 3 * self.step))
        return texture

    def build(self, inputs):
        """Build an acceleration structure (or a micromap array) and return it."""
        info = self.device.GetRaytracingAccelerationStructurePrebuildInfo(inputs)
        result = self.default_buffer(info.ResultDataMaxSizeInBytes)
        scratch = self.default_buffer(info.ScratchDataSizeInBytes, dx.D3D12_RESOURCE_STATE_COMMON)
        self.keep.append(scratch)
        self.cl.BuildRaytracingAccelerationStructure(dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_DESC(
            DestAccelerationStructureData=result.GetGPUVirtualAddress(), Inputs=inputs,
            ScratchAccelerationStructureData=scratch.GetGPUVirtualAddress()))
        self.cl.ResourceBarrier([uav_barrier(result)])
        return result

    # -- the scene ----------------------------------------------------------------------------------
    def build_scene(self, trees, level):
        rng = numpy.random.default_rng(7)
        cl = self.cl
        pixels = leaf_texture(rng)
        self.leaf_texture = self.upload_texture(pixels)

        # the micromaps: one per triangle of a leaf card, shared by every card
        start = time.perf_counter()
        maps, states = zip(*(micromap(pixels[..., 3] >= 128, level, parity) for parity in (0, 1)))
        counts = sum(states)
        print('micromaps: 2 x %d micro-triangles (level %d), %.1f%% opaque, %.1f%% transparent, %.1f%% unknown, '
              'built in %.2f s' % (4 ** level, level, *(counts[[1, 0, 3]] * 100.0 / counts.sum()),
                                   time.perf_counter() - start))
        self.micromap_data = self.upload(numpy.concatenate(maps))
        descs = (dx.D3D12_RAYTRACING_OPACITY_MICROMAP_DESC * 2)()
        for i in range(2):
            descs[i].ByteOffset = i * len(maps[0])
            descs[i].SubdivisionLevel = level
            descs[i].Format = dx.D3D12_RAYTRACING_OPACITY_MICROMAP_FORMAT_OC1_4_STATE
        self.micromap_descs = self.upload(numpy.frombuffer(bytes(descs), numpy.uint8))
        histogram = dx.D3D12_RAYTRACING_OPACITY_MICROMAP_HISTOGRAM_ENTRY(
            Count=2, SubdivisionLevel=level, Format=dx.D3D12_RAYTRACING_OPACITY_MICROMAP_FORMAT_OC1_4_STATE)
        array_desc = dx.D3D12_RAYTRACING_OPACITY_MICROMAP_ARRAY_DESC(
            NumOmmHistogramEntries=1, pOmmHistogram=ctypes.pointer(histogram),
            InputBuffer=self.micromap_data.GetGPUVirtualAddress(),
            PerOmmDescs=dx.D3D12_GPU_VIRTUAL_ADDRESS_AND_STRIDE(
                StartAddress=self.micromap_descs.GetGPUVirtualAddress(),
                StrideInBytes=ctypes.sizeof(dx.D3D12_RAYTRACING_OPACITY_MICROMAP_DESC)))
        inputs = dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
            Type=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_OPACITY_MICROMAP_ARRAY,
            Flags=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_TRACE, NumDescs=1)
        inputs.pOpacityMicromapArrayDesc = ctypes.pointer(array_desc)
        self.micromap_array = self.build(inputs)

        # tree shapes: an opaque trunk BLAS and a leaf BLAS whose triangles point at the micromaps
        trunk_normals, leaf_normals = [], []
        self.trunk_blas, self.leaf_blas, trunk_base, leaf_base = [], [], [], []
        leaf_triangles_total = 0
        for _ in range(VARIANTS):
            (tv, tn, tt), (lv, lt, ln) = tree(rng)
            trunk_base.append(sum(len(n) for n in trunk_normals))
            trunk_normals.append(numpy.pad(tn[tt].reshape(-1, 3), ((0, 0), (0, 1))))
            leaf_base.append(sum(len(n) for n in leaf_normals))
            leaf_normals.append(numpy.pad(ln, ((0, 0), (0, 1))))
            leaf_triangles_total += len(lt)

            vb, ib = self.upload(tv.astype(numpy.float32)), self.upload(tt.astype(numpy.uint32))
            geometry = dx.D3D12_RAYTRACING_GEOMETRY_DESC(Type=dx.D3D12_RAYTRACING_GEOMETRY_TYPE_TRIANGLES,
                                                         Flags=dx.D3D12_RAYTRACING_GEOMETRY_FLAG_OPAQUE)
            geometry.Triangles = self.triangles(vb, len(tv), ib, tt.size)
            self.trunk_blas.append(self.build_blas(geometry))
            self.keep += [vb, ib]

            vb, ib = self.upload(lv.astype(numpy.float32)), self.upload(lt.astype(numpy.uint32))
            indices = self.upload(numpy.arange(len(lt), dtype=numpy.uint16) & 1)  # micromap of each triangle
            triangles = self.triangles(vb, len(lv), ib, lt.size)
            linkage = dx.D3D12_RAYTRACING_GEOMETRY_OMM_LINKAGE_DESC(
                OpacityMicromapIndexBuffer=dx.D3D12_GPU_VIRTUAL_ADDRESS_AND_STRIDE(
                    StartAddress=indices.GetGPUVirtualAddress(), StrideInBytes=2),
                OpacityMicromapIndexFormat=dx.DXGI_FORMAT_R16_UINT,
                OpacityMicromapArray=self.micromap_array.GetGPUVirtualAddress())
            geometry = dx.D3D12_RAYTRACING_GEOMETRY_DESC(Type=dx.D3D12_RAYTRACING_GEOMETRY_TYPE_OMM_TRIANGLES,
                                                         Flags=dx.D3D12_RAYTRACING_GEOMETRY_FLAG_NONE)
            geometry.OmmTriangles = dx.D3D12_RAYTRACING_GEOMETRY_OMM_TRIANGLES_DESC(
                pTriangles=ctypes.pointer(triangles), pOmmLinkage=ctypes.pointer(linkage))
            self.leaf_blas.append(self.build_blas(geometry))
            self.keep += [vb, ib, indices]
        self.trunk_normals = self.upload(numpy.concatenate(trunk_normals).astype(numpy.float32))
        self.leaf_normals = self.upload(numpy.concatenate(leaf_normals).astype(numpy.float32))

        # the forest: two instances per tree (trunk, leaves), and the same forest with micromaps disabled
        positions = []
        while len(positions) < trees:
            p = rng.uniform(-45, 45, 2)
            if numpy.hypot(*(p - (0, -12))) > 5 and all(numpy.hypot(*(p - q)) > 3.2 for q in positions):
                positions.append(p)
        yaws, scales = rng.uniform(0, 2 * math.pi, trees), rng.uniform(0.8, 1.25, trees)
        self.tlas = []
        for disable in (False, True):
            instances = (dx.D3D12_RAYTRACING_INSTANCE_DESC * (2 * trees))()
            for i, (x, z) in enumerate(positions):
                variant = i % VARIANTS
                yaw, scale = yaws[i], scales[i]
                rotation = numpy.array([[math.cos(yaw), 0, math.sin(yaw)], [0, 1, 0],
                                        [-math.sin(yaw), 0, math.cos(yaw)]]) * scale
                for k, (blas, base, hit_group) in enumerate(((self.trunk_blas[variant], trunk_base[variant], 0),
                                                             (self.leaf_blas[variant], leaf_base[variant], 1))):
                    instance = instances[2 * i + k]
                    for row in range(3):
                        for col in range(3):
                            instance.Transform[row][col] = rotation[row][col]
                    instance.Transform[0][3], instance.Transform[2][3] = x, z
                    instance.InstanceID = base
                    instance.InstanceMask = 0xFF
                    instance.InstanceContributionToHitGroupIndex = hit_group
                    instance.Flags = (dx.D3D12_RAYTRACING_INSTANCE_FLAG_TRIANGLE_CULL_DISABLE |
                                      (dx.D3D12_RAYTRACING_INSTANCE_FLAG_DISABLE_OMMS if disable and k else 0))
                    instance.AccelerationStructure = blas.GetGPUVirtualAddress()
            buffer = self.upload(numpy.frombuffer(bytes(instances), numpy.uint8))
            self.keep.append(buffer)
            inputs = dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
                Type=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_TOP_LEVEL,
                Flags=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_TRACE,
                NumDescs=2 * trees, DescsLayout=dx.D3D12_ELEMENTS_LAYOUT_ARRAY)
            inputs.InstanceDescs = buffer.GetGPUVirtualAddress()
            self.tlas.append(self.build(inputs))
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        self.wait()
        self.keep.clear()  # scratch and staging memory are no longer needed
        print('forest: %d trees, %d leaf cards' % (trees, leaf_triangles_total // 2 * trees // VARIANTS))

    def triangles(self, vertex_buffer, vertex_count, index_buffer, index_count):
        return dx.D3D12_RAYTRACING_GEOMETRY_TRIANGLES_DESC(
            IndexFormat=dx.DXGI_FORMAT_R32_UINT, VertexFormat=dx.DXGI_FORMAT_R32G32B32_FLOAT,
            IndexCount=index_count, VertexCount=vertex_count, IndexBuffer=index_buffer.GetGPUVirtualAddress(),
            VertexBuffer=dx.D3D12_GPU_VIRTUAL_ADDRESS_AND_STRIDE(StartAddress=vertex_buffer.GetGPUVirtualAddress(),
                                                                 StrideInBytes=12))

    def build_blas(self, geometry):
        inputs = dx.D3D12_BUILD_RAYTRACING_ACCELERATION_STRUCTURE_INPUTS(
            Type=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_TYPE_BOTTOM_LEVEL,
            Flags=dx.D3D12_RAYTRACING_ACCELERATION_STRUCTURE_BUILD_FLAG_PREFER_FAST_TRACE,
            NumDescs=1, DescsLayout=dx.D3D12_ELEMENTS_LAYOUT_ARRAY)
        inputs.pGeometryDescs = ctypes.pointer(geometry)
        return self.build(inputs)

    # -- the pipeline -------------------------------------------------------------------------------
    def build_pipeline(self):
        device = self.device
        table = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE)
        table.DescriptorTable = dx.D3D12_ROOT_DESCRIPTOR_TABLE1(pDescriptorRanges=[
            dx.D3D12_DESCRIPTOR_RANGE1(RangeType=dx.D3D12_DESCRIPTOR_RANGE_TYPE_UAV, NumDescriptors=3,
                                       BaseShaderRegister=0, OffsetInDescriptorsFromTableStart=0),
            dx.D3D12_DESCRIPTOR_RANGE1(RangeType=dx.D3D12_DESCRIPTOR_RANGE_TYPE_SRV, NumDescriptors=1,
                                       BaseShaderRegister=1, OffsetInDescriptorsFromTableStart=3)])
        constants = dx.D3D12_ROOT_PARAMETER1(ParameterType=dx.D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS)
        constants.Constants = dx.D3D12_ROOT_CONSTANTS(ShaderRegister=0, Num32BitValues=20)

        def root_descriptor(kind, register):
            return dx.D3D12_ROOT_PARAMETER1(ParameterType=kind,
                                            Descriptor=dx.D3D12_ROOT_DESCRIPTOR1(ShaderRegister=register))
        parameters = [constants, table,
                      root_descriptor(dx.D3D12_ROOT_PARAMETER_TYPE_SRV, 0),   # the scene
                      root_descriptor(dx.D3D12_ROOT_PARAMETER_TYPE_SRV, 2),   # trunk normals
                      root_descriptor(dx.D3D12_ROOT_PARAMETER_TYPE_SRV, 3),   # leaf normals
                      root_descriptor(dx.D3D12_ROOT_PARAMETER_TYPE_UAV, 3)]   # statistics
        versioned = dx.D3D12_VERSIONED_ROOT_SIGNATURE_DESC(Version=dx.D3D_ROOT_SIGNATURE_VERSION_1_1)
        versioned.Desc_1_1 = dx.D3D12_ROOT_SIGNATURE_DESC1(pParameters=parameters)
        self.root = device.CreateRootSignature(0, dx.D3D12SerializeVersionedRootSignature(versioned))

        library = compile_library(SHADERS)
        self.subobject_descs = [  # each subobject's pDesc points to a struct that must stay alive
            (dx.D3D12_STATE_SUBOBJECT_TYPE_DXIL_LIBRARY,
             dx.D3D12_DXIL_LIBRARY_DESC(DXILLibrary=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=library))),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_HIT_GROUP,
             dx.D3D12_HIT_GROUP_DESC(HitGroupExport='TrunkGroup', Type=dx.D3D12_HIT_GROUP_TYPE_TRIANGLES,
                                     ClosestHitShaderImport='TrunkHit')),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_HIT_GROUP,
             dx.D3D12_HIT_GROUP_DESC(HitGroupExport='LeafGroup', Type=dx.D3D12_HIT_GROUP_TYPE_TRIANGLES,
                                     ClosestHitShaderImport='LeafHit', AnyHitShaderImport='LeafAnyHit')),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_SHADER_CONFIG,
             dx.D3D12_RAYTRACING_SHADER_CONFIG(MaxPayloadSizeInBytes=32, MaxAttributeSizeInBytes=8)),
            # micromaps are ignored unless the pipeline allows them
            (dx.D3D12_STATE_SUBOBJECT_TYPE_RAYTRACING_PIPELINE_CONFIG1,
             dx.D3D12_RAYTRACING_PIPELINE_CONFIG1(MaxTraceRecursionDepth=1,
                                                  Flags=dx.D3D12_RAYTRACING_PIPELINE_FLAG_ALLOW_OPACITY_MICROMAPS)),
            (dx.D3D12_STATE_SUBOBJECT_TYPE_GLOBAL_ROOT_SIGNATURE,
             dx.D3D12_GLOBAL_ROOT_SIGNATURE(pGlobalRootSignature=self.root)),
        ]
        self.state_object = device.CreateStateObject(dx.D3D12_STATE_OBJECT_DESC(
            Type=dx.D3D12_STATE_OBJECT_TYPE_RAYTRACING_PIPELINE,
            pSubobjects=[dx.D3D12_STATE_SUBOBJECT(Type=kind, pDesc=ctypes.addressof(desc))
                         for kind, desc in self.subobject_descs]))

        # shader table: ray generation | miss | trunk hit group | leaf hit group
        properties = dx.ID3D12StateObjectProperties(self.state_object)
        record = dx.D3D12_RAYTRACING_SHADER_TABLE_BYTE_ALIGNMENT
        data = numpy.zeros(record * 4, numpy.uint8)
        for slot, export in enumerate(('RayGen', 'Miss', 'TrunkGroup', 'LeafGroup')):
            address = properties.GetShaderIdentifier(export)
            assert address, 'no export named %s' % export
            data[slot * record:slot * record + dx.D3D12_SHADER_IDENTIFIER_SIZE_IN_BYTES] = numpy.frombuffer(
                ctypes.string_at(address, dx.D3D12_SHADER_IDENTIFIER_SIZE_IN_BYTES), numpy.uint8)
        self.shader_table = self.upload(data)
        start = self.shader_table.GetGPUVirtualAddress()
        self.dispatch = dx.D3D12_DISPATCH_RAYS_DESC(
            RayGenerationShaderRecord=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE(StartAddress=start, SizeInBytes=record),
            MissShaderTable=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE_AND_STRIDE(
                StartAddress=start + record, SizeInBytes=record, StrideInBytes=record),
            HitGroupTable=dx.D3D12_GPU_VIRTUAL_ADDRESS_RANGE_AND_STRIDE(
                StartAddress=start + record * 2, SizeInBytes=record * 2, StrideInBytes=record),
            Width=WIDTH, Height=HEIGHT, Depth=1)

    # -- frames -------------------------------------------------------------------------------------
    def render(self, constants, micromaps, present=True):
        """Trace a frame; return (GPU milliseconds, any-hit invocations)."""
        cl = self.cl
        self.allocator.Reset()
        cl.Reset(self.allocator)
        cl.ResourceBarrier([transition(self.stats, dx.D3D12_RESOURCE_STATE_COMMON,
                                       dx.D3D12_RESOURCE_STATE_COPY_DEST)])
        cl.CopyBufferRegion(self.stats, 0, self.zeros, 0, 16)
        cl.ResourceBarrier([transition(self.stats, dx.D3D12_RESOURCE_STATE_COPY_DEST,
                                       dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
        cl.SetPipelineState1(self.state_object)
        cl.SetComputeRootSignature(self.root)
        cl.SetDescriptorHeaps([self.heap])
        cl.SetComputeRoot32BitConstants(0, len(constants), constants, 0)
        cl.SetComputeRootDescriptorTable(1, self.heap.GetGPUDescriptorHandleForHeapStart())
        cl.SetComputeRootShaderResourceView(2, self.tlas[0 if micromaps else 1].GetGPUVirtualAddress())
        cl.SetComputeRootShaderResourceView(3, self.trunk_normals.GetGPUVirtualAddress())
        cl.SetComputeRootShaderResourceView(4, self.leaf_normals.GetGPUVirtualAddress())
        cl.SetComputeRootUnorderedAccessView(5, self.stats.GetGPUVirtualAddress())
        cl.EndQuery(self.timestamps, dx.D3D12_QUERY_TYPE_TIMESTAMP, 0)
        cl.DispatchRays(self.dispatch)
        cl.EndQuery(self.timestamps, dx.D3D12_QUERY_TYPE_TIMESTAMP, 1)
        cl.ResolveQueryData(self.timestamps, dx.D3D12_QUERY_TYPE_TIMESTAMP, 0, 2, self.timestamp_readback, 0)
        cl.ResourceBarrier([transition(self.stats, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                       dx.D3D12_RESOURCE_STATE_COPY_SOURCE)])
        cl.CopyBufferRegion(self.stats_readback, 0, self.stats, 0, 16)
        cl.ResourceBarrier([transition(self.stats, dx.D3D12_RESOURCE_STATE_COPY_SOURCE,
                                       dx.D3D12_RESOURCE_STATE_COMMON)])
        if present:
            back_buffer = self.back_buffers[self.swap_chain.GetCurrentBackBufferIndex()]
            cl.ResourceBarrier([
                transition(self.output, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS, dx.D3D12_RESOURCE_STATE_COPY_SOURCE),
                transition(back_buffer, dx.D3D12_RESOURCE_STATE_PRESENT, dx.D3D12_RESOURCE_STATE_COPY_DEST)])
            cl.CopyResource(back_buffer, self.output)
            cl.ResourceBarrier([
                transition(self.output, dx.D3D12_RESOURCE_STATE_COPY_SOURCE, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
                transition(back_buffer, dx.D3D12_RESOURCE_STATE_COPY_DEST, dx.D3D12_RESOURCE_STATE_PRESENT)])
        cl.Close()
        self.queue.ExecuteCommandLists([cl])
        if present:
            self.swap_chain.Present(0, 0)
        self.wait()
        start, end = numpy.frombuffer(ctypes.string_at(self.timestamp_readback.Map(0), 16), numpy.uint64)
        self.timestamp_readback.Unmap(0)
        hits = int(numpy.frombuffer(ctypes.string_at(self.stats_readback.Map(0), 4), numpy.uint32)[0])
        self.stats_readback.Unmap(0)
        return (int(end) - int(start)) * 1000.0 / self.ticks, hits

    def read_output(self):
        """The output image as a (HEIGHT, WIDTH, 4) array."""
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
        data = numpy.frombuffer(ctypes.string_at(readback.Map(0), total), numpy.uint8)
        readback.Unmap(0)
        return numpy.stack([data[y * pitch:y * pitch + WIDTH * 4] for y in range(HEIGHT)]).reshape(HEIGHT, WIDTH, 4)


def millions(count):
    return '%.1fM' % (count / 1e6) if count >= 100000 else '%.1fK' % (count / 1e3)


def camera_constants(state, frame, view):
    yaw, pitch = state['yaw'], state['pitch']
    forward = numpy.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    right = numpy.cross([0.0, 1.0, 0.0], forward)
    right /= numpy.linalg.norm(right)
    up = numpy.cross(forward, right)
    tan = math.tan(math.radians(60) / 2)
    constants = numpy.zeros(20, numpy.float32)
    as_uint = constants.view(numpy.uint32)
    constants[0:3], as_uint[3] = state['position'], frame
    constants[4:7], as_uint[7] = forward, view
    constants[8:11], constants[11] = right * tan * WIDTH / HEIGHT, 32.0
    constants[12:15] = up * tan
    constants[16:19] = SUN
    return constants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trees', type=int, default=100)
    ap.add_argument('--level', type=int, default=9, help='micromap subdivision level (4^level micro-triangles)')
    ap.add_argument('--micromaps', choices=('on', 'off'), default='on')
    ap.add_argument('--view', choices=VIEWS, default='shaded')
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames')
    ap.add_argument('--screenshot', help='save the last frame to this PNG')
    ap.add_argument('--check', action='store_true', help='render the first frame with and without micromaps '
                                                         'and compare them')
    ap.add_argument('--debug', action='store_true', help='enable the D3D12 debug layer and report its errors')
    args = ap.parse_args()
    if args.debug:
        dx.D3D12GetDebugInterface().EnableDebugLayer()

    root = tkinter.Tk()
    root.title('pydx12: opacity micromaps')
    view = tkinter.Frame(root, width=WIDTH, height=HEIGHT)
    view.pack()
    root.resizable(False, False)
    root.update()
    renderer = Renderer(view.winfo_id(), args.trees, args.level)

    state: dict = {'position': numpy.array([0.0, 1.7, -12.0]), 'yaw': -0.62, 'pitch': 0.16, 'drag': None,
                   'micromaps': args.micromaps == 'on', 'view': VIEWS.index(args.view), 'walk': False,
                   'closed': False, 'dirty': True}

    if args.check:
        images, hits = [], []
        for micromaps in (True, False):
            hits.append(renderer.render(camera_constants(state, 0, 0), micromaps, present=False)[1])
            images.append(renderer.read_output())
        different = numpy.any(images[0] != images[1], axis=2)
        print('any-hit invocations: %d with micromaps, %d without (%.1fx fewer)' % (
            hits[0], hits[1], hits[1] / max(hits[0], 1)))
        print('pixels that differ: %d of %d' % (different.sum(), different.size))
        # alternate frame by frame, so both see the same GPU clocks
        times: dict = {True: [], False: []}
        for i in range(200):
            micromaps = i % 2 == 0
            times[micromaps].append(renderer.render(camera_constants(state, i // 2, 0), micromaps,
                                                    present=False)[0])
        on, off = (sorted(times[m])[len(times[m]) // 2] for m in (True, False))
        print('GPU time (median of 100 frames each): %.2f ms with micromaps, %.2f ms without (%.1fx faster)' % (
            on, off, off / on))

    def on_drag(event):
        if state['drag']:
            state['yaw'] += (event.x - state['drag'][0]) * 0.004
            state['pitch'] = min(1.2, max(-1.2, state['pitch'] - (event.y - state['drag'][1]) * 0.004))
            state['dirty'] = True
        state['drag'] = (event.x, event.y)

    def on_wheel(event):
        state['position'] += numpy.array([math.sin(state['yaw']), 0, math.cos(state['yaw'])]) * (
            1.0 if event.delta > 0 else -1.0)
        state['dirty'] = True

    def on_key(event):
        key = event.keysym.lower()
        if key == 'm':
            state['micromaps'] = not state['micromaps']
        elif key == 'v':
            state['view'] = (state['view'] + 1) % len(VIEWS)
        elif key == 'space':
            state['walk'] = not state['walk']
        elif key == 'escape':
            state['closed'] = True
        state['dirty'] = True

    view.bind('<ButtonPress-1>', lambda e: state.update(drag=(e.x, e.y)))
    view.bind('<B1-Motion>', on_drag)
    root.bind('<MouseWheel>', on_wheel)
    root.bind('<Key>', on_key)
    root.protocol('WM_DELETE_WINDOW', lambda: state.update(closed=True))

    timings: dict = {True: [], False: []}
    frames, sample, last = 0, 0, time.perf_counter()
    while not state['closed'] and (not args.frames or frames < args.frames):
        root.update()
        now = time.perf_counter()
        if state['walk']:
            state['position'] += numpy.array([math.sin(state['yaw']), 0, math.cos(state['yaw'])]) * (now - last) * 1.5
            state['yaw'] += (now - last) * 0.05
            state['dirty'] = True
        last = now
        if state['dirty']:
            sample, state['dirty'] = 0, False
        milliseconds, hits = renderer.render(camera_constants(state, sample, state['view']), state['micromaps'])
        timings[state['micromaps']].append((milliseconds, hits))
        sample += 1
        frames += 1
        if frames % 10 == 0:
            parts = []
            for micromaps in (True, False):
                if timings[micromaps]:
                    ms, count = timings[micromaps][-1]
                    parts.append('micromaps %s: %.2f ms, %s any-hit' % (
                        'on' if micromaps else 'off', ms, millions(count)))
            root.title('pydx12: opacity micromaps - %s - %d samples - M micromaps, V view, Space walk' % (
                ' | '.join(parts), sample))
    if args.screenshot:
        from PIL import Image
        Image.fromarray(renderer.read_output()[..., :3]).save(args.screenshot)
        print('saved', args.screenshot)
    for micromaps in (True, False):
        if timings[micromaps]:
            ms = [t for t, _ in timings[micromaps]]
            print('micromaps %s: %d frames, %.2f ms average on the GPU, %s any-hit invocations per frame' % (
                'on' if micromaps else 'off', len(ms), sum(ms) / len(ms),
                millions(sum(h for _, h in timings[micromaps]) // len(ms))))
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
