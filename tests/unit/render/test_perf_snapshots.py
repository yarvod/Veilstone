from __future__ import annotations

from voxel_sandbox.render.perf import RenderQueueSnapshot, RuntimePerfTracker


def test_runtime_perf_tracker_combines_frame_timings_and_queues() -> None:
    tracker = RuntimePerfTracker()
    queues = RenderQueueSnapshot(
        loaded_chunks=12,
        pending_chunks=2,
        pending_meshes=3,
        pending_stream_relights=5,
        pending_stream_remeshes=4,
        visible_sections=32,
    )

    tracker.record_update(0.004)
    tracker.record_render(0.006)
    snapshot = tracker.snapshot(fps=50.0, queues=queues)

    assert snapshot.fps == 50.0
    assert snapshot.frame_ms == 20.0
    assert snapshot.update_ms == 4.0
    assert snapshot.render_ms == 6.0
    assert snapshot.bottleneck == "render"
    assert snapshot.queues == queues


def test_render_queue_snapshot_defaults_hidden_work_to_zero() -> None:
    queues = RenderQueueSnapshot()

    assert queues.pending_stream_relights == 0
    assert queues.pending_stream_remeshes == 0


def test_runtime_perf_tracker_uses_recorded_frame_time_without_fps() -> None:
    tracker = RuntimePerfTracker()

    tracker.record_update(0.003)
    tracker.record_render(0.002)
    snapshot = tracker.snapshot(fps=0.0, queues=RenderQueueSnapshot())

    assert snapshot.frame_ms == 5.0


def test_runtime_perf_tracker_reports_update_bottleneck() -> None:
    tracker = RuntimePerfTracker()
    tracker.record_update(0.007)
    tracker.record_render(0.003)

    assert tracker.snapshot(fps=0.0, queues=RenderQueueSnapshot()).bottleneck == "update"


def test_runtime_perf_tracker_reports_balanced_and_idle_stages() -> None:
    tracker = RuntimePerfTracker()

    assert tracker.snapshot(fps=0.0, queues=RenderQueueSnapshot()).bottleneck == "idle"

    tracker.record_update(0.004)
    tracker.record_render(0.004)

    assert tracker.snapshot(fps=0.0, queues=RenderQueueSnapshot()).bottleneck == "balanced"
