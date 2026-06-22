from __future__ import annotations

# pyright: reportPrivateUsage=false
from voxel_sandbox.network.server import _player_snapshot_payload, _validated_held_item


def test_validated_held_item_accepts_compact_payload() -> None:
    assert _validated_held_item({"item_id": 3, "count": 2, "hand": "left"}) == {
        "item_id": 3,
        "count": 2,
        "hand": "left",
    }


def test_validated_held_item_rejects_invalid_payloads() -> None:
    assert _validated_held_item(None) is None
    assert _validated_held_item({"item_id": 0, "count": 1, "hand": "right"}) is None
    assert _validated_held_item({"item_id": 3, "count": 0, "hand": "right"}) is None
    assert _validated_held_item({"item_id": 3, "count": 1, "hand": "off"}) is None


def test_player_snapshot_payload_includes_held_item_when_present() -> None:
    payload = _player_snapshot_payload(
        {
            "name": "Remote",
            "position": [1.0, 2.0, 3.0],
            "yaw": 1.25,
            "animation_state": "walk",
            "animation_phase": 0.5,
            "held_item": {"item_id": 3, "count": 2, "hand": "right"},
        }
    )

    assert payload["held_item"] == {"item_id": 3, "count": 2, "hand": "right"}
