# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass

import moderngl
import numpy as np

from voxel_sandbox.engine.chunks import SECTION_SIZE, SectionCoord
from voxel_sandbox.render.meshes.data import MeshData


@dataclass(slots=True)
class GpuSectionMesh:
    data: MeshData
    origin: tuple[int, int, int]
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]
    section_count: int
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
        shoreline_factor: bool = False,
        batch_chunks: int = 1,
        batch_vertical_sections: bool = False,
    ) -> None:
        if wind_motion and shoreline_factor:
            raise ValueError("Shoreline factor is only supported by non-wind mesh layouts")
        self.context = context
        self.program = program
        self.depth_program = depth_program
        self.wind_motion = wind_motion
        self.shoreline_factor = shoreline_factor
        self.batch_chunks = max(1, batch_chunks)
        self.batch_vertical_sections = batch_vertical_sections
        self._meshes: dict[SectionCoord, GpuSectionMesh] = {}
        self._batch_sections: dict[SectionCoord, dict[SectionCoord, MeshData]] = {}

    def upload(self, key: SectionCoord, mesh: MeshData) -> None:
        self.apply({key: mesh})

    def apply(self, updates: Mapping[SectionCoord, MeshData | None]) -> None:
        affected: set[SectionCoord] = set()
        for key, mesh in updates.items():
            batch_key = self._batch_key(key)
            affected.add(batch_key)
            sections = self._batch_sections.setdefault(batch_key, {})
            if mesh is None or not mesh.indices.size:
                sections.pop(key, None)
            else:
                sections[key] = mesh
            if not sections:
                self._batch_sections.pop(batch_key, None)
        for batch_key in affected:
            self._rebuild(batch_key)

    def _rebuild(self, batch_key: SectionCoord) -> None:
        previous = self._meshes.pop(batch_key, None)
        if previous is not None:
            previous.release()
        sections = self._batch_sections.get(batch_key)
        if not sections:
            return
        mesh, origin, minimum, maximum = combine_section_meshes(batch_key, sections)
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
            detail_attribute = "in_shore_factor" if self.shoreline_factor else "in_ao"
            vertex_content = (
                vertex_buffer,
                "3f 2f 3f 1f 1f 1f 4f",
                "in_position",
                "in_uv",
                "in_normal",
                "in_sky_light",
                "in_block_light",
                detail_attribute,
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
        self._meshes[batch_key] = GpuSectionMesh(
            mesh,
            origin,
            minimum,
            maximum,
            len(sections),
            vertex_buffer,
            index_buffer,
            vertex_array,
            depth_vertex_array,
        )

    def get(self, key: SectionCoord) -> GpuSectionMesh | None:
        return self._meshes.get(self._batch_key(key))

    def items(self) -> Iterator[tuple[SectionCoord, GpuSectionMesh]]:
        return iter(self._meshes.items())

    def remove(self, key: SectionCoord) -> None:
        self.apply({key: None})

    def remove_many(self, keys: Iterable[SectionCoord]) -> None:
        self.apply(dict.fromkeys(keys))

    def release(self) -> None:
        for mesh in self._meshes.values():
            mesh.release()
        self._meshes.clear()
        self._batch_sections.clear()

    def _batch_key(self, key: SectionCoord) -> SectionCoord:
        return SectionCoord(
            key.x // self.batch_chunks * self.batch_chunks,
            0 if self.batch_vertical_sections else key.y,
            key.z // self.batch_chunks * self.batch_chunks,
        )


def combine_section_meshes(
    batch_key: SectionCoord,
    sections: Mapping[SectionCoord, MeshData],
) -> tuple[
    MeshData,
    tuple[int, int, int],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    origin = (
        batch_key.x * SECTION_SIZE,
        batch_key.y * SECTION_SIZE,
        batch_key.z * SECTION_SIZE,
    )
    vertices: list[np.ndarray] = []
    indices: list[np.ndarray] = []
    vertex_offset = 0
    ordered = sorted(sections.items(), key=lambda item: (item[0].x, item[0].y, item[0].z))
    for key, mesh in ordered:
        adjusted_vertices = mesh.vertices.copy()
        adjusted_vertices[:, :3] += np.asarray(
            (
                key.x * SECTION_SIZE - origin[0],
                key.y * SECTION_SIZE - origin[1],
                key.z * SECTION_SIZE - origin[2],
            ),
            dtype=np.float32,
        )
        vertices.append(adjusted_vertices)
        indices.append(mesh.indices + np.uint32(vertex_offset))
        vertex_offset += mesh.vertices.shape[0]

    keys = tuple(sections)
    minimum = (
        float(min(key.x for key in keys) * SECTION_SIZE),
        float(min(key.y for key in keys) * SECTION_SIZE),
        float(min(key.z for key in keys) * SECTION_SIZE),
    )
    maximum = (
        float((max(key.x for key in keys) + 1) * SECTION_SIZE),
        float((max(key.y for key in keys) + 1) * SECTION_SIZE),
        float((max(key.z for key in keys) + 1) * SECTION_SIZE),
    )
    return MeshData(np.concatenate(vertices), np.concatenate(indices)), origin, minimum, maximum
