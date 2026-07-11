from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

FrameBottleneck = Literal["idle", "balanced", "update", "render"]


@dataclass(frozen=True, slots=True)
class RenderQueueSnapshot:
    loaded_chunks: int = 0
    pending_chunks: int = 0
    pending_meshes: int = 0
    pending_stream_relights: int = 0
    pending_stream_remeshes: int = 0
    visible_sections: int = 0


@dataclass(frozen=True, slots=True)
class RuntimePerfSnapshot:
    fps: float = 0.0
    frame_ms: float = 0.0
    update_ms: float = 0.0
    render_ms: float = 0.0
    bottleneck: FrameBottleneck = "idle"
    queues: RenderQueueSnapshot = field(default_factory=RenderQueueSnapshot)


class RuntimePerfTracker:
    def __init__(self) -> None:
        self._update_ms = 0.0
        self._render_ms = 0.0
        self._frame_ms = 0.0

    def record_update(self, seconds: float) -> None:
        self._update_ms = max(seconds, 0.0) * 1000.0
        self._refresh_frame_ms()

    def record_render(self, seconds: float) -> None:
        self._render_ms = max(seconds, 0.0) * 1000.0
        self._refresh_frame_ms()

    def snapshot(self, *, fps: float, queues: RenderQueueSnapshot) -> RuntimePerfSnapshot:
        frame_ms = 1000.0 / fps if fps > 0.0 else self._frame_ms
        return RuntimePerfSnapshot(
            fps=fps,
            frame_ms=frame_ms,
            update_ms=self._update_ms,
            render_ms=self._render_ms,
            bottleneck=frame_bottleneck(self._update_ms, self._render_ms),
            queues=queues,
        )

    def _refresh_frame_ms(self) -> None:
        self._frame_ms = self._update_ms + self._render_ms


def frame_bottleneck(update_ms: float, render_ms: float) -> FrameBottleneck:
    if update_ms <= 0.0 and render_ms <= 0.0:
        return "idle"
    if update_ms == render_ms:
        return "balanced"
    return "update" if update_ms > render_ms else "render"
