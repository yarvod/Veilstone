from __future__ import annotations

from unittest.mock import MagicMock

from voxel_sandbox.engine.authority import NetworkWorldAuthority


def test_network_authority_sends_compact_held_item_input_payload() -> None:
    session = MagicMock()
    authority = NetworkWorldAuthority(session, MagicMock())

    authority.send_input(
        (1.0, 2.0, 3.0),
        1.25,
        {"item_id": 3, "count": 4, "hand": "right"},
    )

    session.send.assert_called_once_with(
        {
            "type": "input",
            "position": [1.0, 2.0, 3.0],
            "yaw": 1.25,
            "held_item": {"item_id": 3, "count": 4, "hand": "right"},
        }
    )
