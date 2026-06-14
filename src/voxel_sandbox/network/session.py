from __future__ import annotations

import queue
import threading

from voxel_sandbox.network.client import LanClient
from voxel_sandbox.network.protocol import Message


class ClientSession:
    def __init__(self) -> None:
        self.client = LanClient()
        self._messages: queue.SimpleQueue[Message] = queue.SimpleQueue()
        self._thread: threading.Thread | None = None
        self._closed = threading.Event()

    @property
    def player_id(self) -> int | None:
        return self.client.player_id

    def connect(self, host: str, port: int, *, name: str) -> Message:
        joined = self.client.connect(host, port, name=name)
        assert self.client.connection is not None
        self.client.connection.settimeout(None)
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        return joined

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
                return
