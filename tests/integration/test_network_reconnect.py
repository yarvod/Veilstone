from __future__ import annotations

from voxel_sandbox.network import ClientSession, LanServer


def test_client_session_can_reconnect_to_running_server() -> None:
    server = LanServer("127.0.0.1", 0, seed="reconnect")
    server.start()
    session = ClientSession()
    try:
        first = session.connect(*server.address, name="Reconnect")
        session.client.close()
        second = session.reconnect(attempts=2, delay=0.01)

        assert first["player_id"] != second["player_id"]
    finally:
        session.close()
        server.stop()
