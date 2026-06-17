from __future__ import annotations

import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import MappingProxyType

from voxel_sandbox.domain.biomes.definitions import BiomeDef


class BiomeRegistry:
    def __init__(self, definitions: Iterable[BiomeDef]) -> None:
        by_key: dict[str, BiomeDef] = {}
        for definition in definitions:
            if definition.key in by_key:
                raise ValueError(f"Duplicate biome key: {definition.key}")
            by_key[definition.key] = definition
        self._by_key = MappingProxyType(by_key)

    def by_key(self, key: str) -> BiomeDef:
        try:
            return self._by_key[key]
        except KeyError as error:
            raise KeyError(f"Unknown biome key: {key}") from error

    def __iter__(self) -> Iterator[BiomeDef]:
        return iter(self._by_key.values())

    def __len__(self) -> int:
        return len(self._by_key)


def load_biome_registry_from_toml(path: Path) -> BiomeRegistry:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return BiomeRegistry(
        BiomeDef(
            b["key"],
            b["name"],
            b["surface_block"],
            b["subsurface_block"],
            b["deep_block"],
            water_level=b.get("water_level", 62),
            base_height=b.get("base_height", 64),
            height_variation=b.get("height_variation", 12),
            tree_density=b.get("tree_density", 0.02),
        )
        for b in data.get("biome", [])
    )
