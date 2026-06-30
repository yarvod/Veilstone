"""Tests for NetworkController — extracted network session manager."""

from __future__ import annotations

import math
import queue
from typing import Any, cast
from unittest.mock import MagicMock, patch

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.ecs import EntityWorld
from voxel_sandbox.network.interpolation import SnapshotInterpolator
from voxel_sandbox.render.network_controller import NetworkController
from voxel_sandbox.render.ui.menu import Screen


def _make_win() -> MagicMock:
    win = MagicMock()
    win.network_session = None
    win.lan_server = None
    win.lan_discovery = None
    win.authority = None
    win.structure_world = MagicMock()
    win.last_structure_revision = 0
    win.remote_player_entities = {}
    win.remote_player_interpolation = {}
    win.requested_remote_chunks = set()
    win.network_players = {}
    win.last_snapshot_sequence = 0
    win.lan_block_actions = queue.SimpleQueue()
    win.remote_chunks_received = 0
    win.inventory_status = ""
    win.player.x = 0.0
    win.player.y = 64.0
    win.player.z = 0.0

    def remote_entity_world() -> Any | None:
        entities = win.entities
        if entities is None:
            return None
        return entities.world

    def remember_remote_player_entity(player_id: int, entity: Any) -> None:
        win.remote_player_entities[player_id] = entity
        win.remote_player_interpolation[player_id] = SnapshotInterpolator()

    def push_remote_player_position(
        player_id: int,
        timestamp: float,
        position: tuple[float, float, float],
    ) -> None:
        win.remote_player_interpolation[player_id].push(timestamp, position)

    def pop_remote_player_entity(player_id: int) -> Any | None:
        entity = win.remote_player_entities.pop(player_id, None)
        win.remote_player_interpolation.pop(player_id, None)
        return entity

    def clear_remote_players() -> None:
        entity_world = remote_entity_world()
        if entity_world is not None:
            for entity in win.remote_player_entities.values():
                entity_world.destroy(entity)
        win.remote_player_entities.clear()
        win.remote_player_interpolation.clear()

    def update_remote_player_positions(timestamp: float, *, delay: float) -> None:
        entity_world = remote_entity_world()
        if entity_world is None:
            return
        for player_id, interpolation in win.remote_player_interpolation.items():
            position = interpolation.sample(timestamp - delay)
            entity = win.remote_player_entities.get(player_id)
            if position is None or entity is None:
                continue
            transform = entity_world.transforms.get(entity)
            if transform is not None:
                transform.x, transform.y, transform.z = position

    def local_network_player_id() -> int | None:
        return win.network_session.player_id if win.network_session is not None else None

    def remote_player_entity(player_id: int) -> Any | None:
        return win.remote_player_entities.get(player_id)

    def remote_player_ids() -> set[int]:
        return set(win.remote_player_entities)

    def request_remote_chunk_from_server(coord: ChunkCoord) -> bool:
        if coord in win.requested_remote_chunks:
            return False
        if win.authority is None:
            return False
        win.authority.request_chunk(coord.x, coord.z)
        win.requested_remote_chunks.add(coord)
        return True

    def clear_remote_chunk_requests() -> None:
        win.requested_remote_chunks.clear()

    win.remote_entity_world.side_effect = remote_entity_world
    win.local_network_player_id.side_effect = local_network_player_id
    win.remote_player_entity.side_effect = remote_player_entity
    win.remember_remote_player_entity.side_effect = remember_remote_player_entity
    win.push_remote_player_position.side_effect = push_remote_player_position
    win.remote_player_ids.side_effect = remote_player_ids
    win.pop_remote_player_entity.side_effect = pop_remote_player_entity
    win.clear_remote_players.side_effect = clear_remote_players
    win.update_remote_player_positions.side_effect = update_remote_player_positions
    win.request_remote_chunk_from_server.side_effect = request_remote_chunk_from_server
    win.clear_remote_chunk_requests.side_effect = clear_remote_chunk_requests
    return win


class TestNormalizePlayers:
    def test_returns_empty_for_non_dict(self):
        assert NetworkController.normalize_players(None) == {}
        assert NetworkController.normalize_players([]) == {}
        assert NetworkController.normalize_players("bad") == {}

    def test_filters_non_int_keys(self):
        raw = {"not_int": {"x": 1.0}}
        assert NetworkController.normalize_players(raw) == {}

    def test_filters_non_dict_values(self):
        raw = {1: "not_a_dict"}
        assert NetworkController.normalize_players(raw) == {}

    def test_converts_valid_players(self):
        raw = {1: {"x": 10.0, "y": 64.0}, 2: {"x": -5.0}}
        result = NetworkController.normalize_players(raw)
        assert set(result.keys()) == {1, 2}
        assert result[1]["x"] == 10.0

    def test_stringifies_nested_keys(self):
        raw = {42: {99: "value"}}
        result = NetworkController.normalize_players(raw)
        assert "99" in result[42]


class TestStopServices:
    def test_closes_network_session(self):
        win = _make_win()
        session = MagicMock()
        win.network_session = session
        nc = NetworkController(win)
        nc.stop_services()
        session.close.assert_called_once()
        assert win.network_session is None

    def test_stops_lan_discovery(self):
        win = _make_win()
        discovery = MagicMock()
        win.lan_discovery = discovery
        nc = NetworkController(win)
        nc.stop_services()
        discovery.stop.assert_called_once()
        assert win.lan_discovery is None

    def test_stops_lan_server(self):
        win = _make_win()
        server = MagicMock()
        win.lan_server = server
        nc = NetworkController(win)
        nc.stop_services()
        server.stop.assert_called_once()
        assert win.lan_server is None

    def test_noop_when_nothing_running(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.stop_services()  # should not raise


class TestSendBlockAction:
    def test_delegates_to_authority_when_present(self):
        win = _make_win()
        win.authority = MagicMock()
        nc = NetworkController(win)
        nc.send_block_action((1, 2, 3), 5)
        win.authority.apply_block_action.assert_called_once_with((1, 2, 3), 5)

    def test_delegates_to_lan_server_when_no_authority(self):
        win = _make_win()
        win.lan_server = MagicMock()
        nc = NetworkController(win)
        nc.send_block_action((1, 2, 3), 5)
        win.lan_server.apply_block_action.assert_called_once_with((1, 2, 3), 5)

    def test_connection_error_sets_status(self):
        win = _make_win()
        win.authority = MagicMock()
        win.authority.apply_block_action.side_effect = ConnectionError("lost")
        nc = NetworkController(win)
        nc.send_block_action((0, 0, 0), 1)
        assert "pending" in win.inventory_status.lower()

    def test_os_error_sets_status(self):
        win = _make_win()
        win.authority = MagicMock()
        win.authority.apply_block_action.side_effect = OSError("broken pipe")
        nc = NetworkController(win)
        nc.send_block_action((0, 0, 0), 1)
        assert "pending" in win.inventory_status.lower()

    def test_noop_when_no_authority_and_no_lan(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.send_block_action((0, 0, 0), 1)  # should not raise


class TestLocalAuthority:
    def test_loads_structure_world_from_runtime_storage(self):
        win = _make_win()
        storage = MagicMock()
        structure_world = MagicMock()
        structure_world.revision = 7
        storage.load_structure_world.return_value = structure_world
        win.world_runtime.storage = storage

        nc = NetworkController(win)
        nc.start_local_authority()

        storage.load_structure_world.assert_called_once_with()
        assert win.structure_world is structure_world
        assert win.last_structure_revision == 7


class TestApplyLanBlockActions:
    def test_drains_queue_and_sets_blocks(self):
        win = _make_win()
        win.lan_block_actions.put(((1, 2, 3), 5))
        win.lan_block_actions.put(((4, 5, 6), 7))
        nc = NetworkController(win)
        nc.apply_lan_block_actions()
        assert win.world_renderer.set_block.call_count == 2
        win.world_renderer.set_block.assert_any_call((1, 2, 3), 5)
        win.world_renderer.set_block.assert_any_call((4, 5, 6), 7)

    def test_empty_queue_is_noop(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.apply_lan_block_actions()
        win.world_renderer.set_block.assert_not_called()


class TestReplaceStructureSnapshots:
    def test_ignores_non_list_snapshots(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.replace_structure_snapshots("bad", 5)
        win.structure_world.replace_from_snapshots.assert_not_called()

    def test_ignores_non_int_revision(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.replace_structure_snapshots([], "bad")
        win.structure_world.replace_from_snapshots.assert_not_called()

    def test_ignores_older_revision(self):
        win = _make_win()
        win.last_structure_revision = 10
        nc = NetworkController(win)
        nc.replace_structure_snapshots([], 5)
        win.structure_world.replace_from_snapshots.assert_not_called()

    def test_applies_valid_snapshots(self):
        win = _make_win()
        win.last_structure_revision = 0
        nc = NetworkController(win)
        snapshots: list[dict[str, object]] = [
            {"id": "test", "blocks": cast(dict[object, object], {})}
        ]
        nc.replace_structure_snapshots(snapshots, 1)
        win.structure_world.replace_from_snapshots.assert_called_once()
        assert win.last_structure_revision == 1

    def test_same_revision_is_applied(self):
        win = _make_win()
        win.last_structure_revision = 5
        nc = NetworkController(win)
        nc.replace_structure_snapshots([{"id": "x"}], 5)
        win.structure_world.replace_from_snapshots.assert_called_once()

    def test_non_dict_entry_aborts(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.replace_structure_snapshots(["not_a_dict"], 1)
        win.structure_world.replace_from_snapshots.assert_not_called()


class TestRequestRemoteChunk:
    def test_noop_when_no_session(self):
        win = _make_win()
        win.network_session = None
        win.authority = MagicMock()
        nc = NetworkController(win)
        nc.request_remote_chunk()
        win.authority.request_chunk.assert_not_called()

    def test_skips_already_requested_chunks(self):
        win = _make_win()
        win.network_session = MagicMock()
        win.authority = MagicMock()
        # All nearby chunks already requested
        win.requested_remote_chunks = {ChunkCoord(x, z) for x in range(-2, 3) for z in range(-2, 3)}
        nc = NetworkController(win)
        nc.request_remote_chunk()
        win.authority.request_chunk.assert_not_called()

    def test_requests_nearest_unrequested_chunk(self):
        win = _make_win()
        win.network_session = MagicMock()
        win.authority = MagicMock()
        win.player.x = 0.0
        win.player.z = 0.0
        nc = NetworkController(win)
        nc.request_remote_chunk()
        # Should request (0,0) as nearest
        win.authority.request_chunk.assert_called_once_with(0, 0)
        assert ChunkCoord(0, 0) in win.requested_remote_chunks


class TestApplyMessage:
    def test_chat_message_sets_status(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.apply_message({"type": "chat", "text": "hello"})
        assert "hello" in win.inventory_status

    def test_reconnecting_message_sets_status(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.apply_message({"type": "session_reconnecting"})
        assert "reconnecting" in win.inventory_status.lower()

    def test_block_delta_message_sets_block(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.apply_message(
            {
                "type": "block_delta",
                "position": [1, 2, 3],
                "block_id": 5,
            }
        )
        win.world_renderer.set_block.assert_called_once_with((1, 2, 3), 5)

    def test_block_delta_ignores_bad_position(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.apply_message({"type": "block_delta", "position": "bad", "block_id": 5})
        win.world_renderer.set_block.assert_not_called()

    def test_disconnected_clears_players_and_goes_to_multiplayer(self):
        win = _make_win()
        win.network_session = MagicMock()
        win.remote_player_entities = {1: 100}
        nc = NetworkController(win)
        nc.apply_message({"type": "session_disconnected"})
        assert win.remote_player_entities == {}
        assert win.network_session is None
        assert win.menu.screen == Screen.MULTIPLAYER

    def test_entity_snapshot_ignored_if_older_sequence(self):
        win = _make_win()
        win.last_snapshot_sequence = 10
        nc = NetworkController(win)
        nc.apply_message(
            {
                "type": "entity_snapshot",
                "players": {},
                "sequence": 5,
                "full": True,
            }
        )
        # sequence 5 < 10, should be ignored
        assert win.last_snapshot_sequence == 10

    def test_entity_snapshot_updates_players(self):
        win = _make_win()
        win.last_snapshot_sequence = 0
        nc = NetworkController(win)
        nc.apply_message(
            {
                "type": "entity_snapshot",
                "players": {},
                "sequence": 1,
                "full": True,
            }
        )
        assert win.last_snapshot_sequence == 1

    def test_unknown_message_type_is_ignored(self):
        win = _make_win()
        nc = NetworkController(win)
        nc.apply_message({"type": "future_feature", "data": 42})  # should not raise


def test_sync_remote_players_maps_held_item_component():
    win = _make_win()
    win.entities.world = EntityWorld()
    win.network_session = MagicMock(player_id=99)
    nc = NetworkController(win)

    nc.sync_remote_players(
        {
            1: {
                "position": [1.0, 64.0, 2.0],
                "yaw": 1.25,
                "held_item": {"item_id": 3, "count": 2, "hand": "left"},
            }
        }
    )

    entity = win.remote_player_entities[1]
    held_item = win.entities.world.held_items[entity]
    assert held_item.item_id == 3
    assert held_item.count == 2
    assert held_item.hand == "left"


def test_sync_remote_players_uses_player_avatar_adapter() -> None:
    win = _make_win()
    win.entities.world = EntityWorld()
    win.network_session = MagicMock(player_id=99)
    nc = NetworkController(win)

    nc.sync_remote_players(
        {
            1: {
                "position": [1.0, 64.0, 2.0],
                "yaw": math.pi,
                "name": "RemoteHero",
            }
        }
    )

    entity = win.remote_player_entities[1]
    transform = win.entities.world.transforms[entity]
    model = win.entities.world.render_models[entity]
    assert model.key == "remote_player"
    assert model.color == (0.45, 0.68, 1.0)
    assert model.scale == (0.65, 1.8, 0.65)
    assert math.isclose(transform.yaw, math.pi)


def test_update_remote_players_samples_interpolated_position() -> None:
    win = _make_win()
    win.entities.world = EntityWorld()
    win.network_session = MagicMock(player_id=99)
    nc = NetworkController(win)

    with patch(
        "voxel_sandbox.render.network_controller.time.monotonic",
        side_effect=[1.0, 1.2, 1.2],
    ):
        nc.sync_remote_players({1: {"position": [0.0, 64.0, 0.0]}})
        nc.sync_remote_players({1: {"position": [2.0, 64.0, 0.0]}})
        nc.update_remote_players()

    entity = win.remote_player_entities[1]
    transform = win.entities.world.transforms[entity]
    assert math.isclose(transform.x, 1.0)
    assert math.isclose(transform.y, 64.0)
    assert math.isclose(transform.z, 0.0)


def test_sync_remote_players_removes_stale_held_item_component():
    win = _make_win()
    win.entities.world = EntityWorld()
    win.network_session = MagicMock(player_id=99)
    nc = NetworkController(win)

    nc.sync_remote_players(
        {
            1: {
                "position": [1.0, 64.0, 2.0],
                "held_item": {"item_id": 3, "count": 2, "hand": "right"},
            }
        }
    )
    entity = win.remote_player_entities[1]
    assert win.entities.world.held_items.get(entity) is not None

    nc.sync_remote_players({1: {"position": [1.0, 64.0, 2.0]}})

    assert win.entities.world.held_items.get(entity) is None
