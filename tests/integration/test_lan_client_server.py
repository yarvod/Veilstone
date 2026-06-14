from __future__ import annotations

from pathlib import Path

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.infrastructure.storage import WorldStorage
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
        assert all(
            "animation_state" in player and "animation_phase" in player
            for player in snapshot["players"].values()  # type: ignore[union-attr]
        )

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

        first.send({"type": "block_action", "position": [2, 40, 4], "block_id": 10})
        delta = receive_type(second, "block_delta")
        assert delta["position"] == [2, 40, 4]
        assert delta["block_id"] == 10

        second.send({"type": "chat", "text": "hello LAN"})
        chat = receive_type(first, "chat")
        assert chat["text"] == "hello LAN"
    finally:
        first.close()
        second.close()
        server.stop()


def test_server_reads_and_persists_the_configured_world(tmp_path: Path) -> None:
    storage = WorldStorage(tmp_path)
    storage.ensure_world(name="Shared World", seed="network-storage")
    server = LanServer("127.0.0.1", 0, seed="network-storage", storage=storage)
    server.start()
    client = LanClient()
    try:
        client.connect(*server.address, name="Builder")
        client.send({"type": "input", "position": [8.5, 40.0, 8.5]})
        receive_type(client, "entity_snapshot")
        client.send({"type": "block_action", "position": [8, 40, 8], "block_id": 10})
        receive_type(client, "block_delta")
    finally:
        client.close()
        server.stop()

    saved = storage.load_chunk(ChunkCoord(0, 0))
    assert saved is not None
    assert saved.get_block(8, 40, 8) == 10


def test_join_accepts_initial_position_and_runtime_rename() -> None:
    server = LanServer("127.0.0.1", 0, seed="join-state")
    server.start()
    client = LanClient()
    try:
        joined = client.connect(
            *server.address,
            name="Before",
            position=(8.5, 33.0, 8.5),
        )
        player_id = joined["player_id"]
        snapshot = receive_type(client, "entity_snapshot")
        assert snapshot["players"][player_id]["position"] == [8.5, 33.0, 8.5]  # type: ignore[index]

        client.send({"type": "rename", "name": "After"})
        renamed = receive_type(client, "entity_snapshot")
        assert renamed["players"][player_id]["name"] == "After"  # type: ignore[index]
    finally:
        client.close()
        server.stop()
