# pyright: reportPrivateUsage=false, reportUnknownArgumentType=false

from __future__ import annotations

import math
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Protocol, cast

from voxel_sandbox.app.commands import (
    CommandError,
    ListStructuresCommand,
    ResourcePackCommand,
    SetDifficultyCommand,
    SetTimeCommand,
    SpawnStructureCommand,
    TeleportCommand,
    ToggleStructureCommand,
    parse_command,
)
from voxel_sandbox.app.settings import AppSettings, save_user_settings
from voxel_sandbox.application.resource_packs import (
    ApplyResourcePackUseCase,
    TexturePackServicePort,
)
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.generation import TerrainGenerator
from voxel_sandbox.engine.physics.player import PlayerController

if TYPE_CHECKING:
    from voxel_sandbox.render.window import GameWindow


class GameplayView(Protocol):
    world_runtime: Any
    settings: AppSettings
    world_renderer: Any
    network_session: Any | None
    network_players: dict[int, dict[str, object]]
    player: PlayerController | None
    camera: Any
    lan_server: Any | None
    structure_world: Any
    entities: Any | None
    inventory_status: str

    def _is_solid_combined(self, x: int, y: int, z: int) -> bool: ...

    def apply_resource_pack(self, path: str | None) -> str: ...


class GameplayWindowAdapter:
    def __init__(self, window: GameWindow) -> None:
        object.__setattr__(self, "_window", window)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._window, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._window, name, value)

    def apply_resource_pack(self, path: str | None) -> str:
        texture_packs = self._window.app_runtime.texture_packs
        if texture_packs is None:
            raise RuntimeError("GameplayController requires texture-pack service")
        result = ApplyResourcePackUseCase(
            texture_packs=cast(TexturePackServicePort, texture_packs),
            settings_store=self._window.app_runtime.settings_store,
        ).execute(
            path=path,
            settings=self._window.settings,
            renderer=self._window.world_renderer,
            block_registry=cast(BlockRegistry, self._window.world_runtime.block_registry),
            cache_root=self._window.active_save_root.parent / "texture_cache",
        )
        if result.applied:
            self._window.settings = result.settings
        return result.status


class GameplayController:
    def __init__(self, win: GameplayView) -> None:
        self.win = win

    def _block_registry(self) -> BlockRegistry:
        return cast(BlockRegistry, self.win.world_runtime.block_registry)

    def _terrain_generator(self) -> TerrainGenerator:
        return cast(TerrainGenerator, self.win.world_runtime.generation)

    def _player(self) -> PlayerController:
        player = self.win.player
        if player is None:
            raise RuntimeError("GameplayController requires a local player")
        return player

    def execute_command(self, source: str) -> None:
        win = self.win
        try:
            command = parse_command(source)
        except CommandError as error:
            win.inventory_status = str(error)
            return
        match command:
            case SetTimeCommand():
                self._handle_set_time(command)
            case SetDifficultyCommand():
                self._handle_set_difficulty(command)
            case ResourcePackCommand():
                self._handle_resource_pack(command)
            case TeleportCommand():
                self._handle_teleport(command)
            case SpawnStructureCommand():
                self._handle_spawn_structure(command)
            case ToggleStructureCommand():
                self._handle_toggle_structure(command)
            case ListStructuresCommand():
                self._handle_list_structures()
            case _:
                win.inventory_status = (
                    "/time set <...>; /difficulty <...>; "
                    "/resourcepack <path|default>; /structure <spawn|toggle|list>"
                )

    def _handle_set_time(self, command: SetTimeCommand) -> None:
        win = self.win
        win.world_renderer.time_of_day = command.time_of_day
        if command.freeze:
            win.world_renderer.day_cycle_seconds = 0.0
        else:
            win.world_renderer.day_cycle_seconds = win.settings.graphics.day_cycle_seconds
        win.inventory_status = (
            f"Time set to {command.label}{' (frozen)' if command.freeze else ''}."
        )

    def _handle_set_difficulty(self, command: SetDifficultyCommand) -> None:
        self._set_difficulty(command.difficulty)
        self.win.inventory_status = f"Difficulty set to {command.difficulty}."

    def _handle_resource_pack(self, command: ResourcePackCommand) -> None:
        win = self.win
        win.inventory_status = win.apply_resource_pack(command.path)

    def _handle_teleport(self, command: TeleportCommand) -> None:
        win = self.win
        if win.network_session is None:
            win.inventory_status = "Teleportation requires multiplayer."
            return
        target_pos: tuple[float, float, float] | None = None
        for _p_id, p in win.network_players.items():
            if str(p.get("name", "")).casefold() == command.target_name.casefold():
                raw_position = p.get("position")
                if (
                    isinstance(raw_position, list)
                    and len(raw_position) == 3
                    and all(
                        isinstance(value, int | float) for value in cast(list[object], raw_position)
                    )
                ):
                    values = cast(list[int | float], raw_position)
                    target_pos = float(values[0]), float(values[1]), float(values[2])
                break
        if target_pos is not None:
            player = self._player()
            player.x, player.y, player.z = target_pos
            win.inventory_status = f"Teleported to {command.target_name}."
        else:
            win.inventory_status = f"Player {command.target_name} not found."

    def _handle_spawn_structure(self, command: SpawnStructureCommand) -> None:
        win = self.win
        if win.lan_server is None or win.world_renderer.remote_mode:
            win.inventory_status = "Structure commands require a local authoritative world."
            return
        distance = 5.0
        player = self._player()
        origin = (
            math.floor(player.x + win.camera.direction[0] * distance),
            math.floor(player.y),
            math.floor(player.z + win.camera.direction[2] * distance),
        )
        entity = win.lan_server.spawn_structure(command.key, origin)
        win.structure_world = win.lan_server.structure_world
        win.inventory_status = f"Spawned {command.key} structure #{entity.entity_id}."

    def _handle_toggle_structure(self, command: ToggleStructureCommand) -> None:
        win = self.win
        if win.lan_server is None or win.world_renderer.remote_mode:
            win.inventory_status = "Structure commands require a local authoritative world."
            return
        try:
            entity = win.lan_server.toggle_structure(command.entity_id)
        except KeyError:
            win.inventory_status = f"Unknown structure #{command.entity_id}."
            return
        win.inventory_status = (
            f"Structure #{entity.entity_id} {'activated' if entity.active else 'stopped'}."
        )

    def _handle_list_structures(self) -> None:
        win = self.win
        structures = sorted(
            win.structure_world.entities.values(),
            key=lambda item: item.entity_id,
        )
        win.inventory_status = (
            ", ".join(f"#{item.entity_id} {item.key}" for item in structures)
            if structures
            else "No runtime structures."
        )

    def _set_difficulty(self, difficulty: str) -> None:
        win = self.win
        win.settings = replace(
            win.settings,
            gameplay=replace(win.settings.gameplay, difficulty=difficulty),
        )
        player = self._player()
        self._maintain_population((player.x, player.y, player.z))
        save_user_settings(win.settings)

    def _maintain_population(self, center: tuple[float, float, float]) -> None:
        win = self.win
        entities = win.entities
        if entities is None:
            return
        hostile_count = 0 if win.settings.gameplay.difficulty == "peaceful" else 1
        entities.maintain_population(
            center,
            self._terrain_generator().height_at,
            self._is_entity_hazard,
            hostile_count=hostile_count,
            hostile_spawn_allowed=self._hostile_spawn_allowed,
            is_solid=win._is_solid_combined,
        )

    def _hostile_spawn_allowed(self, x: int, y: int, z: int) -> bool:
        win = self.win
        light_level = win.world_renderer.spawn_light_level(x, y, z)
        return (
            light_level is not None
            and light_level <= win.settings.gameplay.hostile_spawn_light_limit
        )

    def _is_entity_hazard(self, x: int, y: int, z: int) -> bool:
        block_id = self.win.world_renderer.get_block(x, y, z)
        return self._block_registry().by_id(block_id).is_fluid
