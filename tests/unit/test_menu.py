from __future__ import annotations

from voxel_sandbox.render.ui.menu import MENUS, MenuCommand, MenuController, Screen


def labels(screen: Screen) -> list[str]:
    return [item.label for item in MENUS[screen]]


def test_player_facing_menu_tree() -> None:
    assert labels(Screen.MAIN) == ["Singleplayer", "Multiplayer", "Settings", "Exit"]
    assert labels(Screen.SINGLEPLAYER) == ["Create World", "Load World", "Back"]
    assert labels(Screen.MULTIPLAYER) == ["Join LAN World", "Direct Connect", "Back"]
    assert labels(Screen.PAUSE) == ["Resume", "Open to LAN", "Settings", "Main Menu"]


def test_singleplayer_enters_game_and_escape_opens_pause() -> None:
    menu = MenuController()
    menu.activate()
    assert menu.screen is Screen.SINGLEPLAYER

    menu.activate()
    assert menu.screen is Screen.GAME

    menu.back()
    assert menu.screen is Screen.PAUSE


def test_pause_settings_returns_to_pause() -> None:
    menu = MenuController()
    menu.screen = Screen.PAUSE
    menu.select(2)
    menu.activate()
    assert menu.screen is Screen.SETTINGS

    menu.activate()
    assert menu.screen is Screen.PAUSE


def test_open_to_lan_records_intent_without_claiming_network_is_ready() -> None:
    menu = MenuController()
    menu.screen = Screen.PAUSE
    menu.select(1)

    assert menu.activate() is MenuCommand.NONE
    assert menu.world_open_to_lan
    assert "Phase 13" in menu.status


def test_exit_returns_close_command() -> None:
    menu = MenuController()
    menu.select(3)
    assert menu.activate() is MenuCommand.CLOSE


def test_join_lan_returns_discovery_command() -> None:
    menu = MenuController()
    menu.screen = Screen.MULTIPLAYER

    assert menu.activate() is MenuCommand.DISCOVER_LAN
    assert "Searching" in menu.status
