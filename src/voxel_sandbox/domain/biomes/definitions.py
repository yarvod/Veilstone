from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BiomeDef:
    key: str
    name: str
    surface_block: str
    subsurface_block: str
    deep_block: str
    water_level: int = 62
    base_height: int = 64
    height_variation: int = 12
    tree_density: float = 0.02

    def __post_init__(self) -> None:
        if not self.key or self.key.lower() != self.key:
            raise ValueError("Biome key must be non-empty lowercase text")
        if not 0 <= self.tree_density <= 1.0:
            raise ValueError("tree_density must be between 0 and 1")
