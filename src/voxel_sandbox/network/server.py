from __future__ import annotations

import math
import socket
import socketserver
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

from voxel_sandbox.domain.blocks import BlockRegistry, create_core_block_registry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, Chunk, ChunkCoord, split_world_axis
from voxel_sandbox.engine.generation import TerrainGenerator, WorldSeed
from voxel_sandbox.infrastructure.storage import WorldStorage
from voxel_sandbox.network.chunks import encode_chunk_blocks
from voxel_sandbox.network.protocol import PROTOCOL_VERSION, Message, receive_frame, send_frame
from voxel_sandbox.network.rate_limit import TokenBucket


@dataclass(slots=True)
class ServerState:
    seed: str
    storage: WorldStorage | None = None
    block_action_sink: Callable[[tuple[int, int, int], int], None] | None = None
    generator: TerrainGenerator = field(init=False)
    block_registry: BlockRegistry = field(init=False)
    next_player_id: int = 1
    clients: dict[int, socket.socket] = field(default_factory=lambda: {})
    players: dict[int, dict[str, object]] = field(default_factory=lambda: {})
    blocks: dict[tuple[int, int, int], int] = field(default_factory=lambda: {})
    rate_limits: dict[int, TokenBucket] = field(default_factory=lambda: {})
    snapshot_sequences: dict[int, int] = field(default_factory=lambda: {})
    snapshot_baselines: dict[int, dict[int, dict[str, object]]] = field(default_factory=lambda: {})
    chunks: dict[ChunkCoord, Chunk] = field(default_factory=lambda: {})
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.generator = TerrainGenerator(WorldSeed.parse(self.seed))
        self.block_registry = create_core_block_registry()

    def allows_player_block_action(
        self,
        position: tuple[int, int, int],
        block_id: int,
    ) -> bool:
        try:
            self.block_registry.by_id(block_id)
        except KeyError:
            return False
        if block_id != 0:
            return True
        world_x, y, world_z = position
        if not 0 <= y < CHUNK_HEIGHT:
            return False
        chunk_x, local_x = split_world_axis(world_x)
        chunk_z, local_z = split_world_axis(world_z)
        current = self.chunk_at(ChunkCoord(chunk_x, chunk_z)).get_block(local_x, y, local_z)
        return not self.block_registry.by_id(current).is_fluid

    def broadcast(self, message: Message) -> None:
        with self.lock:
            clients = tuple(self.clients.values())
        for connection in clients:
            try:
                send_frame(connection, message)
            except OSError:
                continue

    def apply_block_action(
        self,
        position: tuple[int, int, int],
        block_id: int,
        *,
        notify_sink: bool,
    ) -> None:
        with self.lock:
            self.blocks[position] = block_id
            world_x, y, world_z = position
            chunk_x, local_x = split_world_axis(world_x)
            chunk_z, local_z = split_world_axis(world_z)
            chunk = self.chunks.get(ChunkCoord(chunk_x, chunk_z))
            if chunk is not None and 0 <= y < CHUNK_HEIGHT:
                chunk.set_block(local_x, y, local_z, block_id)
        if notify_sink and self.block_action_sink is not None:
            self.block_action_sink(position, block_id)
        self.broadcast({"type": "block_delta", "position": list(position), "block_id": block_id})

    def chunk_at(self, coord: ChunkCoord) -> Chunk:
        with self.lock:
            cached = self.chunks.get(coord)
        if cached is not None:
            return cached
        chunk = self.storage.load_chunk(coord) if self.storage is not None else None
        if chunk is None:
            chunk = self.generator.generate_chunk(coord)
        with self.lock:
            overrides = tuple(self.blocks.items())
        for (world_x, y, world_z), block_id in overrides:
            chunk_x, local_x = split_world_axis(world_x)
            chunk_z, local_z = split_world_axis(world_z)
            if (chunk_x, chunk_z) == (coord.x, coord.z) and 0 <= y < CHUNK_HEIGHT:
                chunk.set_block(local_x, y, local_z, block_id)
        with self.lock:
            self.chunks[coord] = chunk
        return chunk

    def save(self) -> None:
        if self.storage is None:
            return
        with self.lock:
            changed_coords = {
                ChunkCoord(split_world_axis(x)[0], split_world_axis(z)[0])
                for x, _y, z in self.blocks
            }
        for coord in changed_coords:
            self.storage.save_chunk(self.chunk_at(coord))

    def send_entity_snapshots(self, *, force_full: bool = False) -> None:
        with self.lock:
            clients = tuple(self.clients.items())
            players = dict(self.players)
        for player_id, connection in clients:
            own = players.get(player_id)
            if own is None:
                continue
            own_position = cast(list[float], own["position"])
            visible = {
                other_id: {
                    "name": player["name"],
                    "position": list(cast(list[float], player["position"])),
                    "animation_state": player.get("animation_state", "idle"),
                    "animation_phase": player.get("animation_phase", 0.0),
                }
                for other_id, player in players.items()
                if _distance_squared(
                    own_position,
                    cast(list[float], player["position"]),
                )
                <= 64.0**2
            }
            sequence = self.snapshot_sequences.get(player_id, 0) + 1
            self.snapshot_sequences[player_id] = sequence
            baseline = self.snapshot_baselines.get(player_id, {})
            full = force_full or not baseline or sequence % 20 == 0
            changed = (
                visible
                if full
                else {
                    entity_id: player
                    for entity_id, player in visible.items()
                    if baseline.get(entity_id) != player
                }
            )
            removed = (
                [] if full else [entity_id for entity_id in baseline if entity_id not in visible]
            )
            self.snapshot_baselines[player_id] = visible
            try:
                send_frame(
                    connection,
                    {
                        "type": "entity_snapshot",
                        "sequence": sequence,
                        "full": full,
                        "players": changed,
                        "removed": removed,
                    },
                )
            except OSError:
                continue


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        connection = self.request
        assert isinstance(connection, socket.socket)
        player_id: int | None = None
        try:
            handshake = receive_frame(connection)
            if handshake.get("type") != "handshake" or handshake.get("version") != PROTOCOL_VERSION:
                send_frame(connection, {"type": "error", "reason": "protocol_mismatch"})
                return
            name = str(handshake.get("name", "Player"))[:32]
            send_frame(connection, {"type": "handshake_ok", "version": PROTOCOL_VERSION})
            join = receive_frame(connection)
            if join.get("type") != "join":
                send_frame(connection, {"type": "error", "reason": "join_required"})
                return
            server = cast(_ThreadingServer, self.server)
            state = server.state
            joined_position = _validated_position(join.get("position")) or (0.5, 40.0, 0.5)
            with state.lock:
                player_id = state.next_player_id
                state.next_player_id += 1
                state.clients[player_id] = connection
                state.players[player_id] = {
                    "name": name,
                    "position": list(joined_position),
                    "animation_state": "idle",
                    "animation_phase": 0.0,
                }
                state.rate_limits[player_id] = TokenBucket(rate=40.0, capacity=80.0)
                state.snapshot_sequences[player_id] = 0
                players = dict(state.players)
            send_frame(
                connection,
                {
                    "type": "join_ok",
                    "player_id": player_id,
                    "seed": state.seed,
                    "players": players,
                },
            )
            state.send_entity_snapshots(force_full=True)
            while True:
                message = receive_frame(connection)
                self._handle_message(player_id, message)
        except (EOFError, ConnectionError, OSError):
            pass
        finally:
            if player_id is not None:
                server = cast(_ThreadingServer, self.server)
                state = server.state
                with state.lock:
                    state.clients.pop(player_id, None)
                    state.players.pop(player_id, None)
                    state.rate_limits.pop(player_id, None)
                    state.snapshot_sequences.pop(player_id, None)
                    state.snapshot_baselines.pop(player_id, None)
                state.send_entity_snapshots(force_full=True)

    def _handle_message(self, player_id: int, message: Message) -> None:
        server = cast(_ThreadingServer, self.server)
        state = server.state
        limiter = state.rate_limits.get(player_id)
        if limiter is not None and not limiter.allow():
            return
        message_type = message.get("type")
        if message_type == "input":
            position = message.get("position")
            validated = _validated_position(position)
            if validated is not None:
                with state.lock:
                    player = state.players[player_id]
                    previous = cast(list[float], player["position"])
                    distance = math.dist(previous, validated)
                    player["position"] = list(validated)
                    player["animation_state"] = "walk" if distance > 0.002 else "idle"
                    raw_phase = player.get("animation_phase", 0.0)
                    previous_phase = float(raw_phase) if isinstance(raw_phase, int | float) else 0.0
                    player["animation_phase"] = (
                        previous_phase + distance * 3.5 + time.monotonic() * 0.0001
                    ) % math.tau
                state.send_entity_snapshots()
        elif message_type == "block_action":
            position = message.get("position")
            block_id = message.get("block_id")
            if (
                isinstance(position, list)
                and len(cast(list[object], position)) == 3
                and isinstance(block_id, int)
            ):
                values = cast(list[object], position)
                if not all(isinstance(value, int) for value in values):
                    return
                coordinates = cast(list[int], values)
                key = coordinates[0], coordinates[1], coordinates[2]
                player = state.players.get(player_id)
                if player is None or not _block_action_in_range(
                    cast(list[float], player["position"]), key
                ):
                    return
                if not state.allows_player_block_action(key, block_id):
                    return
                state.apply_block_action(key, block_id, notify_sink=True)
        elif message_type == "chat":
            text = str(message.get("text", ""))[:256]
            if text:
                state.broadcast({"type": "chat", "player_id": player_id, "text": text})
        elif message_type == "rename":
            name = str(message.get("name", ""))[:32].strip()
            if name:
                with state.lock:
                    state.players[player_id]["name"] = name
                state.send_entity_snapshots(force_full=True)
        elif message_type == "request_chunk":
            coord = message.get("coord", [0, 0])
            connection = state.clients.get(player_id)
            if (
                connection is not None
                and isinstance(coord, list)
                and len(cast(list[object], coord)) == 2
            ):
                raw_coord = cast(list[object], coord)
                if not all(isinstance(value, int) for value in raw_coord):
                    return
                chunk_coord = ChunkCoord(*cast(list[int], raw_coord))
                player = state.players.get(player_id)
                if player is None:
                    return
                player_position = cast(list[float], player["position"])
                player_chunk = ChunkCoord(
                    int(player_position[0]) // 16, int(player_position[2]) // 16
                )
                if (
                    max(
                        abs(chunk_coord.x - player_chunk.x),
                        abs(chunk_coord.z - player_chunk.z),
                    )
                    > 4
                ):
                    return
                chunk = state.chunk_at(chunk_coord)
                send_frame(
                    connection,
                    {
                        "type": "chunk",
                        "coord": [chunk_coord.x, chunk_coord.z],
                        "blocks": encode_chunk_blocks(chunk),
                    },
                )


class _ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    state: ServerState


class LanServer:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        seed: str,
        storage: WorldStorage | None = None,
        block_action_sink: Callable[[tuple[int, int, int], int], None] | None = None,
    ) -> None:
        self._server = _ThreadingServer((host, port), _Handler)
        self._server.state = ServerState(seed, storage, block_action_sink)
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        address = self._server.server_address
        host, port = address[0], address[1]
        return str(host), int(port)

    @property
    def player_count(self) -> int:
        with self._server.state.lock:
            return len(self._server.state.players)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def apply_block_action(self, position: tuple[int, int, int], block_id: int) -> None:
        self._server.state.apply_block_action(position, block_id, notify_sink=False)

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._server.state.save()


def _distance_squared(first: list[float], second: list[float]) -> float:
    return sum((first[index] - second[index]) ** 2 for index in range(3))


def _validated_position(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(cast(list[object], value)) != 3:
        return None
    raw = cast(list[object], value)
    if not all(isinstance(coordinate, int | float) for coordinate in raw):
        return None
    x, y, z = (float(cast(int | float, coordinate)) for coordinate in raw)
    if not all(math.isfinite(coordinate) for coordinate in (x, y, z)):
        return None
    if abs(x) > 30_000_000.0 or abs(z) > 30_000_000.0 or not 0.0 <= y <= CHUNK_HEIGHT:
        return None
    return x, y, z


def _block_action_in_range(
    player_position: list[float], block_position: tuple[int, int, int]
) -> bool:
    block_center = [float(coordinate) + 0.5 for coordinate in block_position]
    return _distance_squared(player_position, block_center) <= 8.0**2
