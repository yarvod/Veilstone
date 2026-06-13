from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Screen(Enum):
    MAIN = auto()
    SINGLEPLAYER = auto()
    MULTIPLAYER = auto()
    SETTINGS = auto()
    GAME = auto()
    PAUSE = auto()


class MenuCommand(Enum):
    NONE = auto()
    CLOSE = auto()


@dataclass(frozen=True, slots=True)
class MenuItem:
    label: str
    target: Screen | None = None
    action: str | None = None


MENUS: dict[Screen, tuple[MenuItem, ...]] = {
    Screen.MAIN: (
        MenuItem("Singleplayer", target=Screen.SINGLEPLAYER),
        MenuItem("Multiplayer", target=Screen.MULTIPLAYER),
        MenuItem("Settings", target=Screen.SETTINGS),
        MenuItem("Exit", action="exit"),
    ),
    Screen.SINGLEPLAYER: (
        MenuItem("Create World", action="create_world"),
        MenuItem("Load World", action="load_world"),
        MenuItem("Back", target=Screen.MAIN),
    ),
    Screen.MULTIPLAYER: (
        MenuItem("Join LAN World", action="join_lan"),
        MenuItem("Direct Connect", action="direct_connect"),
        MenuItem("Back", target=Screen.MAIN),
    ),
    Screen.SETTINGS: (MenuItem("Back", action="settings_back"),),
    Screen.PAUSE: (
        MenuItem("Resume", target=Screen.GAME),
        MenuItem("Open to LAN", action="open_lan"),
        MenuItem("Settings", target=Screen.SETTINGS),
        MenuItem("Main Menu", target=Screen.MAIN),
    ),
}


class MenuController:
    def __init__(self) -> None:
        self.screen = Screen.MAIN
        self.selected_index = 0
        self.status = ""
        self.world_open_to_lan = False
        self._settings_return = Screen.MAIN

    @property
    def items(self) -> tuple[MenuItem, ...]:
        return MENUS.get(self.screen, ())

    @property
    def title(self) -> str:
        titles = {
            Screen.MAIN: "VEILSTONE",
            Screen.SINGLEPLAYER: "SINGLEPLAYER",
            Screen.MULTIPLAYER: "MULTIPLAYER",
            Screen.SETTINGS: "SETTINGS",
            Screen.PAUSE: "PAUSED",
        }
        return titles.get(self.screen, "")

    @property
    def in_game(self) -> bool:
        return self.screen is Screen.GAME

    def move_selection(self, offset: int) -> None:
        if self.items:
            self.selected_index = (self.selected_index + offset) % len(self.items)

    def select(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self.selected_index = index

    def activate(self) -> MenuCommand:
        if not self.items:
            return MenuCommand.NONE
        item = self.items[self.selected_index]
        if item.target is not None:
            if item.target is Screen.SETTINGS:
                self._settings_return = self.screen
            self._go_to(item.target)
            return MenuCommand.NONE
        return self._run_action(item.action)

    def back(self) -> None:
        targets = {
            Screen.SINGLEPLAYER: Screen.MAIN,
            Screen.MULTIPLAYER: Screen.MAIN,
            Screen.SETTINGS: self._settings_return,
            Screen.PAUSE: Screen.GAME,
            Screen.GAME: Screen.PAUSE,
        }
        target = targets.get(self.screen)
        if target is not None:
            self._go_to(target)

    def _go_to(self, screen: Screen) -> None:
        self.screen = screen
        self.selected_index = 0
        self.status = ""

    def _run_action(self, action: str | None) -> MenuCommand:
        if action == "exit":
            return MenuCommand.CLOSE
        if action in {"create_world", "load_world"}:
            self._go_to(Screen.GAME)
        elif action == "join_lan":
            self.status = "Searching for LAN worlds..."
        elif action == "direct_connect":
            self.status = "Direct Connect screen is scheduled for the network phase."
        elif action == "open_lan":
            self.world_open_to_lan = True
            self.status = "Local world marked open to LAN. Networking follows in Phase 13."
        elif action == "settings_back":
            self._go_to(self._settings_return)
        return MenuCommand.NONE
