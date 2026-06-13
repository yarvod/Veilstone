# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from dataclasses import dataclass

import moderngl

from voxel_sandbox.engine.chunks import SectionCoord
from voxel_sandbox.render.meshes.data import MeshData


@dataclass(slots=True)
class GpuSectionMesh:
    data: MeshData
    vertex_buffer: moderngl.Buffer
    index_buffer: moderngl.Buffer
    vertex_array: moderngl.VertexArray

    def release(self) -> None:
        self.vertex_array.release()
        self.index_buffer.release()
        self.vertex_buffer.release()


class SectionMeshCache:
    def __init__(self, context: moderngl.Context, program: moderngl.Program) -> None:
        self.context = context
        self.program = program
        self._meshes: dict[SectionCoord, GpuSectionMesh] = {}

    def upload(self, key: SectionCoord, mesh: MeshData) -> None:
        self.remove(key)
        vertex_buffer = self.context.buffer(mesh.vertices.tobytes())
        index_buffer = self.context.buffer(mesh.indices.tobytes())
        vertex_array = self.context.vertex_array(
            self.program,
            [(vertex_buffer, "3f 2f 3f", "in_position", "in_uv", "in_normal")],
            index_buffer,
            index_element_size=4,
        )
        self._meshes[key] = GpuSectionMesh(mesh, vertex_buffer, index_buffer, vertex_array)

    def get(self, key: SectionCoord) -> GpuSectionMesh | None:
        return self._meshes.get(key)

    def remove(self, key: SectionCoord) -> None:
        previous = self._meshes.pop(key, None)
        if previous is not None:
            previous.release()

    def release(self) -> None:
        for mesh in self._meshes.values():
            mesh.release()
        self._meshes.clear()
