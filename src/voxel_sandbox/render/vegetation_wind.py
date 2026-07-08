from __future__ import annotations

from voxel_sandbox.domain.blocks import BlockDef, Material

WIND_STATIC = 0.0
WIND_FOLIAGE = 1.0
WIND_CROSS_PLANT = 2.0


def wind_motion_kind(block: BlockDef) -> str:
    if block.material is not Material.PLANT:
        return "none"
    if block.render_shape == "cross":
        return "cross_plant"
    if block.render_layer == "cutout":
        return "foliage"
    return "none"


def wind_motion_value(kind: str) -> float:
    if kind == "foliage":
        return WIND_FOLIAGE
    if kind == "cross_plant":
        return WIND_CROSS_PLANT
    return WIND_STATIC


def wind_motion_value_for_block(block: BlockDef) -> float:
    return wind_motion_value(wind_motion_kind(block))
