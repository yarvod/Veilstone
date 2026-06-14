from __future__ import annotations

import socket
import socketserver
import threading
from dataclasses import dataclass, field
from typing import cast

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import TerrainGenerator, WorldSeed
from voxel_sandbox.network.chunks import encode_chunk_blocks
from voxel_sandbox.network.protocol import PROTOCOL_VERSION, Message, receive_frame, send_frame
from voxel_sandbox.network.rate_limit import TokenBucket


@dataclass(slots=True)
class ServerState:
    seed: str
    generator: TerrainGenerator = field(init=False)
    next_player_id: int = 1
    clients: dict[int, socket.socket] = field(default_factory=lambda: {})
    players: dict[int, dict[str, object]] = field(default_factory=lambda: {})
    blocks: dict[tuple[int, int, int], int] = field(default_factory=lambda: {})
    rate_limits: dict[int, TokenBucket] = field(default_factory=lambda: {})
    snapshot_sequences: dict[int, int] = field(default_factory=lambda: {})
    snapshot_baselines: dict[int, dict[int, dict[str, object]]] = field(default_factory=lambda: {})
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.generator = TerrainGenerator(WorldSeed.parse(self.seed))

    def broadcast(self, message: Message) -> None:
        with self.lock:
            clients = tuple(self.clients.values())
        for connection in clients:
            try:
                send_frame(connection, message)
            except OSError:
                continue

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
            with state.lock:
                player_id = state.next_player_id
                state.next_player_id += 1
                state.clients[player_id] = connection
                state.players[player_id] = {"name": name, "position": [0.5, 40.0, 0.5]}
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
            if isinstance(position, list) and len(cast(list[object], position)) == 3:
                with state.lock:
                    state.players[player_id]["position"] = position
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
                with state.lock:
                    state.blocks[key] = block_id
                state.broadcast(
                    {"type": "block_delta", "position": list(key), "block_id": block_id}
                )
        elif message_type == "chat":
            text = str(message.get("text", ""))[:256]
            if text:
                state.broadcast({"type": "chat", "player_id": player_id, "text": text})
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
                chunk = state.generator.generate_chunk(chunk_coord)
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
    def __init__(self, host: str, port: int, *, seed: str) -> None:
        self._server = _ThreadingServer((host, port), _Handler)
        self._server.state = ServerState(seed)
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

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


def _distance_squared(first: list[float], second: list[float]) -> float:
    return sum((first[index] - second[index]) ** 2 for index in range(3))
