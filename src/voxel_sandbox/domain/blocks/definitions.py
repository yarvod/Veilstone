from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Material(Enum):
    AIR = "air"
    STONE = "stone"
    EARTH = "earth"
    WOOD = "wood"
    PLANT = "plant"
    GLASS = "glass"
    FLUID = "fluid"


@dataclass(frozen=True, slots=True)
class BlockDef:
    id: int
    key: str
    name: str
    material: Material
    hardness: float
    is_solid: bool = True
    is_opaque: bool = True
    is_transparent: bool = False
    is_fluid: bool = False
    emits_light: int = 0
    texture_top: str = "missing"
    texture_side: str = "missing"
    texture_bottom: str = "missing"

    def __post_init__(self) -> None:
        if not 0 <= self.id <= 65535:
            raise ValueError("Block ID must fit into uint16")
        if not self.key or self.key.lower() != self.key:
            raise ValueError("Block key must be non-empty lowercase text")
        if not 0 <= self.emits_light <= 15:
            raise ValueError("Block light emission must be between 0 and 15")
