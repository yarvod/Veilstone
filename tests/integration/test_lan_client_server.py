from __future__ import annotations

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.network import LanClient, LanServer, Message, decode_chunk_blocks


def receive_type(client: LanClient, expected: str) -> Message:
    for _ in range(8):
        message = client.receive()
        if message.get("type") == expected:
            return message
    raise AssertionError(f"Did not receive {expected}")


def test_two_clients_join_and_receive_entities_blocks_and_chat() -> None:
    server = LanServer("127.0.0.1", 0, seed="network-test")
    server.start()
    first = LanClient()
    second = LanClient()
    try:
        first_join = first.connect(*server.address, name="First")
        second_join = second.connect(*server.address, name="Second")
        assert first_join["seed"] == "network-test"
        assert first_join["player_id"] != second_join["player_id"]

        snapshot = receive_type(first, "entity_snapshot")
        while len(snapshot["players"]) < 2:  # type: ignore[arg-type]
            snapshot = receive_type(first, "entity_snapshot")
        assert snapshot["full"] is True
        assert len(snapshot["players"]) == 2  # type: ignore[arg-type]

        first.send({"type": "input", "position": [3.0, 40.0, 5.0]})
        for _ in range(4):
            moved = receive_type(second, "entity_snapshot")
            if any(
                player["position"] == [3.0, 40.0, 5.0]
                for player in moved["players"].values()  # type: ignore[union-attr]
            ):
                break
        else:
            raise AssertionError("Moved player snapshot was not received")
        assert moved["full"] is False
        assert isinstance(moved["sequence"], int)

        second.send({"type": "request_chunk", "coord": [0, 0]})
        chunk = receive_type(second, "chunk")
        assert chunk["coord"] == [0, 0]
        decoded = decode_chunk_blocks(ChunkCoord(0, 0), chunk["blocks"])  # type: ignore[arg-type]
        assert decoded.get_block(8, 1, 8) != 0

        first.send({"type": "block_action", "position": [1, 20, 3], "block_id": 10})
        delta = receive_type(second, "block_delta")
        assert delta["position"] == [1, 20, 3]
        assert delta["block_id"] == 10

        second.send({"type": "chat", "text": "hello LAN"})
        chat = receive_type(first, "chat")
        assert chat["text"] == "hello LAN"
    finally:
        first.close()
        second.close()
        server.stop()
