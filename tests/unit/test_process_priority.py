from __future__ import annotations

import os

import pytest

from voxel_sandbox.engine.perf.process_priority import (
    _lower_windows_process_priority,
    lower_background_process_priority,
)


class _FakeKernel32:
    def __init__(self) -> None:
        self.priority_calls: list[tuple[int, int]] = []

    def GetCurrentProcess(self) -> int:
        return 42

    def SetPriorityClass(self, process: int, priority: int) -> int:
        self.priority_calls.append((process, priority))
        return 1


def test_background_process_priority_uses_positive_nice_increment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    increments: list[int] = []
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(os, "nice", increments.append, raising=False)

    lower_background_process_priority()

    assert increments == [5]


def test_background_process_priority_tolerates_os_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "name", "posix")

    def reject(_increment: int) -> int:
        raise OSError("priority changes unavailable")

    monkeypatch.setattr(os, "nice", reject, raising=False)

    lower_background_process_priority()


def test_background_process_priority_is_optional_on_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.delattr(os, "nice", raising=False)

    lower_background_process_priority()


def test_windows_background_priority_targets_current_process() -> None:
    kernel32 = _FakeKernel32()

    assert _lower_windows_process_priority(kernel32) is True
    assert kernel32.priority_calls == [(42, 0x00004000)]
