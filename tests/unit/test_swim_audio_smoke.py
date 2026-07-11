from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from voxel_sandbox.tools.swim_audio_smoke import (
    build_swim_audio_smoke_metadata,
    validate_swim_audio_smoke_metadata,
    write_swim_audio_smoke_metadata,
)


def _valid_metadata():
    return build_swim_audio_smoke_metadata(
        screenshot=Path("screenshots/swim.png"),
        audio_backend="PygletAudioBackend",
        stroke_events=2,
        played_swim_sounds=2,
        water_entries=1,
        water_exits=1,
        played_splash_sounds=2,
        swim_distance=3.75,
        in_water_after_swim=True,
    )


def test_swim_audio_smoke_metadata_validates_and_writes(tmp_path: Path) -> None:
    metadata = validate_swim_audio_smoke_metadata(_valid_metadata())
    path = tmp_path / "swim.json"

    write_swim_audio_smoke_metadata(path, metadata)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["stroke_events"] == 2
    assert payload["played_swim_sounds"] == 2
    assert payload["invariants_passed"] is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("audio_backend", "NullAudioBackend", "real Pyglet"),
        ("stroke_events", 3, "cadence"),
        ("played_swim_sounds", 1, "audio routing"),
        ("water_entries", 2, "transition"),
        ("played_splash_sounds", 1, "splash"),
        ("swim_distance", 0.0, "move through water"),
        ("in_water_after_swim", False, "move through water"),
    ],
)
def test_swim_audio_smoke_metadata_rejects_regressions(
    field: str,
    value: str | int | float | bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_swim_audio_smoke_metadata(replace(_valid_metadata(), **{field: value}))
