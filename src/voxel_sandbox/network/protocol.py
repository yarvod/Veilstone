# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from __future__ import annotations

import socket
import struct
from typing import cast

import msgpack

PROTOCOL_VERSION = 1
MAX_FRAME_SIZE = 4 * 1024 * 1024
FRAME_LENGTH = struct.Struct("!I")
type Message = dict[str, object]


def encode_frame(message: Message) -> bytes:
    payload = cast(bytes, msgpack.packb(message, use_bin_type=True))
    if len(payload) > MAX_FRAME_SIZE:
        raise ValueError("Network frame exceeds maximum size")
    return FRAME_LENGTH.pack(len(payload)) + payload


def receive_frame(connection: socket.socket) -> Message:
    header = _receive_exact(connection, FRAME_LENGTH.size)
    (length,) = FRAME_LENGTH.unpack(header)
    if length > MAX_FRAME_SIZE:
        raise ValueError("Network frame exceeds maximum size")
    payload = _receive_exact(connection, length)
    decoded = cast(object, msgpack.unpackb(payload, raw=False, strict_map_key=False))
    if not isinstance(decoded, dict):
        raise ValueError("Network frame payload must be a map")
    return cast(Message, decoded)


def send_frame(connection: socket.socket, message: Message) -> None:
    connection.sendall(encode_frame(message))


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            raise EOFError("Connection closed while receiving frame")
        chunks.extend(chunk)
    return bytes(chunks)
