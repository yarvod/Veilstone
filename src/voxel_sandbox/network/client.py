from __future__ import annotations

import socket
from contextlib import suppress

from voxel_sandbox.network.protocol import PROTOCOL_VERSION, Message, receive_frame, send_frame


class LanClient:
    def __init__(self) -> None:
        self.connection: socket.socket | None = None
        self.player_id: int | None = None

    def connect(
        self,
        host: str,
        port: int,
        *,
        name: str,
        position: tuple[float, float, float] | None = None,
    ) -> Message:
        self.connection = socket.create_connection((host, port), timeout=2.0)
        send_frame(
            self.connection,
            {"type": "handshake", "version": PROTOCOL_VERSION, "name": name},
        )
        response = receive_frame(self.connection)
        if response.get("type") != "handshake_ok":
            raise ConnectionError(f"Handshake failed: {response}")
        join: Message = {"type": "join"}
        if position is not None:
            join["position"] = list(position)
        send_frame(self.connection, join)
        joined = receive_frame(self.connection)
        player_id = joined.get("player_id")
        if not isinstance(player_id, int):
            raise ConnectionError(f"Join failed: {joined}")
        self.player_id = player_id
        return joined

    def send(self, message: Message) -> None:
        if self.connection is None:
            raise ConnectionError("Client is not connected")
        send_frame(self.connection, message)

    def receive(self) -> Message:
        if self.connection is None:
            raise ConnectionError("Client is not connected")
        return receive_frame(self.connection)

    def close(self) -> None:
        connection = self.connection
        self.connection = None
        if connection is not None:
            with suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
            connection.close()
