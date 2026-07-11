from __future__ import annotations

import pytest

from voxel_sandbox.render import macos_input


@pytest.fixture(autouse=True)
def reset_first_mouse_imp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(macos_input, "_first_mouse_imp", None)


def test_non_macos_does_not_install_first_mouse_method() -> None:
    calls = 0

    def install() -> object:
        nonlocal calls
        calls += 1
        return object()

    assert not macos_input.configure_macos_first_mouse_acceptance(
        platform="linux",
        installer=install,
    )
    assert calls == 0


def test_macos_installs_first_mouse_method_once_and_retains_imp() -> None:
    imp = object()
    calls = 0

    def install() -> object:
        nonlocal calls
        calls += 1
        return imp

    assert macos_input.configure_macos_first_mouse_acceptance(
        platform="darwin",
        installer=install,
    )
    assert macos_input.configure_macos_first_mouse_acceptance(
        platform="darwin",
        installer=install,
    )
    assert calls == 1
    assert macos_input._first_mouse_imp is imp  # pyright: ignore[reportPrivateUsage]
