from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


def platform_font_name(platform: str) -> str:
    return "Segoe UI" if platform == "win32" else "Menlo"


class Screen(Enum):
    MAIN = auto()
    SINGLEPLAYER = auto()
    MULTIPLAYER = auto()
    SETTINGS = auto()
    GAME = auto()
    PAUSE = auto()
    CONTROLS = auto()
    AUDIO = auto()
    DEVELOPMENT = auto()
    TEXTURE_PACKS = auto()
    UPDATES = auto()


class MenuCommand(Enum):
    NONE = auto()
    CLOSE = auto()
    DISCOVER_LAN = auto()
    DIRECT_CONNECT = auto()
    EDIT_NICKNAME = auto()
    OPEN_LAN = auto()
    CYCLE_SHADOWS = auto()
    TOGGLE_CLOUDS = auto()
    TOGGLE_VSYNC = auto()
    CYCLE_RENDER_DISTANCE = auto()
    CYCLE_DIFFICULTY = auto()
    CREATE_WORLD = auto()
    REBIND_FORWARD = auto()
    REBIND_BACKWARD = auto()
    REBIND_LEFT = auto()
    REBIND_RIGHT = auto()
    REBIND_JUMP = auto()
    CYCLE_MASTER_VOLUME = auto()
    CYCLE_EFFECTS_VOLUME = auto()
    CYCLE_MUSIC_VOLUME = auto()
    CYCLE_AMBIENCE_VOLUME = auto()
    TOGGLE_SMOOTH_LIGHTING = auto()
    TOGGLE_AMBIENT_OCCLUSION = auto()
    TOGGLE_FOG = auto()
    TOGGLE_MESHER = auto()


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
        MenuItem("Back", target=Screen.MAIN),
    ),
    Screen.MULTIPLAYER: (
        MenuItem("Join LAN World", action="join_lan"),
        MenuItem("Direct Connect", action="direct_connect"),
        MenuItem("Nickname", action="nickname"),
        MenuItem("Back", target=Screen.MAIN),
    ),
    Screen.SETTINGS: (
        MenuItem("Shadow Quality", action="cycle_shadows"),
        MenuItem("Clouds", action="toggle_clouds"),
        MenuItem("VSync", action="toggle_vsync"),
        MenuItem("Render Distance", action="cycle_render_distance"),
        MenuItem("Difficulty", action="cycle_difficulty"),
        MenuItem("Texture Packs", target=Screen.TEXTURE_PACKS),
        MenuItem("Updates", target=Screen.UPDATES),
        MenuItem("Audio", target=Screen.AUDIO),
        MenuItem("Controls", target=Screen.CONTROLS),
        MenuItem("Development", target=Screen.DEVELOPMENT),
        MenuItem("Back", action="settings_back"),
    ),
    Screen.CONTROLS: (
        MenuItem("Forward", action="rebind_forward"),
        MenuItem("Backward", action="rebind_backward"),
        MenuItem("Left", action="rebind_left"),
        MenuItem("Right", action="rebind_right"),
        MenuItem("Jump", action="rebind_jump"),
        MenuItem("Back", target=Screen.SETTINGS),
    ),
    Screen.AUDIO: (
        MenuItem("Master", action="cycle_master_volume"),
        MenuItem("Effects", action="cycle_effects_volume"),
        MenuItem("Music", action="cycle_music_volume"),
        MenuItem("Ambience", action="cycle_ambience_volume"),
        MenuItem("Back", target=Screen.SETTINGS),
    ),
    Screen.DEVELOPMENT: (
        MenuItem("Smooth Lighting", action="toggle_smooth_lighting"),
        MenuItem("Ambient Occlusion", action="toggle_ambient_occlusion"),
        MenuItem("Fog", action="toggle_fog"),
        MenuItem("Mesher", action="toggle_mesher"),
        MenuItem("Back", target=Screen.SETTINGS),
    ),
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
            Screen.CONTROLS: "CONTROLS",
            Screen.AUDIO: "AUDIO",
            Screen.TEXTURE_PACKS: "TEXTURE PACKS",
            Screen.UPDATES: "UPDATES",
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
            if item.target is Screen.SETTINGS and self.screen in {Screen.MAIN, Screen.PAUSE}:
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
            Screen.CONTROLS: Screen.SETTINGS,
            Screen.AUDIO: Screen.SETTINGS,
            Screen.DEVELOPMENT: Screen.SETTINGS,
            Screen.TEXTURE_PACKS: Screen.SETTINGS,
            Screen.UPDATES: Screen.SETTINGS,
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
        if action == "create_world":
            return MenuCommand.CREATE_WORLD
        elif action == "join_lan":
            self.status = "Searching for LAN worlds..."
            return MenuCommand.DISCOVER_LAN
        elif action == "direct_connect":
            return MenuCommand.DIRECT_CONNECT
        elif action == "nickname":
            return MenuCommand.EDIT_NICKNAME
        elif action == "open_lan":
            return MenuCommand.OPEN_LAN
        elif action == "cycle_shadows":
            return MenuCommand.CYCLE_SHADOWS
        elif action == "toggle_clouds":
            return MenuCommand.TOGGLE_CLOUDS
        elif action == "toggle_vsync":
            return MenuCommand.TOGGLE_VSYNC
        if action == "cycle_render_distance":
            return MenuCommand.CYCLE_RENDER_DISTANCE
        elif action == "cycle_difficulty":
            return MenuCommand.CYCLE_DIFFICULTY
        elif action == "rebind_forward":
            return MenuCommand.REBIND_FORWARD
        elif action == "rebind_backward":
            return MenuCommand.REBIND_BACKWARD
        elif action == "rebind_left":
            return MenuCommand.REBIND_LEFT
        elif action == "rebind_right":
            return MenuCommand.REBIND_RIGHT
        elif action == "rebind_jump":
            return MenuCommand.REBIND_JUMP
        elif action == "cycle_master_volume":
            return MenuCommand.CYCLE_MASTER_VOLUME
        elif action == "cycle_effects_volume":
            return MenuCommand.CYCLE_EFFECTS_VOLUME
        elif action == "cycle_music_volume":
            return MenuCommand.CYCLE_MUSIC_VOLUME
        elif action == "cycle_ambience_volume":
            return MenuCommand.CYCLE_AMBIENCE_VOLUME
        elif action == "toggle_smooth_lighting":
            return MenuCommand.TOGGLE_SMOOTH_LIGHTING
        elif action == "toggle_ambient_occlusion":
            return MenuCommand.TOGGLE_AMBIENT_OCCLUSION
        elif action == "toggle_fog":
            return MenuCommand.TOGGLE_FOG
        elif action == "toggle_mesher":
            return MenuCommand.TOGGLE_MESHER
        elif action == "settings_back":
            self._go_to(self._settings_return)
        return MenuCommand.NONE
