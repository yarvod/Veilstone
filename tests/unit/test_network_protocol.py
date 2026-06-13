from __future__ import annotations

import socket

from voxel_sandbox.network.protocol import Message, encode_frame, receive_frame


def test_msgpack_frame_roundtrip_over_socket() -> None:
    sender, receiver = socket.socketpair()
    message: Message = {"type": "chunk", "coord": [-2, 3], "blocks": b"compressed"}
    try:
        sender.sendall(encode_frame(message))
        assert receive_frame(receiver) == message
    finally:
        sender.close()
        receiver.close()
