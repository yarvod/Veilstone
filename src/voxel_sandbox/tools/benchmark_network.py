from __future__ import annotations

import socket
from time import perf_counter

from voxel_sandbox.network.protocol import Message, encode_frame, receive_frame


def run_benchmark(iterations: int = 1000) -> int:
    sender, receiver = socket.socketpair()
    message: Message = {
        "type": "entity_snapshot",
        "players": {1: {"position": [1.0, 2.0, 3.0]}},
    }
    frame = encode_frame(message)
    start = perf_counter()
    try:
        for _ in range(iterations):
            sender.sendall(frame)
            receive_frame(receiver)
    finally:
        sender.close()
        receiver.close()
    elapsed = (perf_counter() - start) * 1000.0
    print(f"network {iterations} frames: total={elapsed:.2f} ms avg={elapsed / iterations:.3f} ms")
    return 0
