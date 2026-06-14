from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from voxel_sandbox.audio.events import VolumeGroup


@dataclass(frozen=True, slots=True)
class AudioResource:
    key: str
    path: Path
    group: VolumeGroup
    loop: bool = False


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
        resources = tuple(
            AudioResource(
                key=str(entry["key"]),
                path=asset_root / str(entry["path"]),
                group=VolumeGroup(str(entry["group"])),
                loop=bool(entry.get("loop", False)),
            )
            for entry in entries
        )
        return cls(resources)

    def get(self, key: str) -> AudioResource:
        try:
            return self._resources[key]
        except KeyError as error:
            raise KeyError(f"Unknown audio resource: {key}") from error

    def __contains__(self, key: str) -> bool:
        return key in self._resources
