from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.tools.input_lifecycle_smoke import (
    build_input_lifecycle_metadata,
    validate_input_lifecycle_metadata,
    write_input_lifecycle_metadata,
)


def _valid_metadata():
    return build_input_lifecycle_metadata(
        screenshot=Path("screenshots/input.png"),
        walk_distance=0.16,
        post_release_drift=0.0,
        pause_keys_cleared=True,
        post_resume_drift=0.0,
        resume_clicks=2,
        resume_captured=True,
        first_motion_yaw_delta=2.88,
        inventory_keys_cleared=True,
        focus_keys_cleared=True,
        focus_recaptured=True,
    )


def test_input_lifecycle_metadata_validates_and_writes(tmp_path: Path) -> None:
    metadata = validate_input_lifecycle_metadata(_valid_metadata())
    path = tmp_path / "input.json"

    write_input_lifecycle_metadata(path, metadata)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["walk_distance"] == 0.16
    assert payload["post_release_drift"] == 0.0
    assert payload["resume_clicks"] == 2
    assert payload["invariants_passed"] is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("post_release_drift", 0.02, "ordinary key release"),
        ("pause_keys_cleared", False, "Pause did not clear"),
        ("post_resume_drift", 0.02, "stale input"),
        ("inventory_keys_cleared", False, "Inventory transition"),
        ("focus_recaptured", False, "Focus transition"),
    ],
)
def test_input_lifecycle_metadata_rejects_regressions(
    field: str,
    value: float | bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_input_lifecycle_metadata(replace(_valid_metadata(), **{field: value}))


def test_input_lifecycle_smoke_skips_successfully_without_display(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import pyglet

    from voxel_sandbox.tools.input_lifecycle_smoke import run_input_lifecycle_smoke

    def no_screens() -> list[object]:
        return []

    monkeypatch.setattr(
        pyglet.display,
        "get_display",
        lambda: SimpleNamespace(get_screens=no_screens),
    )

    assert run_input_lifecycle_smoke(AppSettings()) == 0
    assert capsys.readouterr().out == "input-lifecycle-smoke: skipped (no active display)\n"
