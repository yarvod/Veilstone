from __future__ import annotations

from voxel_sandbox.render.ui.menu import (
    MENUS,
    MenuCommand,
    MenuController,
    Screen,
    platform_font_name,
)


def labels(screen: Screen) -> list[str]:
    return [item.label for item in MENUS[screen]]


def test_player_facing_menu_tree() -> None:
    assert labels(Screen.MAIN) == ["Singleplayer", "Multiplayer", "Settings", "Exit"]
    assert labels(Screen.SINGLEPLAYER) == ["Create World", "Back"]
    assert labels(Screen.MULTIPLAYER) == [
        "Join LAN World",
        "Direct Connect",
        "Nickname",
        "Back",
    ]
    assert labels(Screen.PAUSE) == ["Resume", "Open to LAN", "Settings", "Main Menu"]


def test_singleplayer_enters_game_and_escape_opens_pause() -> None:
    menu = MenuController()
    menu.activate()
    assert menu.screen is Screen.SINGLEPLAYER

    assert menu.activate() is MenuCommand.CREATE_WORLD


def test_singleplayer_back_goes_to_main() -> None:
    menu = MenuController()
    menu.screen = Screen.SINGLEPLAYER
    menu.select(1)
    menu.activate()
    assert menu.screen is Screen.MAIN


def test_pause_settings_returns_to_pause() -> None:
    menu = MenuController()
    menu.screen = Screen.PAUSE
    menu.select(2)
    menu.activate()
    assert menu.screen is Screen.SETTINGS

    menu.select(len(menu.items) - 1)
    menu.activate()
    assert menu.screen is Screen.PAUSE


def test_audio_back_does_not_replace_settings_return_screen() -> None:
    menu = MenuController()
    menu.select(2)
    menu.activate()
    assert menu.screen is Screen.SETTINGS

    menu.select(4)
    menu.activate()
    assert menu.screen is Screen.AUDIO
    menu.select(len(menu.items) - 1)
    menu.activate()
    assert menu.screen is Screen.SETTINGS

    menu.select(len(menu.items) - 1)
    menu.activate()
    assert menu.screen is Screen.MAIN


def test_settings_menu_exposes_runtime_graphics_actions() -> None:
    assert labels(Screen.SETTINGS) == [
        "Shadow Quality",
        "Clouds",
        "VSync",
        "Difficulty",
        "Audio",
        "Controls",
        "Back",
    ]
    menu = MenuController()
    menu.screen = Screen.SETTINGS
    assert menu.activate() is MenuCommand.CYCLE_SHADOWS
    menu.select(1)
    assert menu.activate() is MenuCommand.TOGGLE_CLOUDS
    menu.select(3)
    assert menu.activate() is MenuCommand.CYCLE_DIFFICULTY


def test_controls_menu_exposes_rebinding_actions() -> None:
    assert labels(Screen.CONTROLS) == ["Forward", "Backward", "Left", "Right", "Jump", "Back"]
    menu = MenuController()
    menu.screen = Screen.CONTROLS

    assert menu.activate() is MenuCommand.REBIND_FORWARD
    menu.select(4)
    assert menu.activate() is MenuCommand.REBIND_JUMP


def test_open_to_lan_returns_application_command() -> None:
    menu = MenuController()
    menu.screen = Screen.PAUSE
    menu.select(1)

    assert menu.activate() is MenuCommand.OPEN_LAN


def test_exit_returns_close_command() -> None:
    menu = MenuController()
    menu.select(3)
    assert menu.activate() is MenuCommand.CLOSE


def test_join_lan_returns_discovery_command() -> None:
    menu = MenuController()
    menu.screen = Screen.MULTIPLAYER

    assert menu.activate() is MenuCommand.DISCOVER_LAN
    assert "Searching" in menu.status


def test_direct_connect_and_nickname_return_input_commands() -> None:
    menu = MenuController()
    menu.screen = Screen.MULTIPLAYER

    menu.select(1)
    assert menu.activate() is MenuCommand.DIRECT_CONNECT
    menu.select(2)
    assert menu.activate() is MenuCommand.EDIT_NICKNAME


def test_platform_font_uses_windows_native_metrics() -> None:
    assert platform_font_name("win32") == "Segoe UI"
    assert platform_font_name("darwin") == "Menlo"
