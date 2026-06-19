from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TexturePackInfo:
    id: str
    name: str
    source_path: Path
    source_kind: str  # "zip" | "folder" | "default"
    format: str  # "minecraft_java" | "veilstone_native"
    tile_size: int | None


@dataclass
class ImportReport:
    pack_id: str
    imported: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    fallback: list[str] = field(default_factory=list)
    ignored_animations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
