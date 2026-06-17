# pyright: reportPrivateUsage=false

from __future__ import annotations

import logging
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
        win._stop_network_services()
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
            win._restore_player_position(saved.position)
        win.entities = EntitySimulation(seed=win.world_renderer.generator.seed.value)
        win._maintain_population((win.player.x, win.player.y, win.player.z))
        win.network_players.clear()
        win.remote_player_entities.clear()
        win.remote_player_interpolation.clear()
        win.requested_remote_chunks.clear()
        win.last_snapshot_sequence = 0
        win.structure_world = win.world_renderer.storage.load_structure_world()
        win.last_structure_revision = win.structure_world.revision
        win._start_local_authority()
        win.menu.screen = Screen.GAME
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
