from __future__ import annotations

import os

import pytest

from voxel_sandbox.engine.perf.process_priority import lower_background_process_priority


def test_background_process_priority_uses_positive_nice_increment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    increments: list[int] = []
    monkeypatch.setattr(os, "nice", increments.append, raising=False)

    lower_background_process_priority()

    assert increments == [5]


def test_background_process_priority_tolerates_os_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject(_increment: int) -> int:
        raise OSError("priority changes unavailable")

    monkeypatch.setattr(os, "nice", reject, raising=False)

    lower_background_process_priority()


def test_background_process_priority_is_optional_on_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(os, "nice", raising=False)

    lower_background_process_priority()
