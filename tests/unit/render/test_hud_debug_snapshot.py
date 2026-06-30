from __future__ import annotations

from types import SimpleNamespace

from voxel_sandbox.render.hud_controller import DebugSlowTelemetry, HudWindowAdapter
from voxel_sandbox.render.perf import RenderQueueSnapshot, RuntimePerfSnapshot


class _Generation:
    def biome_key_at(self, _x: int, _z: int) -> str:
        return "plains"


def test_hud_debug_snapshot_formats_window_state_without_controller_reads() -> None:
    adapter = HudWindowAdapter(_fake_window())

    snapshot = adapter.debug_overlay_snapshot(
        entity_draws=7,
        slow_telemetry=DebugSlowTelemetry(
            memory="123 MB",
            runtime="Python test",
            device="Unit GPU",
        ),
        animation_summary="idle:1",
        selected_item_name="Stone x2",
    )

    assert "FPS  60.0 Frame  16.7 ms" in snapshot.text
    assert "Biome plains Memory 123 MB" in snapshot.text
    assert "Chunks 9 Pending 1 Mesh queue 2 Stream remesh 3 Visible sections 4" in snapshot.text
    assert "Entities 5 Mobs 2 Drops 1 Entity draws 7" in snapshot.text
    assert "Network singleplayer Known players 1" in snapshot.text
    assert "Runtime Python test Frame 1280x720" in snapshot.text
    assert "Device Unit GPU" in snapshot.text
    assert "Animation states idle:1" in snapshot.text
    assert "Selected Stone x2" in snapshot.text
    assert "Target (1, 2, 3)" in snapshot.text


def test_hud_player_list_snapshot_formats_singleplayer() -> None:
    adapter = HudWindowAdapter(_fake_window())

    snapshot = adapter.player_list_snapshot()

    assert snapshot.lines == ("Players Online:", "You (Singleplayer)")
    assert snapshot.text == "Players Online:\nYou (Singleplayer)"


def test_hud_player_list_snapshot_filters_local_network_player() -> None:
    window = _fake_window()
    window.network_session = SimpleNamespace(player_id=42)
    window.network_players = {
        42: {"name": "Local"},
        7: {"name": "Alex"},
        8: {},
    }
    adapter = HudWindowAdapter(window)

    snapshot = adapter.player_list_snapshot()

    assert snapshot.lines == ("Players Online:", "You (Local)", "Alex", "Player 8")


def _fake_window() -> SimpleNamespace:
    return SimpleNamespace(
        width=1280,
        height=720,
        runtime_perf_snapshot=RuntimePerfSnapshot(
            fps=60.0,
            frame_ms=16.7,
            update_ms=4.0,
            render_ms=12.7,
            queues=RenderQueueSnapshot(
                loaded_chunks=9,
                pending_chunks=1,
                pending_meshes=2,
                pending_stream_remeshes=3,
                visible_sections=4,
            ),
        ),
        camera=SimpleNamespace(
            position=(10.5, 64.0, -3.25),
            yaw_degrees=90.0,
            pitch_degrees=-5.0,
        ),
        player=SimpleNamespace(on_ground=True, velocity_y=0.0),
        settings=SimpleNamespace(
            world=SimpleNamespace(render_distance=3, mesh_uploads_per_frame=2)
        ),
        world_renderer=SimpleNamespace(
            face_count=120,
            triangle_count=240,
            draw_calls=8,
            daylight=0.95,
            smooth_lighting=True,
            ambient_occlusion=True,
            fog_enabled=True,
            greedy_meshing=True,
            selection=SimpleNamespace(block=(1, 2, 3)),
        ),
        player_health=20.0,
        entities=SimpleNamespace(
            world=SimpleNamespace(
                alive={1, 2, 3, 4, 5},
                mob_ai={2: object(), 3: object()},
                items={4: object()},
            )
        ),
        remote_player_entities={},
        network_session=None,
        network_players={1: {"name": "You"}},
        world_runtime=SimpleNamespace(generation=_Generation()),
    )
