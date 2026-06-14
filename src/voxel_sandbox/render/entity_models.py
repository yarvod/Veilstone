from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

type Vec3 = tuple[float, float, float]
type Vec4 = tuple[float, float, float, float]
type FaceUVs = tuple[Vec4, Vec4, Vec4, Vec4, Vec4, Vec4]


@dataclass(frozen=True, slots=True)
class ModelPart:
    name: str
    parent: str | None
    offset: Vec3
    size: Vec3
    pivot: Vec3 = (0.0, 0.0, 0.0)
    material: str = "skin"
    uv: Vec4 = (0.0, 0.0, 1.0, 1.0)
    face_uvs: FaceUVs | None = None
    tint: Vec3 = (1.0, 1.0, 1.0)


@dataclass(frozen=True, slots=True)
class EntityModelDef:
    key: str
    texture: Path
    base_color: Vec3
    parts: tuple[ModelPart, ...]


class EntityModelRegistry:
    def __init__(self, models: tuple[EntityModelDef, ...]) -> None:
        self._models = {model.key: model for model in models}
        if len(self._models) != len(models):
            raise ValueError("Entity model keys must be unique")
        for model in models:
            _validate_hierarchy(model)

    @classmethod
    def from_toml(cls, path: Path, asset_root: Path) -> EntityModelRegistry:
        with path.open("rb") as file:
            data = tomllib.load(file)
        if data.get("version") != 1:
            raise ValueError("Unsupported entity model format version")
        raw_models = data.get("models")
        if not isinstance(raw_models, list):
            raise ValueError("entity_models.toml must contain [[models]]")
        models: list[EntityModelDef] = []
        for raw_model in cast("list[object]", raw_models):
            if not isinstance(raw_model, dict):
                raise ValueError("Entity models must be TOML tables")
            model = cast("dict[str, object]", raw_model)
            raw_regions = model.get("uv_regions", {})
            if not isinstance(raw_regions, dict):
                raise ValueError("Entity model uv_regions must be a table")
            regions = {
                str(name): _vec4(value)
                for name, value in cast("dict[object, object]", raw_regions).items()
            }
            raw_parts = model.get("parts")
            if not isinstance(raw_parts, list):
                raise ValueError("Entity model must contain parts")
            parts = tuple(_parse_part(part, regions) for part in cast("list[object]", raw_parts))
            models.append(
                EntityModelDef(
                    key=str(model["key"]),
                    texture=asset_root / str(model["texture"]),
                    base_color=_vec3(model["base_color"]),
                    parts=parts,
                )
            )
        return cls(tuple(models))

    def get(self, key: str) -> EntityModelDef:
        return self._models[key]


def _parse_part(raw: object, regions: dict[str, Vec4]) -> ModelPart:
    if not isinstance(raw, dict):
        raise ValueError("Model parts must be TOML tables")
    values = cast("dict[str, object]", raw)
    uv = _resolve_uv(values.get("uv_all", values.get("uv", [0.0, 0.0, 1.0, 1.0])), regions)
    face_values = {face: uv for face in ("front", "back", "left", "right", "top", "bottom")}
    for alias, faces in (
        ("uv_sides", ("front", "back", "left", "right")),
        ("uv_x", ("left", "right")),
        ("uv_y", ("top", "bottom")),
        ("uv_z", ("front", "back")),
    ):
        if alias in values:
            resolved = _resolve_uv(values[alias], regions)
            for face in faces:
                face_values[face] = resolved
    for face in face_values:
        if (key := f"uv_{face}") in values:
            face_values[face] = _resolve_uv(values[key], regions)
    face_uvs = tuple(
        face_values[face] for face in ("front", "back", "left", "right", "top", "bottom")
    )
    return ModelPart(
        name=str(values["name"]),
        parent=str(parent) if (parent := values.get("parent")) is not None else None,
        offset=_vec3(values["offset"]),
        size=_vec3(values["size"]),
        pivot=_vec3(values.get("pivot", [0.0, 0.0, 0.0])),
        material=str(values.get("material", "skin")),
        uv=uv,
        face_uvs=cast("FaceUVs", face_uvs),
        tint=_vec3(values.get("tint", [1.0, 1.0, 1.0])),
    )


def _resolve_uv(value: object, regions: dict[str, Vec4]) -> Vec4:
    if isinstance(value, str):
        try:
            return regions[value]
        except KeyError as error:
            raise ValueError(f"Unknown entity UV region: {value}") from error
    return _vec4(value)


def _vec3(value: object) -> Vec3:
    if not isinstance(value, list):
        raise ValueError("Expected a three-component vector")
    values = cast("list[object]", value)
    if len(values) != 3:
        raise ValueError("Expected a three-component vector")
    if not all(isinstance(component, int | float) for component in values):
        raise ValueError("Vector components must be numbers")
    numbers = cast("list[int | float]", values)
    return float(numbers[0]), float(numbers[1]), float(numbers[2])


def _vec4(value: object) -> Vec4:
    if not isinstance(value, list):
        raise ValueError("Expected a four-component vector")
    values = cast("list[object]", value)
    if len(values) != 4 or not all(isinstance(component, int | float) for component in values):
        raise ValueError("UV components must be four numbers")
    numbers = cast("list[int | float]", values)
    return float(numbers[0]), float(numbers[1]), float(numbers[2]), float(numbers[3])


def _validate_hierarchy(model: EntityModelDef) -> None:
    names = {part.name for part in model.parts}
    if len(names) != len(model.parts):
        raise ValueError(f"Duplicate part in model {model.key}")
    for part in model.parts:
        if part.parent is not None and part.parent not in names:
            raise ValueError(f"Unknown parent {part.parent} in model {model.key}")
