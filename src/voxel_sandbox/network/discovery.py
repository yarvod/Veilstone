from __future__ import annotations

import json
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

DISCOVERY_QUERY = b"VEILSTONE_DISCOVER_V1"


@dataclass(frozen=True, slots=True)
class DiscoveredWorld:
    name: str
    host: str
    port: int
    players: int


class DiscoveryResponder:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        world_name: str,
        game_port: int,
        player_count: Callable[[], int],
    ) -> None:
        self.world_name = world_name
        self.game_port = game_port
        self.player_count = player_count
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.settimeout(0.2)
        self._closed = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.socket.getsockname()
        return str(host), int(port)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._closed.set()
        self.socket.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._closed.is_set():
            try:
                payload, address = self.socket.recvfrom(1024)
            except TimeoutError:
                continue
            except OSError:
                return
            if payload != DISCOVERY_QUERY:
                continue
            response = json.dumps(
                {
                    "name": self.world_name,
                    "port": self.game_port,
                    "players": self.player_count(),
                },
                separators=(",", ":"),
            ).encode("utf-8")
            self.socket.sendto(response, address)


def discover_worlds(
    *,
    port: int = 25565,
    timeout: float = 0.3,
    target: str = "255.255.255.255",
) -> tuple[DiscoveredWorld, ...]:
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    connection.settimeout(timeout)
    discovered: dict[tuple[str, int], DiscoveredWorld] = {}
    try:
        connection.sendto(DISCOVERY_QUERY, (target, port))
        while True:
            try:
                payload, address = connection.recvfrom(2048)
            except TimeoutError:
                break
            decoded = json.loads(payload.decode("utf-8"))
            if not isinstance(decoded, dict):
                continue
            values = cast(dict[str, object], decoded)
            name = values.get("name")
            game_port = values.get("port")
            players = values.get("players")
            if (
                not isinstance(name, str)
                or not isinstance(game_port, int)
                or not isinstance(players, int)
            ):
                continue
            world = DiscoveredWorld(
                name,
                str(address[0]),
                game_port,
                players,
            )
            discovered[(world.host, world.port)] = world
    finally:
        connection.close()
    return tuple(discovered.values())
