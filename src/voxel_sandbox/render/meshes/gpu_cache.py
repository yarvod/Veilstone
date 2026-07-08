# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from collections.abc import Iterator
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
    depth_vertex_array: moderngl.VertexArray | None = None

    def release(self) -> None:
        if self.depth_vertex_array is not None:
            self.depth_vertex_array.release()
        self.vertex_array.release()
        self.index_buffer.release()
        self.vertex_buffer.release()


class SectionMeshCache:
    def __init__(
        self,
        context: moderngl.Context,
        program: moderngl.Program,
        depth_program: moderngl.Program | None = None,
        *,
        wind_motion: bool = True,
    ) -> None:
        self.context = context
        self.program = program
        self.depth_program = depth_program
        self.wind_motion = wind_motion
        self._meshes: dict[SectionCoord, GpuSectionMesh] = {}

    def upload(self, key: SectionCoord, mesh: MeshData) -> None:
        self.remove(key)
        vertex_buffer = self.context.buffer(mesh.vertices.tobytes())
        index_buffer = self.context.buffer(mesh.indices.tobytes())
        if self.wind_motion:
            vertex_content = (
                vertex_buffer,
                "3f 2f 3f 1f 1f 1f 4f 1f",
                "in_position",
                "in_uv",
                "in_normal",
                "in_sky_light",
                "in_block_light",
                "in_ao",
                "in_atlas_rect",
                "in_wind_motion",
            )
        else:
            vertex_content = (
                vertex_buffer,
                "3f 2f 3f 1f 1f 1f 4f",
                "in_position",
                "in_uv",
                "in_normal",
                "in_sky_light",
                "in_block_light",
                "in_ao",
                "in_atlas_rect",
            )
        vertex_array = self.context.vertex_array(
            self.program,
            [vertex_content],
            index_buffer,
            index_element_size=4,
        )
        depth_vertex_array = None
        if self.depth_program is not None:
            if self.wind_motion:
                depth_content = (
                    vertex_buffer,
                    "3f 2f 24x 4f 1f",
                    "in_position",
                    "in_uv",
                    "in_atlas_rect",
                    "in_wind_motion",
                )
            else:
                depth_content = (
                    vertex_buffer,
                    "3f 2f 24x 4f",
                    "in_position",
                    "in_uv",
                    "in_atlas_rect",
                )
            depth_vertex_array = self.context.vertex_array(
                self.depth_program,
                [depth_content],
                index_buffer,
                index_element_size=4,
            )
        self._meshes[key] = GpuSectionMesh(
            mesh,
            vertex_buffer,
            index_buffer,
            vertex_array,
            depth_vertex_array,
        )

    def get(self, key: SectionCoord) -> GpuSectionMesh | None:
        return self._meshes.get(key)

    def items(self) -> Iterator[tuple[SectionCoord, GpuSectionMesh]]:
        return iter(self._meshes.items())

    def remove(self, key: SectionCoord) -> None:
        previous = self._meshes.pop(key, None)
        if previous is not None:
            previous.release()

    def release(self) -> None:
        for mesh in self._meshes.values():
            mesh.release()
        self._meshes.clear()
