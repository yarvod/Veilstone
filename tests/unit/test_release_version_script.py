from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path("scripts/set_release_version.py")
SPEC = importlib.util.spec_from_file_location("set_release_version", SCRIPT_PATH)
assert SPEC is not None
set_release_version = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(set_release_version)


def test_version_from_release_tag_strips_v_prefix() -> None:
    assert set_release_version.version_from_tag("v0.2.0") == "0.2.0"


def test_version_from_release_tag_rejects_plain_version() -> None:
    with pytest.raises(SystemExit):
        set_release_version.version_from_tag("0.2.0")
