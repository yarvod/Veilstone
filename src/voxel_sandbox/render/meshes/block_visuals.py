from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.render.model_snapshots import build_block_model_snapshot
from voxel_sandbox.render.vegetation_wind import wind_motion_value

type TextureRect = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class BlockMeshVisualLookups:
    texture_rects: dict[str, NDArray[np.float32]]
    material_rects: dict[str, dict[str, NDArray[np.float32]]]
    cross_lookup: NDArray[np.bool_]
    wind_lookup: NDArray[np.float32]


def build_block_mesh_visual_lookups(
    registry: BlockRegistry,
    texture_uvs: dict[str, TextureRect],
    material_uvs: dict[str, dict[str, TextureRect]] | None = None,
) -> BlockMeshVisualLookups:
    max_block_id = max((definition.id for definition in registry), default=0)
    texture_rects = {
        face: np.zeros((max_block_id + 1, 4), dtype=np.float32)
        for face in ("top", "side", "bottom")
    }
    material_rects = {
        role: {
            face: np.zeros((max_block_id + 1, 4), dtype=np.float32)
            for face in ("top", "side", "bottom")
        }
        for role in (material_uvs or {})
    }
    cross_lookup = np.zeros(max_block_id + 1, dtype=np.bool_)
    wind_lookup = np.zeros(max_block_id + 1, dtype=np.float32)

    for definition in registry:
        snapshot = build_block_model_snapshot(definition.id, registry)
        cross_lookup[snapshot.block_id] = snapshot.render_shape == "cross"
        wind_lookup[snapshot.block_id] = wind_motion_value(snapshot.wind_motion)
        for visual in snapshot.material_visuals(texture_uvs, material_uvs):
            texture_rects[visual.face][snapshot.block_id] = visual.color_rect
            for role, rect in visual.material_rects.items():
                material_rects[role][visual.face][snapshot.block_id] = rect

    return BlockMeshVisualLookups(
        texture_rects=texture_rects,
        material_rects=material_rects,
        cross_lookup=cross_lookup,
        wind_lookup=wind_lookup,
    )
