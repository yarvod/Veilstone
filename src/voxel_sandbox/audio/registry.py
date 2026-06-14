from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from voxel_sandbox.audio.events import VolumeGroup


@dataclass(frozen=True, slots=True)
class AudioResource:
    key: str
    paths: tuple[Path, ...]
    group: VolumeGroup
    loop: bool = False
    gain: float = 1.0

    def __post_init__(self) -> None:
        if not self.paths:
            raise ValueError("Audio resource must contain at least one path")
        if not 0.0 <= self.gain <= 2.0:
            raise ValueError("Audio resource gain must be between 0 and 2")


class AudioRegistry:
    def __init__(self, resources: tuple[AudioResource, ...]) -> None:
        if len({resource.key for resource in resources}) != len(resources):
            raise ValueError("Audio resource keys must be unique")
        self._resources = {resource.key: resource for resource in resources}

    @classmethod
    def from_toml(cls, path: Path, asset_root: Path) -> AudioRegistry:
        with path.open("rb") as file:
            data = tomllib.load(file)
        raw_entries = data.get("audio", [])
        if not isinstance(raw_entries, list):
            raise ValueError("audio.toml must contain [[audio]] entries")
        entries: list[dict[str, object]] = []
        for raw_entry in cast("list[object]", raw_entries):
            if not isinstance(raw_entry, dict):
                raise ValueError("audio.toml entries must be tables")
            entries.append(cast("dict[str, object]", raw_entry))
        resources: list[AudioResource] = []
        for entry in entries:
            raw_path = entry.get("path")
            if raw_path is not None:
                paths = (asset_root / str(raw_path),)
            elif "paths" in entry:
                raw_paths = entry["paths"]
                if not isinstance(raw_paths, list):
                    raise ValueError("Audio resource paths must be an array")
                paths = tuple(asset_root / str(item) for item in cast("list[object]", raw_paths))
            else:
                raise ValueError("Audio resource must specify path or paths")
            resources.append(
                AudioResource(
                    key=str(entry["key"]),
                    paths=paths,
                    group=VolumeGroup(str(entry["group"])),
                    loop=bool(entry.get("loop", False)),
                    gain=_gain(entry),
                )
            )
        return cls(tuple(resources))

    def get(self, key: str) -> AudioResource:
        try:
            return self._resources[key]
        except KeyError as error:
            raise KeyError(f"Unknown audio resource: {key}") from error

    def __contains__(self, key: str) -> bool:
        return key in self._resources


def _gain(entry: dict[str, object]) -> float:
    value = entry.get("gain", 1.0)
    if not isinstance(value, int | float):
        raise ValueError("Audio resource gain must be numeric")
    return float(value)
