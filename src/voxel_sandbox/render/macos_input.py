from __future__ import annotations

import sys
from collections.abc import Callable
from typing import cast

_first_mouse_imp: object | None = None


def configure_macos_first_mouse_acceptance(
    *,
    platform: str | None = None,
    installer: Callable[[], object] | None = None,
) -> bool:
    """Allow the first click on an inactive macOS game window to reach Pyglet."""
    global _first_mouse_imp

    current_platform = sys.platform if platform is None else platform
    if current_platform != "darwin":
        return False
    if _first_mouse_imp is None:
        install = _install_first_mouse_method if installer is None else installer
        _first_mouse_imp = install()
    return True


def _install_first_mouse_method() -> object:
    from pyglet.libs.darwin.cocoapy import runtime
    from pyglet.window.cocoa import pyglet_view

    add_method = cast(
        Callable[[object, str, Callable[[object, object, object], bool], bytes], object],
        runtime.add_method,  # pyright: ignore[reportUnknownMemberType]
    )
    pyglet_view_class = cast(
        object,
        pyglet_view.PygletView,  # pyright: ignore[reportUnknownMemberType]
    )

    def accepts_first_mouse(_self: object, _cmd: object, _event: object) -> bool:
        return True

    return add_method(
        pyglet_view_class,
        "acceptsFirstMouse:",
        accepts_first_mouse,
        b"B@:@",
    )
