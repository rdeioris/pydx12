"""Conway's Game of Life, run as a DirectML operator graph.

Each generation is one dispatch of a compiled DirectML graph:

    cells --> PADDING (wrap) --> CONVOLUTION 3x3 --> ABS --> CLIP --> next cells

The convolution kernel is all ones with 0.5 in the centre, so it computes
s = neighbours + 0.5 * alive. A cell lives in the next generation exactly when
s is 2.5, 3 or 3.5, i.e. |s - 3| <= 0.5, which ABS (with bias -3) and CLIP
(scale -2, bias 2, clamped to [0, 1]) turn into 0 or 1. Wrap padding makes the
world a torus. No custom shaders: only DirectML operators.

Keys: space pauses, R reseeds, G drops a glider gun, Escape quits.

Usage: python examples/directml_life.py [--size 384] [--scale 2] [--frames N] [--check]
"""
import argparse
import ctypes
import time
import tkinter

import numpy
from PIL import Image, ImageTk

import pydx12 as dx

F32 = 4


class Life:
    def __init__(self, size):
        self.size = size
        self.nbytes = size * size * F32
        self.keep = []  # descriptor structs referenced through raw `Desc` pointers must outlive the calls

        self.device = dx.D3D12CreateDevice(dx.CreateDXGIFactory2().EnumAdapterByGpuPreference(
            0, dx.DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE))
        self.queue = self.device.CreateCommandQueue(dx.D3D12_COMMAND_QUEUE_DESC(Type=dx.D3D12_COMMAND_LIST_TYPE_DIRECT))
        self.allocator = self.device.CreateCommandAllocator(dx.D3D12_COMMAND_LIST_TYPE_DIRECT)
        self.cl = self.device.CreateCommandList(0, dx.D3D12_COMMAND_LIST_TYPE_DIRECT, self.allocator)
        self.cl.Close()
        self.fence = self.device.CreateFence()
        self.fence_value = 0

        self.dml = dx.DMLCreateDevice(self.device, dx.DML_CREATE_DEVICE_FLAG_NONE, dx.IDMLDevice1)
        levels = (ctypes.c_int * 1)(dx.DML_FEATURE_LEVEL_6_4)
        query = dx.DML_FEATURE_QUERY_FEATURE_LEVELS(RequestedFeatureLevelCount=1, RequestedFeatureLevels=levels)
        result = dx.DML_FEATURE_DATA_FEATURE_LEVELS()
        self.dml.CheckFeatureSupport(dx.DML_FEATURE_FEATURE_LEVELS, query, ctypes.sizeof(result), ctypes.byref(result))
        self.wrap = result.MaxSupportedFeatureLevel >= dx.DML_FEATURE_LEVEL_6_4
        print('DirectML feature level 0x%X, %s world' % (result.MaxSupportedFeatureLevel,
                                                          'wrapping' if self.wrap else 'bounded'))

        self.compiled = self.build_graph()
        self.cells = [self.buffer(self.nbytes) for _ in range(2)]  # ping-pong state
        self.kernel = self.buffer(9 * F32)
        self.upload = self.buffer(self.nbytes, dx.D3D12_HEAP_TYPE_UPLOAD)
        self.readback = self.buffer(self.nbytes, dx.D3D12_HEAP_TYPE_READBACK)
        self.current = 0
        self.initialize()

    # ---- resources -----------------------------------------------------
    def buffer(self, size, heap=dx.D3D12_HEAP_TYPE_DEFAULT):
        flags = dx.D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS if heap == dx.D3D12_HEAP_TYPE_DEFAULT else 0
        desc = dx.D3D12_RESOURCE_DESC(Dimension=dx.D3D12_RESOURCE_DIMENSION_BUFFER, Width=size, Height=1,
                                      DepthOrArraySize=1, MipLevels=1, Layout=dx.D3D12_TEXTURE_LAYOUT_ROW_MAJOR,
                                      Flags=flags)
        desc.SampleDesc.Count = 1
        state = {dx.D3D12_HEAP_TYPE_UPLOAD: dx.D3D12_RESOURCE_STATE_GENERIC_READ,
                 dx.D3D12_HEAP_TYPE_READBACK: dx.D3D12_RESOURCE_STATE_COPY_DEST}.get(
            heap, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)
        return self.device.CreateCommittedResource(dx.D3D12_HEAP_PROPERTIES(Type=heap), dx.D3D12_HEAP_FLAG_NONE,
                                                   desc, state)

    def binding(self, resource, size):
        buf = dx.DML_BUFFER_BINDING(Buffer=resource, SizeInBytes=size)
        self.keep.append(buf)
        return dx.DML_BINDING_DESC(Type=dx.DML_BINDING_TYPE_BUFFER, Desc=ctypes.addressof(buf))

    # ---- the graph -----------------------------------------------------
    def tensor(self, sizes):
        count = 1
        for s in sizes:
            count *= s
        desc = dx.DML_BUFFER_TENSOR_DESC(DataType=dx.DML_TENSOR_DATA_TYPE_FLOAT32, Sizes=sizes,
                                         TotalTensorSizeInBytes=count * F32)
        self.keep.append(desc)
        tensor = dx.DML_TENSOR_DESC(Type=dx.DML_TENSOR_TYPE_BUFFER, Desc=ctypes.addressof(desc))
        self.keep.append(tensor)
        return ctypes.pointer(tensor)

    def operator(self, type_, desc):
        self.keep.append(desc)
        return self.dml.CreateOperator(dx.DML_OPERATOR_DESC(Type=type_, Desc=ctypes.addressof(desc)))

    def build_graph(self):
        n = self.size
        grid = self.tensor([1, 1, n, n])
        nodes = []
        if self.wrap:
            padded = self.tensor([1, 1, n + 2, n + 2])
            nodes.append(self.operator(dx.DML_OPERATOR_PADDING, dx.DML_PADDING_OPERATOR_DESC(
                InputTensor=grid, OutputTensor=padded, PaddingMode=dx.DML_PADDING_MODE_WRAP,
                StartPadding=[0, 0, 1, 1], EndPadding=[0, 0, 1, 1])))
            conv_input, conv_padding = padded, [0, 0]
        else:
            conv_input, conv_padding = grid, [1, 1]
        nodes.append(self.operator(dx.DML_OPERATOR_CONVOLUTION, dx.DML_CONVOLUTION_OPERATOR_DESC(
            InputTensor=conv_input, FilterTensor=self.tensor([1, 1, 3, 3]), OutputTensor=grid,
            Mode=dx.DML_CONVOLUTION_MODE_CROSS_CORRELATION, Direction=dx.DML_CONVOLUTION_DIRECTION_FORWARD,
            Strides=[1, 1], Dilations=[1, 1], StartPadding=conv_padding, EndPadding=conv_padding,
            OutputPadding=[0, 0], GroupCount=1)))
        nodes.append(self.operator(dx.DML_OPERATOR_ELEMENT_WISE_ABS, dx.DML_ELEMENT_WISE_ABS_OPERATOR_DESC(
            InputTensor=grid, OutputTensor=grid, ScaleBias=ctypes.pointer(dx.DML_SCALE_BIAS(Scale=1, Bias=-3)))))
        nodes.append(self.operator(dx.DML_OPERATOR_ELEMENT_WISE_CLIP, dx.DML_ELEMENT_WISE_CLIP_OPERATOR_DESC(
            InputTensor=grid, OutputTensor=grid, ScaleBias=ctypes.pointer(dx.DML_SCALE_BIAS(Scale=-2, Bias=2)),
            Min=0, Max=1)))

        def edge(type_, desc):
            self.keep.append(desc)
            return dx.DML_GRAPH_EDGE_DESC(Type=type_, Desc=ctypes.addressof(desc))

        node_descs = []
        for i, op in enumerate(nodes):
            node = dx.DML_OPERATOR_GRAPH_NODE_DESC(Operator=op, Name='node%d' % i)
            self.keep.append(node)
            node_descs.append(dx.DML_GRAPH_NODE_DESC(Type=dx.DML_GRAPH_NODE_TYPE_OPERATOR, Desc=ctypes.addressof(node)))
        conv = 1 if self.wrap else 0
        graph = dx.DML_GRAPH_DESC(
            InputCount=2, OutputCount=1, Nodes=node_descs,
            InputEdges=[
                edge(dx.DML_GRAPH_EDGE_TYPE_INPUT, dx.DML_INPUT_GRAPH_EDGE_DESC(GraphInputIndex=0, ToNodeIndex=0)),
                edge(dx.DML_GRAPH_EDGE_TYPE_INPUT, dx.DML_INPUT_GRAPH_EDGE_DESC(
                    GraphInputIndex=1, ToNodeIndex=conv, ToNodeInputIndex=1))],
            IntermediateEdges=[
                edge(dx.DML_GRAPH_EDGE_TYPE_INTERMEDIATE, dx.DML_INTERMEDIATE_GRAPH_EDGE_DESC(
                    FromNodeIndex=i, ToNodeIndex=i + 1)) for i in range(len(nodes) - 1)],
            OutputEdges=[
                edge(dx.DML_GRAPH_EDGE_TYPE_OUTPUT, dx.DML_OUTPUT_GRAPH_EDGE_DESC(
                    FromNodeIndex=len(nodes) - 1, GraphOutputIndex=0))])
        return self.dml.CompileGraph(graph, dx.DML_EXECUTION_FLAG_NONE)

    # ---- execution -----------------------------------------------------
    def submit(self, record):
        self.allocator.Reset()
        self.cl.Reset(self.allocator)
        self.cl.SetDescriptorHeaps([self.heap])
        record()
        self.cl.Close()
        self.queue.ExecuteCommandLists([self.cl])
        self.fence_value += 1
        self.queue.Signal(self.fence, self.fence_value)
        self.fence.SetEventOnCompletion(self.fence_value, None)

    def initialize(self):
        initializer = self.dml.CreateOperatorInitializer([self.compiled])
        init_props = initializer.GetBindingProperties()
        exec_props = self.compiled.GetBindingProperties()
        count = max(init_props.RequiredDescriptorCount, exec_props.RequiredDescriptorCount)
        self.heap = self.device.CreateDescriptorHeap(dx.D3D12_DESCRIPTOR_HEAP_DESC(
            Type=dx.D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, NumDescriptors=count,
            Flags=dx.D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE))
        self.table_desc = dx.DML_BINDING_TABLE_DESC(
            Dispatchable=initializer, CPUDescriptorHandle=self.heap.GetCPUDescriptorHandleForHeapStart(),
            GPUDescriptorHandle=self.heap.GetGPUDescriptorHandleForHeapStart(), SizeInDescriptors=count)
        self.table = self.dml.CreateBindingTable(self.table_desc)
        self.recorder = self.dml.CreateCommandRecorder()

        temp_size = max(init_props.TemporaryResourceSize, exec_props.TemporaryResourceSize)
        self.temporary = self.buffer(temp_size) if temp_size else None
        persistent_size = exec_props.PersistentResourceSize
        self.persistent = self.buffer(persistent_size) if persistent_size else None
        if self.temporary:
            self.table.BindTemporaryResource(self.binding(self.temporary, temp_size))
        if self.persistent:
            self.table.BindOutputs([self.binding(self.persistent, persistent_size)])
        self.submit(lambda: self.recorder.RecordDispatch(self.cl, initializer, self.table))

        # rebind the table to the compiled graph, once per ping-pong direction
        self.table_desc.Dispatchable = self.compiled
        self.table.Reset(self.table_desc)
        if self.temporary:
            self.table.BindTemporaryResource(self.binding(self.temporary, temp_size))
        if self.persistent:
            self.table.BindPersistentResource(self.binding(self.persistent, persistent_size))
        kernel = (ctypes.c_float * 9)(1, 1, 1, 1, 0.5, 1, 1, 1, 1)
        self.write(self.kernel, kernel)
        self.kernel_binding = self.binding(self.kernel, 9 * F32)
        self.cell_bindings = [self.binding(c, self.nbytes) for c in self.cells]

    def barrier(self, resource, before, after):
        b = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_TRANSITION)
        b.Transition = dx.D3D12_RESOURCE_TRANSITION_BARRIER(
            pResource=resource, StateBefore=before, StateAfter=after,
            Subresource=dx.D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)
        return b

    def write(self, target, data):
        ctypes.memmove(self.upload.Map(0), data, ctypes.sizeof(data))
        self.upload.Unmap(0)

        def record():
            self.cl.ResourceBarrier([self.barrier(target, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                                  dx.D3D12_RESOURCE_STATE_COPY_DEST)])
            self.cl.CopyBufferRegion(target, 0, self.upload, 0, ctypes.sizeof(data))
            self.cl.ResourceBarrier([self.barrier(target, dx.D3D12_RESOURCE_STATE_COPY_DEST,
                                                  dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
        self.submit(record)

    def seed(self, cells):
        self.write(self.cells[self.current], numpy.ascontiguousarray(cells, dtype=numpy.float32).ctypes.data_as(
            ctypes.POINTER(ctypes.c_float * (self.size * self.size))).contents)

    def step(self, generations=1):
        """Run some generations on the GPU and return the final grid as a numpy array."""
        def record():
            for _ in range(generations):
                src, dst = self.current, 1 - self.current
                self.table.BindInputs([self.cell_bindings[src], self.kernel_binding])
                self.table.BindOutputs([self.cell_bindings[dst]])
                self.recorder.RecordDispatch(self.cl, self.compiled, self.table)
                uav = dx.D3D12_RESOURCE_BARRIER(Type=dx.D3D12_RESOURCE_BARRIER_TYPE_UAV)
                uav.UAV.pResource = self.cells[dst]
                self.cl.ResourceBarrier([uav])
                self.current = dst
            out = self.cells[self.current]
            self.cl.ResourceBarrier([self.barrier(out, dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                                                  dx.D3D12_RESOURCE_STATE_COPY_SOURCE)])
            self.cl.CopyResource(self.readback, out)
            self.cl.ResourceBarrier([self.barrier(out, dx.D3D12_RESOURCE_STATE_COPY_SOURCE,
                                                  dx.D3D12_RESOURCE_STATE_UNORDERED_ACCESS)])
        self.submit(record)
        address = self.readback.Map(0)
        grid = numpy.ctypeslib.as_array((ctypes.c_float * (self.size * self.size)).from_address(address))
        grid = grid.reshape(self.size, self.size).copy()
        self.readback.Unmap(0)
        return grid


def reference_step(cells, wrap):
    """The same rule on the CPU, to check the GPU."""
    if not wrap:
        cells = numpy.pad(cells, 1)
    n = sum(numpy.roll(numpy.roll(cells, dy, 0), dx_, 1)
            for dy in (-1, 0, 1) for dx_ in (-1, 0, 1) if dy or dx_)
    out = ((n == 3) | ((cells == 1) & (n == 2))).astype(numpy.float32)
    return out if wrap else out[1:-1, 1:-1]


GOSPER_GUN = """
........................O...........
......................O.O...........
............OO......OO............OO
...........O...O....OO............OO
OO........O.....O...OO..............
OO........O...O.OO....O.O...........
..........O.....O.......O...........
...........O...O....................
............OO......................
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=384)
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--frames', type=int, default=0, help='exit after N frames (0 = run until closed)')
    ap.add_argument('--check', action='store_true', help='compare 100 GPU generations against numpy and exit')
    args = ap.parse_args()

    life = Life(args.size)
    rng = numpy.random.default_rng()

    def random_cells():
        return (rng.random((args.size, args.size)) < 0.3).astype(numpy.float32)

    if args.check:
        cells = random_cells()
        life.seed(cells)
        for generation in range(100):
            cells = reference_step(cells, life.wrap)
            gpu = life.step()
            assert numpy.array_equal(gpu, cells), 'mismatch at generation %d' % generation
        print('100 generations match the CPU reference (%d live cells)' % cells.sum())
        return

    root = tkinter.Tk()
    root.title('pydx12: Game of Life on DirectML')
    label = tkinter.Label(root, bd=0)
    label.pack()
    state = {'paused': False, 'closed': False}
    heat = numpy.zeros((args.size, args.size), numpy.float32)

    def reseed(_=None):
        life.seed(random_cells())

    def glider_gun(_=None):
        cells = life.step(0)
        rows = GOSPER_GUN.strip().splitlines()
        y, x = rng.integers(0, args.size - len(rows)), rng.integers(0, args.size - len(rows[0]))
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                cells[y + j, x + i] = 1.0 if ch == 'O' else cells[y + j, x + i]
        life.seed(cells)

    root.bind('<space>', lambda e: state.update(paused=not state['paused']))
    root.bind('<r>', reseed)
    root.bind('<g>', glider_gun)
    root.bind('<Escape>', lambda e: state.update(closed=True))
    root.protocol('WM_DELETE_WINDOW', lambda: state.update(closed=True))
    reseed()

    frames = 0
    start = time.perf_counter()
    while not state['closed'] and (not args.frames or frames < args.frames):
        cells = life.step(0 if state['paused'] else 1)
        # glowing trails: live cells are white-hot, dead ones cool down through orange and purple
        heat = numpy.maximum(heat * 0.92, cells)
        rgb = numpy.stack([numpy.clip(heat * 1.6, 0, 1), heat ** 2.2, numpy.clip(0.25 * heat + heat ** 6, 0, 1)], -1)
        image = Image.fromarray((rgb * 255).astype(numpy.uint8))
        image = image.resize((args.size * args.scale,) * 2, Image.NEAREST)
        photo = ImageTk.PhotoImage(image)
        label.configure(image=photo)
        label.image = photo
        root.update()
        frames += 1
        elapsed = time.perf_counter() - start
        if frames % 30 == 0:
            root.title('pydx12: Game of Life on DirectML - %d live cells - %.0f fps' % (cells.sum(), frames / elapsed))
    print('%d frames, %.1f fps' % (frames, frames / (time.perf_counter() - start)))
    root.destroy()


if __name__ == '__main__':
    main()
