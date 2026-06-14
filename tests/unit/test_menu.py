from __future__ import annotations

from voxel_sandbox.render.ui.menu import MENUS, MenuCommand, MenuController, Screen


def labels(screen: Screen) -> list[str]:
    return [item.label for item in MENUS[screen]]


def test_player_facing_menu_tree() -> None:
    assert labels(Screen.MAIN) == ["Singleplayer", "Multiplayer", "Settings", "Exit"]
    assert labels(Screen.SINGLEPLAYER) == ["Create World", "Load World", "Back"]
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


def test_load_world_returns_application_command() -> None:
    menu = MenuController()
    menu.activate()
    menu.select(1)

    assert menu.activate() is MenuCommand.LOAD_WORLD


def test_pause_settings_returns_to_pause() -> None:
    menu = MenuController()
    menu.screen = Screen.PAUSE
    menu.select(2)
    menu.activate()
    assert menu.screen is Screen.SETTINGS

    menu.select(len(menu.items) - 1)
    menu.activate()
    assert menu.screen is Screen.PAUSE


def test_settings_menu_exposes_runtime_graphics_actions() -> None:
    assert labels(Screen.SETTINGS) == [
        "Shadow Quality",
        "Clouds",
        "Postprocess",
        "VSync",
        "Back",
    ]
    menu = MenuController()
    menu.screen = Screen.SETTINGS
    assert menu.activate() is MenuCommand.CYCLE_SHADOWS
    menu.select(1)
    assert menu.activate() is MenuCommand.TOGGLE_CLOUDS


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
