"""Draw a triangle into a tkinter window through a DXGI flip-model swapchain.

Usage: python examples/triangle.py [--frames N]
"""
import argparse
import ctypes
import time
import tkinter

import pydx12 as dx

WIDTH, HEIGHT = 640, 480
FRAMES = 2

HLSL = """
struct V { float4 pos : SV_Position; float3 color : COLOR; };
V vs(float2 pos : POSITION, float3 color : COLOR) { V v; v.pos = float4(pos, 0, 1); v.color = color; return v; }
float4 ps(V v) : SV_Target { return float4(v.color, 1); }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames (0 = run until closed)')
    args = ap.parse_args()

    root = tkinter.Tk()
    root.title('pydx12 triangle')
    canvas = tkinter.Frame(root, width=WIDTH, height=HEIGHT)
    canvas.pack()
    root.update()
    hwnd = canvas.winfo_id()

    dx.D3D12GetDebugInterface().EnableDebugLayer()
    factory = dx.CreateDXGIFactory2()
    device = dx.D3D12CreateDevice(factory.EnumAdapterByGpuPreference(0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE))
    queue = device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))

    sc_desc = dx.DXGI_SWAP_CHAIN_DESC1(Width=WIDTH, Height=HEIGHT, Format=dx.DXGI_FORMAT_R8G8B8A8_UNORM,
                                       BufferUsage=dx.DXGI_USAGE_RENDER_TARGET_OUTPUT, BufferCount=FRAMES,
                                       SwapEffect=dx.DXGI_SWAP_EFFECT_FLIP_DISCARD)
    sc_desc.SampleDesc.Count = 1
    swapchain = dx.IDXGISwapChain3(factory.CreateSwapChainForHwnd(queue, hwnd, sc_desc))

    rtv_heap = device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_RTV,
                                                                         NumDescriptors=FRAMES))
    rtv_size = device.GetDescriptorHandleIncrementSize(dx.D3D12_DESCRIPTOR_HEAP_TYPE_RTV)
    rtv_start = rtv_heap.GetCPUDescriptorHandleForHeapStart().ptr
    rtvs = [dx.D3D12_CPU_DESCRIPTOR_HANDLE(rtv_start + i * rtv_size) for i in range(FRAMES)]
    buffers = [swapchain.GetBuffer(i) for i in range(FRAMES)]
    for buf, rtv in zip(buffers, rtvs):
        device.CreateRenderTargetView(buf, None, rtv)

    vs = dx.D3DCompile(HLSL, None, None, None, 'vs', 'vs_5_0')
    ps = dx.D3DCompile(HLSL, None, None, None, 'ps', 'ps_5_0')
    root_sig = device.CreateRootSignature(0, dx.D3D12SerializeRootSignature(
        dx.D3D12_ROOT_SIGNATURE_DESC(Flags=dx.D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT),
        dx.D3D_ROOT_SIGNATURE_VERSION_1))

    pso_desc = dx.D3D12_GRAPHICS_PIPELINE_STATE_DESC(
        pRootSignature=root_sig, VS=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=vs),
        PS=dx.D3D12_SHADER_BYTECODE(pShaderBytecode=ps), SampleMask=0xFFFFFFFF,
        PrimitiveTopologyType=dx.D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE, NumRenderTargets=1,
        RTVFormats=(dx.DXGI_FORMAT_R8G8B8A8_UNORM,))
    pso_desc.InputLayout.pInputElementDescs = [
        dx.D3D12_INPUT_ELEMENT_DESC(SemanticName='POSITION', Format=dx.DXGI_FORMAT_R32G32_FLOAT),
        dx.D3D12_INPUT_ELEMENT_DESC(SemanticName='COLOR', Format=dx.DXGI_FORMAT_R32G32B32_FLOAT,
                                    AlignedByteOffset=8)]
    pso_desc.RasterizerState.FillMode = dx.D3D12_FILL_MODE_SOLID
    pso_desc.RasterizerState.CullMode = dx.D3D12_CULL_MODE_NONE
    pso_desc.BlendState.RenderTarget[0].RenderTargetWriteMask = dx.D3D12_COLOR_WRITE_ENABLE_ALL
    pso_desc.SampleDesc.Count = 1
    pso = device.CreateGraphicsPipelineState(pso_desc)

    vertices = (ctypes.c_float * 15)(0.0, 0.7, 1, 0, 0,
                                     0.7, -0.7, 0, 1, 0,
                                     -0.7, -0.7, 0, 0, 1)
    vb_desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=ctypes.sizeof(vertices),
                                     Height=1, DepthOrArraySize=1, MipLevels=1,
                                     Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR)
    vb_desc.SampleDesc.Count = 1
    # an upload-heap vertex buffer keeps the example short
    vb = device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=dx.D3D12_HEAP_TYPE_UPLOAD),
                                        dx.D3D12_HEAP_FLAG_NONE, vb_desc, dx.D3D12_RESOURCE_STATE_GENERIC_READ)
    ctypes.memmove(vb.Map(0), vertices, ctypes.sizeof(vertices))
    vb.Unmap(0)
    vbv = dx.D3D12_VERTEX_BUFFER_VIEW(BufferLocation=vb.GetGPUVirtualAddress(),
                                      SizeInBytes=ctypes.sizeof(vertices), StrideInBytes=20)

    allocator = device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
    cl = device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, allocator)
    cl.Close()
    fence = device.CreateFence()
    fence_value = 0

    def transition(res, before, after):
        b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
        b.Transition = dx.D3D12_RESOURCE_TRANSITION_BARRIER(
            pResource=res, StateBefore=before, StateAfter=after,
            Subresource=dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
        return b

    closed = []
    root.protocol('WM_DELETE_WINDOW', lambda: closed.append(True))
    frame = 0
    start = time.perf_counter()
    while not closed and (not args.frames or frame < args.frames):
        root.update()
        index = swapchain.GetCurrentBackBufferIndex()
        allocator.Reset()
        cl.Reset(allocator, pso)
        cl.SetGraphicsRootSignature(root_sig)
        cl.RSSetViewports([dx.D3D12_VIEWPORT(Width=WIDTH, Height=HEIGHT, MaxDepth=1)])
        cl.RSSetScissorRects([dx.D3D12_RECT(right=WIDTH, bottom=HEIGHT)])
        cl.ResourceBarrier([transition(buffers[index], dx.D3D12_RESOURCE_STATE_PRESENT,
                                       dx.D3D12_RESOURCE_STATE_RENDER_TARGET)])
        cl.OMSetRenderTargets(1, [rtvs[index]], False)
        cl.ClearRenderTargetView(rtvs[index], (0.1, 0.1, 0.15, 1))
        cl.IASetPrimitiveTopology(dx.D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
        cl.IASetVertexBuffers(0, [vbv])
        cl.DrawInstanced(3, 1, 0, 0)
        cl.ResourceBarrier([transition(buffers[index], dx.D3D12_RESOURCE_STATE_RENDER_TARGET,
                                       dx.D3D12_RESOURCE_STATE_PRESENT)])
        cl.Close()
        queue.ExecuteCommandLists([cl])
        swapchain.Present(1, 0)
        fence_value += 1
        queue.Signal(fence, fence_value)
        fence.SetEventOnCompletion(fence_value, None)
        frame += 1
    elapsed = time.perf_counter() - start
    print('%d frames, %.1f fps' % (frame, frame / elapsed if elapsed else 0))
    root.destroy()


if __name__ == '__main__':
    main()
