from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.domain.biomes import BiomeDef, BiomeRegistry, load_biome_registry_from_toml


def test_biome_registry_basic() -> None:
    plains = BiomeDef("twilight_plains", "Twilight Plains", "grass", "dirt", "stone")
    woods = BiomeDef(
        "twilight_woods", "Twilight Woods", "grass", "dirt", "stone", tree_density=0.15
    )

    registry = BiomeRegistry((plains, woods))

    assert len(registry) == 2
    assert registry.by_key("twilight_plains").surface_block == "grass"
    assert registry.by_key("twilight_woods").tree_density == 0.15


def test_biome_registry_rejects_duplicate_key() -> None:
    plains = BiomeDef("plains", "Plains", "grass", "dirt", "stone")

    with pytest.raises(ValueError, match="Duplicate biome key"):
        BiomeRegistry((plains, plains))


def test_biome_registry_unknown_key_raises() -> None:
    registry = BiomeRegistry([BiomeDef("plains", "Plains", "grass", "dirt", "stone")])

    with pytest.raises(KeyError, match="Unknown biome key"):
        registry.by_key("nonexistent")


def test_biome_def_validates_key() -> None:
    with pytest.raises(ValueError, match="lowercase"):
        BiomeDef("BAD_KEY", "Bad", "grass", "dirt", "stone")


def test_biome_def_validates_tree_density() -> None:
    with pytest.raises(ValueError, match="tree_density"):
        BiomeDef("plains", "Plains", "grass", "dirt", "stone", tree_density=1.5)


_MINIMAL_BIOME_TOML = """\
[[biome]]
key = "twilight_plains"
name = "Twilight Plains"
surface_block = "grass"
subsurface_block = "dirt"
deep_block = "stone"
water_level = 62
base_height = 64
height_variation = 12
tree_density = 0.02

[[biome]]
key = "dusk_highlands"
name = "Dusk Highlands"
surface_block = "stone"
subsurface_block = "stone"
deep_block = "stone"
water_level = 58
base_height = 80
height_variation = 24
tree_density = 0.01
"""


def test_load_biome_registry_from_toml(tmp_path: Path) -> None:
    toml_file = tmp_path / "biomes.toml"
    toml_file.write_text(_MINIMAL_BIOME_TOML)

    registry = load_biome_registry_from_toml(toml_file)

    assert len(registry) == 2
    plains = registry.by_key("twilight_plains")
    assert plains.base_height == 64
    assert plains.tree_density == 0.02
    highlands = registry.by_key("dusk_highlands")
    assert highlands.water_level == 58


def test_load_biome_registry_data_file() -> None:
    data_path = Path(__file__).parents[2] / "data" / "biomes.toml"
    registry = load_biome_registry_from_toml(data_path)

    assert len(registry) == 4
    assert registry.by_key("twilight_plains").surface_block == "grass"
    assert registry.by_key("gloom_swamp").water_level == 65
