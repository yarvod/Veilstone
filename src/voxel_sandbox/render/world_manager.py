# pyright: reportPrivateUsage=false

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

from voxel_sandbox.app.paths import application_data_root
from voxel_sandbox.domain.inventory import Hotbar, Inventory
from voxel_sandbox.domain.items import ItemStack
from voxel_sandbox.engine.ecs import EntitySimulation
from voxel_sandbox.engine.physics import PlayerController
from voxel_sandbox.infrastructure.storage import PlayerSnapshot, WorldStorage
from voxel_sandbox.render.ui.menu import Screen

if TYPE_CHECKING:
    from voxel_sandbox.render.window import GameWindow

LOGGER = logging.getLogger(__name__)


class WorldManager:
    def __init__(self, win: GameWindow) -> None:
        self.win = win

    def create_world(self, name: str, seed: str) -> None:
        root = application_data_root() / self._world_slug(name)
        WorldStorage(root).ensure_world(name=name, seed=seed)
        self._switch_world(root)

    def load_world(self, name: str) -> bool:
        match = next(
            (
                path
                for world_name, path in self._saved_worlds()
                if name.casefold() in {world_name.casefold(), path.name.casefold()}
            ),
            None,
        )
        if match is None:
            return False
        self._switch_world(match)
        return True

    def _switch_world(self, save_root: Path) -> None:
        win = self.win
        self._save_player()
        win.world_renderer.autosave()
        win._net.stop_services()
        win.world_renderer.release()
        win.active_save_root = save_root
        win.world_renderer = win._create_world_renderer(save_root)
        spawn_x, spawn_y, spawn_z = win.world_renderer.spawn_position
        win.player = PlayerController(x=spawn_x, y=spawn_y, z=spawn_z)
        win.inventory = Inventory()
        win.hotbar = Hotbar(win.inventory)
        win.inventory.set(0, ItemStack(3, 32), win.item_registry)
        win.inventory.set(1, ItemStack(7, 8), win.item_registry)
        win.inventory.set(2, ItemStack(8, 1), win.item_registry)
        win.inventory.set(3, ItemStack(4, 4), win.item_registry)
        win.player_health = 20.0
        saved = win.world_renderer.storage.load_player(win.item_registry)
        if saved is not None:
            win.world_renderer.storage.restore_inventory(saved, win.inventory, win.item_registry)
            win.player_health = saved.health
            win.hotbar.select(saved.selected_slot)
            self.restore_player_position(saved.position)
        win.entities = EntitySimulation(seed=win.world_renderer.generator.seed.value)
        win._gameplay._maintain_population((win.player.x, win.player.y, win.player.z))
        win.network_players.clear()
        win.remote_player_entities.clear()
        win.remote_player_interpolation.clear()
        win.requested_remote_chunks.clear()
        win.last_snapshot_sequence = 0
        win.structure_world = win.world_renderer.storage.load_structure_world()
        win.last_structure_revision = win.structure_world.revision
        win._net.start_local_authority()
        win.menu.screen = Screen.GAME
        win._sync_game_state()
        win.menu.status = ""
        win._sync_camera_to_player()
        win._sync_mouse_capture()

    def _save_player(self) -> None:
        win = self.win
        win.world_renderer.storage.save_player(
            PlayerSnapshot(
                (win.player.x, win.player.y, win.player.z),
                win.player_health,
                win.hotbar.selected_index,
                tuple(win.inventory),
            )
        )
        if win.lan_server is not None:
            win.lan_server.save()

    def restore_player_position(self, position: tuple[float, float, float]) -> bool:
        win = self.win
        if not self._position_within_world(position):
            self.move_player_to_spawn()
            return False
        x, y, z = position
        win.world_renderer.ensure_collision_area_loaded(x, z, win.player.width / 2.0)
        win.player.x, win.player.y, win.player.z = x, y, z
        win.player.velocity_y = 0.0
        win.player.on_ground = False
        if win.player.collides(win.world_renderer.is_solid_block):
            self.move_player_to_spawn()
            return False
        return True

    def invalid_player_position_reason(self) -> str | None:
        player = self.win.player
        if not all(math.isfinite(v) for v in (player.x, player.y, player.z)):
            return "non-finite coordinate"
        if not -256.0 <= player.y <= 1024.0:
            return f"vertical coordinate {player.y:.2f} outside safety bounds"
        if abs(player.x) > 30_000_000.0 or abs(player.z) > 30_000_000.0:
            return "horizontal coordinate outside safety bounds"
        return None

    def move_player_to_spawn(self) -> None:
        win = self.win
        spawn_x, spawn_y, spawn_z = win.world_renderer.spawn_position
        win.player.x, win.player.y, win.player.z = spawn_x, spawn_y, spawn_z
        win.player.velocity_y = 0.0
        win.player.on_ground = False

    def _position_within_world(self, position: tuple[float, float, float]) -> bool:
        x, y, z = position
        return (
            all(math.isfinite(v) for v in position)
            and -256.0 <= y <= 1024.0
            and abs(x) <= 30_000_000.0
            and abs(z) <= 30_000_000.0
        )

    @staticmethod
    def _saved_worlds() -> tuple[tuple[str, Path], ...]:
        saves_root = application_data_root()
        if not saves_root.exists():
            return ()
        worlds: list[tuple[str, Path]] = []
        for path in sorted(saves_root.iterdir()):
            if not path.is_dir():
                continue
            metadata = WorldStorage(path).load_metadata()
            if metadata is not None:
                worlds.append((metadata.name, path))
        return tuple(worlds)

    @staticmethod
    def _world_slug(name: str) -> str:
        slug = "-".join(
            "".join(character.lower() for character in part if character.isalnum())
            for part in name.split()
        )
        return slug or "world"
