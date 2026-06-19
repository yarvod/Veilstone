from __future__ import annotations

import logging
import queue
import time
from typing import TYPE_CHECKING, cast

from voxel_sandbox.domain.blocks.structures import StructureSnapshot, StructureWorld
from voxel_sandbox.engine.authority import LocalWorldAuthority, NetworkWorldAuthority
from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.ecs import AnimationState, RenderModel, Transform
from voxel_sandbox.network import ClientSession, LanServer, Message, decode_chunk_blocks
from voxel_sandbox.network.discovery import DiscoveryResponder
from voxel_sandbox.network.interpolation import SnapshotInterpolator
from voxel_sandbox.render.ui.menu import Screen

if TYPE_CHECKING:
    from voxel_sandbox.render.window import GameWindow

LOGGER = logging.getLogger(__name__)


class NetworkController:
    """Manages all network session logic, keeping GameWindow a thin coordinator."""

    def __init__(self, win: GameWindow) -> None:
        self.win = win

    def connect_remote(self, target: str, player_name: str) -> None:
        win = self.win
        host, separator, raw_port = target.rpartition(":")
        if not separator or not host:
            raise ValueError("Connect address must use HOST:PORT")
        session = ClientSession(auto_reconnect=True, reconnect_attempts=10, reconnect_delay=0.1)
        joined = session.connect(host, int(raw_port), name=player_name[:32] or "Player")
        self.stop_services()
        win.network_session = session
        win.structure_world = StructureWorld()
        win.authority = NetworkWorldAuthority(session, win.structure_world)
        win.world_renderer.enable_remote_mode()
        win.last_structure_revision = -1
        self.replace_structure_snapshots(
            joined.get("structures", []),
            joined.get("structure_revision", 0),
        )
        win.inventory_status = f"Connected as player {joined['player_id']}"
        win.authority.request_chunk(0, 0)
        win.requested_remote_chunks.add(ChunkCoord(0, 0))
        win.menu.screen = Screen.GAME
        win._sync_game_state()
        win._sync_mouse_capture()

    def process_messages(self) -> None:
        win = self.win
        assert win.network_session is not None
        for message in win.network_session.poll():
            self.apply_message(message)

    def apply_message(self, message: Message) -> None:
        win = self.win
        message_type = message.get("type")
        if message_type == "chunk":
            coord = message.get("coord")
            payload = message.get("blocks")
            if (
                isinstance(coord, list)
                and len(cast(list[object], coord)) == 2
                and all(isinstance(value, int) for value in cast(list[object], coord))
                and isinstance(payload, bytes)
            ):
                values = cast(list[int], coord)
                win.world_renderer.install_remote_chunk(
                    decode_chunk_blocks(ChunkCoord(values[0], values[1]), payload)
                )
                win.remote_chunks_received += 1
        elif message_type == "block_delta":
            position = message.get("position")
            block_id = message.get("block_id")
            if (
                isinstance(position, list)
                and len(cast(list[object], position)) == 3
                and all(isinstance(value, int) for value in cast(list[object], position))
                and isinstance(block_id, int)
            ):
                values = cast(list[int], position)
                win.world_renderer.set_block((values[0], values[1], values[2]), block_id)
        elif message_type == "entity_snapshot":
            players = message.get("players")
            sequence = message.get("sequence", 0)
            full = message.get("full", True)
            removed = message.get("removed", [])
            if (
                isinstance(players, dict)
                and isinstance(sequence, int)
                and sequence > win.last_snapshot_sequence
            ):
                win.last_snapshot_sequence = sequence
                normalized_players = self.normalize_players(players)
                if full is True:
                    win.network_players = normalized_players
                else:
                    win.network_players.update(normalized_players)
                    if isinstance(removed, list):
                        for player_id in cast(list[object], removed):
                            if isinstance(player_id, int):
                                win.network_players.pop(player_id, None)
                self.sync_remote_players(win.network_players)
        elif message_type == "structure_snapshot":
            self.replace_structure_snapshots(
                message.get("structures", []),
                message.get("revision", 0),
            )
        elif message_type == "chat":
            win.inventory_status = f"Chat: {message.get('text', '')}"
        elif message_type == "session_reconnecting":
            win.inventory_status = "Connection interrupted; reconnecting..."
        elif message_type == "session_reconnected":
            win.last_snapshot_sequence = 0
            win.network_players.clear()
            win.requested_remote_chunks.clear()
            joined = message.get("joined")
            if isinstance(joined, dict):
                win.last_structure_revision = -1
                self.replace_structure_snapshots(
                    joined.get("structures", []),
                    joined.get("structure_revision", 0),
                )
            win.inventory_status = "Reconnected to server"
            self.request_remote_chunk()
        elif message_type == "session_disconnected":
            assert win.network_session is not None
            win.network_session.close()
            win.network_session = None
            for entity in win.remote_player_entities.values():
                win.entities.world.destroy(entity)
            win.remote_player_entities.clear()
            win.remote_player_interpolation.clear()
            win.menu.screen = Screen.MULTIPLAYER
            win._sync_game_state()
            win.menu.status = "Disconnected: reconnect attempts exhausted."
            win._sync_mouse_capture()

    @staticmethod
    def normalize_players(raw_players: object) -> dict[int, dict[str, object]]:
        if not isinstance(raw_players, dict):
            return {}
        players: dict[int, dict[str, object]] = {}
        for raw_id, raw_player in cast(dict[object, object], raw_players).items():
            if isinstance(raw_id, int) and isinstance(raw_player, dict):
                players[raw_id] = {
                    str(key_name): value
                    for key_name, value in cast(dict[object, object], raw_player).items()
                }
        return players

    def sync_remote_players(self, players: dict[int, dict[str, object]]) -> None:
        win = self.win
        local_id = win.network_session.player_id if win.network_session is not None else None
        visible_ids: set[int] = set()
        for raw_id, raw_player in players.items():
            player = raw_player
            position = player.get("position")
            if not isinstance(position, list) or len(cast(list[object], position)) != 3:
                continue
            values = cast(list[object], position)
            if not all(isinstance(value, int | float) for value in values):
                continue
            coordinates = cast(list[int | float], values)
            position_tuple = (
                float(coordinates[0]),
                float(coordinates[1]),
                float(coordinates[2]),
            )
            if raw_id == local_id:
                continue
            entity = win.remote_player_entities.get(raw_id)
            if entity is None:
                entity = win.entities.world.create()
                win.remote_player_entities[raw_id] = entity
                win.remote_player_interpolation[raw_id] = SnapshotInterpolator()
                win.entities.world.render_models.set(
                    entity,
                    RenderModel("remote_player", (0.72, 0.58, 0.88), (0.65, 1.8, 0.65)),
                )
                win.entities.world.transforms.set(
                    entity,
                    Transform(float(coordinates[0]), float(coordinates[1]), float(coordinates[2])),
                )
                win.entities.world.animations.set(entity, AnimationState())
            animation = win.entities.world.animations.get(entity)
            transform = win.entities.world.transforms.get(entity)
            raw_yaw = player.get("yaw", 0.0)
            if transform is not None and isinstance(raw_yaw, int | float):
                transform.yaw = float(raw_yaw)
            if animation is not None:
                raw_phase = player.get("animation_phase", 0.0)
                animation.phase = float(raw_phase) if isinstance(raw_phase, int | float) else 0.0
                animation.speed = 1.8 if player.get("animation_state") == "walk" else 0.0
            win.remote_player_interpolation[raw_id].push(
                time.monotonic(),
                position_tuple,
            )
            visible_ids.add(raw_id)
        for player_id in set(win.remote_player_entities) - visible_ids:
            win.entities.world.destroy(win.remote_player_entities.pop(player_id))
            win.remote_player_interpolation.pop(player_id, None)

    def update_remote_players(self) -> None:
        win = self.win
        now = time.monotonic()
        for player_id, interpolation in win.remote_player_interpolation.items():
            position = interpolation.sample(now)
            entity = win.remote_player_entities.get(player_id)
            if position is None or entity is None:
                continue
            transform = win.entities.world.transforms.get(entity)
            if transform is not None:
                transform.x, transform.y, transform.z = position

    def send_block_action(self, block: tuple[int, int, int], block_id: int) -> None:
        win = self.win
        if win.authority is not None:
            try:
                win.authority.apply_block_action(block, block_id)
            except (ConnectionError, OSError):
                win.inventory_status = "Block action pending reconnect"
        elif win.lan_server is not None:
            win.lan_server.apply_block_action(block, block_id)

    def open_to_lan(self) -> None:
        win = self.win
        if win.lan_server is not None:
            win.menu.status = f"World already open to LAN on port {win.lan_server.address[1]}"
            return
        if win.network_session is not None:
            win.menu.status = "Cannot open a multiplayer game to LAN."
            return
        win.world_renderer.autosave()
        if win.world_renderer.storage is not None:
            win.world_renderer.storage.save_structure_world(win.structure_world)
        server = LanServer(
            "0.0.0.0",
            25565,
            seed=win.world_renderer.seed_text,
            storage=win.world_renderer.storage,
            block_action_sink=lambda position, block_id: win.lan_block_actions.put(
                (position, block_id)
            ),
        )
        server.start()
        win.lan_server = server
        session = ClientSession(auto_reconnect=True, reconnect_attempts=10, reconnect_delay=0.1)
        try:
            session.connect(
                "127.0.0.1",
                server.address[1],
                name=win.player_name,
                position=(win.player.x, win.player.y, win.player.z),
            )
        except OSError as error:
            server.stop()
            win.menu.status = f"Failed to connect to local server: {error}"
            win.lan_server = None
            return
        win.network_session = session
        win.authority = NetworkWorldAuthority(session, win.structure_world)
        try:
            discovery = DiscoveryResponder(
                "0.0.0.0",
                25565,
                world_name="Veilstone Singleplayer World",
                game_port=win.lan_server.address[1],
                player_count=lambda: win.lan_server.player_count if win.lan_server else 0,
            )
            discovery.start()
        except OSError as error:
            win.menu.status = f"Could not open LAN discovery port 25565: {error}"
            return
        win.lan_discovery = discovery
        win.menu.world_open_to_lan = True
        win.menu.status = f"Open to LAN on port {win.lan_server.address[1]}"

    def apply_lan_block_actions(self) -> None:
        win = self.win
        while True:
            try:
                block, block_id = win.lan_block_actions.get_nowait()
            except queue.Empty:
                return
            win.world_renderer.set_block(block, block_id)

    def start_local_authority(self) -> None:
        win = self.win
        win.structure_world = (
            win.world_renderer.storage.load_structure_world()
            if win.world_renderer.storage is not None
            else StructureWorld()
        )
        win.last_structure_revision = win.structure_world.revision
        win.authority = LocalWorldAuthority(
            win.structure_world,
            lambda position, block_id: win.lan_block_actions.put((position, block_id)),
        )

    def replace_structure_snapshots(self, raw_snapshots: object, raw_revision: object) -> None:
        win = self.win
        if not isinstance(raw_snapshots, list) or not isinstance(raw_revision, int):
            return
        if raw_revision < win.last_structure_revision:
            return
        if win.structure_world is None:
            return
        snapshots: list[StructureSnapshot] = []
        for raw in cast("list[object]", raw_snapshots):
            if not isinstance(raw, dict):
                return
            snapshots.append(cast("StructureSnapshot", raw))
        win.structure_world.replace_from_snapshots(snapshots)
        win.structure_world.revision = raw_revision
        win.last_structure_revision = raw_revision

    def stop_services(self) -> None:
        win = self.win
        if win.network_session is not None:
            win.network_session.close()
            win.network_session = None
        if win.lan_discovery is not None:
            win.lan_discovery.stop()
            win.lan_discovery = None
        if win.lan_server is not None:
            win.lan_server.stop()
            win.lan_server = None

    def toggle_structure(self, entity_id: int) -> None:
        win = self.win
        if win.world_renderer.remote_mode and win.authority is not None:
            try:
                win.authority.toggle_structure(entity_id)
                win.inventory_status = f"Requested structure #{entity_id} toggle."
            except (ConnectionError, OSError):
                win.inventory_status = "Structure interaction pending reconnect."
            return
        if win.lan_server is not None:
            entity = win.lan_server.toggle_structure(entity_id)
            win.inventory_status = (
                f"Structure #{entity.entity_id} {'activated' if entity.active else 'stopped'}."
            )
        elif win.authority is not None:
            entity = win.authority.toggle_structure(entity_id)
            if entity is not None:
                win.inventory_status = (
                    f"Structure #{entity.entity_id} {'activated' if entity.active else 'stopped'}."
                )

    def request_remote_chunk(self) -> None:
        win = self.win
        if win.network_session is None:
            return
        center = ChunkCoord(int(win.player.x) // 16, int(win.player.z) // 16)
        desired = [
            ChunkCoord(center.x + dx, center.z + dz) for dx in range(-2, 3) for dz in range(-2, 3)
        ]
        for coord in sorted(
            desired,
            key=lambda item: (item.x - center.x) ** 2 + (item.z - center.z) ** 2,
        ):
            if coord in win.requested_remote_chunks:
                continue
            if win.authority is not None:
                win.authority.request_chunk(coord.x, coord.z)
            return
