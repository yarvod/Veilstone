from __future__ import annotations

import time

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


def test_client_session_reports_automatic_reconnect() -> None:
    server = LanServer("127.0.0.1", 0, seed="auto-reconnect")
    server.start()
    session = ClientSession(auto_reconnect=True, reconnect_attempts=5, reconnect_delay=0.01)
    try:
        first = session.connect(*server.address, name="Reconnect")
        session.client.close()
        messages: list[dict[str, object]] = []
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            messages.extend(session.poll())
            if any(message.get("type") == "session_reconnected" for message in messages):
                break
            time.sleep(0.01)

        assert any(message.get("type") == "session_reconnecting" for message in messages)
        reconnected = next(
            message for message in messages if message.get("type") == "session_reconnected"
        )
        joined = reconnected["joined"]
        assert isinstance(joined, dict)
        assert joined["player_id"] != first["player_id"]
    finally:
        session.close()
        server.stop()


def test_client_session_reports_exhausted_reconnect_attempts() -> None:
    server = LanServer("127.0.0.1", 0, seed="disconnect")
    server.start()
    session = ClientSession(auto_reconnect=True, reconnect_attempts=2, reconnect_delay=0.01)
    session.connect(*server.address, name="Disconnect")
    server.stop()
    try:
        session.client.close()
        messages: list[dict[str, object]] = []
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            messages.extend(session.poll())
            if any(message.get("type") == "session_disconnected" for message in messages):
                break
            time.sleep(0.01)

        assert any(message.get("type") == "session_reconnecting" for message in messages)
        assert any(message.get("type") == "session_disconnected" for message in messages)
    finally:
        session.close()
