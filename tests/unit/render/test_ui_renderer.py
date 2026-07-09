"""Unit tests for UiRenderer widget interaction and list screen support."""

# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.support.pyglet_gl import has_shader_capable_gl

pytestmark = pytest.mark.skipif(
    not has_shader_capable_gl(), reason="requires shader-capable OpenGL display"
)


def _make_renderer(w: int = 800, h: int = 600):
    from voxel_sandbox.render.ui.renderer import UiRenderer

    return UiRenderer(w, h)


# ---------------------------------------------------------------------------
# Action button persistence — pressed state must survive across frames
# ---------------------------------------------------------------------------


def test_action_buttons_are_persistent_across_update_world_list_calls() -> None:
    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer()
    r._current_screen = Screen.SINGLEPLAYER

    cb = MagicMock()
    r.update_world_list(
        [], -1, lambda idx: None, cb, lambda: None, lambda: None, lambda: None, lambda: None
    )
    btn_first = r._action_primary

    r.update_world_list(
        [], -1, lambda idx: None, cb, lambda: None, lambda: None, lambda: None, lambda: None
    )
    btn_second = r._action_primary

    assert btn_first is btn_second, "Primary action button must be the same object across calls"


def test_action_button_callback_is_updated_without_recreating() -> None:
    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer()
    r._current_screen = Screen.SINGLEPLAYER

    cb_first = MagicMock()
    r.update_world_list(
        [], -1, lambda idx: None, cb_first, lambda: None, lambda: None, lambda: None, lambda: None
    )
    assert r._action_primary.on_click_callback is cb_first

    cb_second = MagicMock()
    r.update_world_list(
        [], -1, lambda idx: None, cb_second, lambda: None, lambda: None, lambda: None, lambda: None
    )
    assert r._action_primary.on_click_callback is cb_second


def test_pressed_state_survives_across_frames() -> None:
    """Simulate: press on frame N, render frame N+1, release on frame N+1 → click fires."""
    from pyglet.window import mouse

    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer(800, 600)
    r._current_screen = Screen.SINGLEPLAYER

    fired = []
    r.update_world_list(
        [],
        -1,
        lambda idx: None,
        lambda: fired.append("play"),
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        primary_label="Play",
    )
    # Layout is called inside update_world_list; action hboxes are positioned.

    play_btn = r._action_primary
    assert play_btn.on_click_callback is not None
    assert play_btn.bounds.width > 0, "Button must have non-zero bounds after layout"

    # Simulate press at button centre.
    cx = int(play_btn.bounds.x + play_btn.bounds.width / 2)
    cy = int(play_btn.bounds.y + play_btn.bounds.height / 2)
    r.on_mouse_press(cx, cy, mouse.LEFT, 0)
    assert play_btn.pressed is True

    # Frame N+1: update_world_list called again (simulates next frame).
    r.update_world_list(
        [],
        -1,
        lambda idx: None,
        lambda: fired.append("play"),
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        primary_label="Play",
    )

    # Button object must be the SAME — pressed state intact.
    assert r._action_primary is play_btn
    assert r._action_primary.pressed is True

    # Release: on_click fires.
    r.on_mouse_release(cx, cy, mouse.LEFT, 0)
    assert len(fired) == 1, "Click callback should fire exactly once"


def test_long_menu_keeps_first_button_below_title() -> None:
    from voxel_sandbox.render.ui.menu import MenuController, Screen

    r = _make_renderer(1024, 768)
    menu = MenuController()
    menu.screen = Screen.SETTINGS

    r.update(menu, lambda index: menu.items[index].label)

    first_button = r.buttons[0]
    assert first_button.bounds.y + first_button.bounds.height <= r.title_label.bounds.y


# ---------------------------------------------------------------------------
# Texture pack screen adds content to root_panel
# ---------------------------------------------------------------------------


def test_texture_pack_screen_widgets_added_to_root_panel() -> None:
    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer()
    r._current_screen = Screen.TEXTURE_PACKS

    r.update_world_list(
        [("Default", None), ("Pack A", None)],
        0,
        lambda idx: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        primary_label="Apply Pack",
        secondary_label="",
        edit_label="",
        delete_label="",
        cancel_label="Back",
    )

    children = r.root_panel.children
    assert r.world_list_vbox in children, "world_list_vbox must be in root_panel for TEXTURE_PACKS"
    assert r.world_actions_hbox1 in children
    assert r.world_actions_hbox2 in children


def test_updates_screen_widgets_added_to_root_panel() -> None:
    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer()
    r._current_screen = Screen.UPDATES
    r.update_world_list(
        [("v0.2.0 - Veilstone v0.2.0", None)],
        0,
        lambda idx: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        primary_label="Download",
        secondary_label="Refresh",
        edit_label="",
        delete_label="",
        cancel_label="Back",
    )

    children = r.root_panel.children
    assert r.world_list_vbox in children, "world_list_vbox must be in root_panel UPDATES"
    assert r.world_actions_hbox1 in children
    assert r.world_actions_hbox2 in children


# ---------------------------------------------------------------------------
# _layout covers both SINGLEPLAYER and TEXTURE_PACKS
# ---------------------------------------------------------------------------


def test_layout_positions_list_widgets_for_singleplayer() -> None:
    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer(800, 600)
    r._current_screen = Screen.SINGLEPLAYER
    r._layout()

    assert r.world_list_vbox.bounds.y == 120
    assert r.world_actions_hbox1.bounds.y == 60
    assert r.world_actions_hbox2.bounds.y == 10


def test_layout_positions_list_widgets_for_texture_packs() -> None:
    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer(800, 600)
    r._current_screen = Screen.TEXTURE_PACKS
    r._layout()

    assert r.world_list_vbox.bounds.y == 120
    assert r.world_actions_hbox1.bounds.y == 60
    assert r.world_actions_hbox2.bounds.y == 10


# ---------------------------------------------------------------------------
# World card click routing
# ---------------------------------------------------------------------------


def test_card_on_select_fires_when_card_clicked() -> None:
    from pyglet.window import mouse

    from voxel_sandbox.render.ui.menu import Screen

    r = _make_renderer(800, 600)
    r._current_screen = Screen.SINGLEPLAYER
    r.root_panel.children.append(r.world_list_vbox)

    selected = []

    r.update_world_list(
        [("World A", None)],
        0,
        lambda idx: selected.append(idx),
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
    )

    # Card should be in world_list_vbox.
    assert len(r.world_cards) == 1
    card = r.world_cards[0]

    cx = int(card.bounds.x + card.bounds.width / 2)
    cy = int(card.bounds.y + card.bounds.height / 2)
    r.on_mouse_press(cx, cy, mouse.LEFT, 0)
    r.on_mouse_release(cx, cy, mouse.LEFT, 0)

    assert 0 in selected
