from __future__ import annotations

import queue
import threading
import time

from voxel_sandbox.network.client import LanClient
from voxel_sandbox.network.protocol import Message


class ClientSession:
    def __init__(
        self,
        *,
        auto_reconnect: bool = False,
        reconnect_attempts: int = 3,
        reconnect_delay: float = 0.1,
    ) -> None:
        self.client = LanClient()
        self._messages: queue.SimpleQueue[Message] = queue.SimpleQueue()
        self._thread: threading.Thread | None = None
        self._closed = threading.Event()
        self._target: tuple[str, int, str, tuple[float, float, float] | None] | None = None
        self._auto_reconnect = auto_reconnect
        self._reconnect_attempts = reconnect_attempts
        self._reconnect_delay = reconnect_delay

    @property
    def player_id(self) -> int | None:
        return self.client.player_id

    def connect(
        self,
        host: str,
        port: int,
        *,
        name: str,
        position: tuple[float, float, float] | None = None,
    ) -> Message:
        self._target = host, port, name, position
        self._closed.clear()
        joined = self.client.connect(host, port, name=name, position=position)
        assert self.client.connection is not None
        self.client.connection.settimeout(None)
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        return joined

    def reconnect(self, *, attempts: int = 3, delay: float = 0.1) -> Message:
        if self._target is None:
            raise ConnectionError("Session has no previous target")
        self.client.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        host, port, name, position = self._target
        last_error: OSError | None = None
        for _ in range(attempts):
            try:
                self.client = LanClient()
                return self.connect(host, port, name=name, position=position)
            except OSError as error:
                last_error = error
                time.sleep(delay)
        raise ConnectionError("Reconnect attempts exhausted") from last_error

    def send(self, message: Message) -> None:
        self.client.send(message)

    def poll(self, limit: int = 32) -> tuple[Message, ...]:
        messages: list[Message] = []
        while len(messages) < limit:
            try:
                messages.append(self._messages.get_nowait())
            except queue.Empty:
                break
        return tuple(messages)

    def close(self) -> None:
        self._closed.set()
        self.client.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _receive_loop(self) -> None:
        while not self._closed.is_set():
            try:
                self._messages.put(self.client.receive())
            except (EOFError, ConnectionError, OSError):
                if self._closed.is_set() or not self._auto_reconnect:
                    return
                self._messages.put({"type": "session_reconnecting"})
                joined = self._reconnect_from_receiver()
                if joined is None:
                    self._messages.put({"type": "session_disconnected"})
                    return
                self._messages.put({"type": "session_reconnected", "joined": joined})

    def _reconnect_from_receiver(self) -> Message | None:
        if self._target is None:
            return None
        host, port, name, position = self._target
        self.client.close()
        for _ in range(self._reconnect_attempts):
            if self._closed.is_set():
                return None
            candidate = LanClient()
            try:
                joined = candidate.connect(host, port, name=name, position=position)
            except OSError:
                candidate.close()
                time.sleep(self._reconnect_delay)
                continue
            assert candidate.connection is not None
            candidate.connection.settimeout(None)
            self.client = candidate
            return joined
        return None
