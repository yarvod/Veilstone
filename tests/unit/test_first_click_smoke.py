from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from voxel_sandbox.tools.first_click_smoke import (
    build_first_click_smoke_metadata,
    validate_first_click_smoke_metadata,
    write_first_click_smoke_metadata,
)


def _valid_metadata():
    return build_first_click_smoke_metadata(
        initial_motion=False,
        platform="darwin",
        cocoa_accepts_first_mouse=True,
        action_counts={
            "settings": 1,
            "settings_back": 1,
            "singleplayer": 1,
            "world_list_cancel": 1,
            "resume": 1,
        },
        resume_captured=True,
        first_motion_yaw_delta=2.88,
        walk_distance=0.16,
        menu_screenshot=Path("screenshots/menu.png"),
        game_screenshot=Path("screenshots/game.png"),
    )


def test_first_click_smoke_metadata_validates_and_writes(tmp_path: Path) -> None:
    metadata = validate_first_click_smoke_metadata(_valid_metadata())
    path = tmp_path / "first-click.json"

    write_first_click_smoke_metadata(path, metadata)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["cocoa_accepts_first_mouse"] is True
    assert payload["settings_actions"] == 1
    assert payload["resume_actions"] == 1
    assert payload["invariants_passed"] is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("cocoa_accepts_first_mouse", False, "Cocoa view"),
        ("settings_actions", 0, "action count"),
        ("resume_actions", 2, "action count"),
        ("resume_captured", False, "exclusive mouse capture"),
        ("first_motion_yaw_delta", 0.0, "rotate the camera"),
        ("walk_distance", 0.0, "move the player"),
    ],
)
def test_first_click_smoke_metadata_rejects_regressions(
    field: str,
    value: float | bool | int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_first_click_smoke_metadata(replace(_valid_metadata(), **{field: value}))
