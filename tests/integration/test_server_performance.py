from __future__ import annotations

from voxel_sandbox.tools.benchmark_server import SERVER_TICK_BUDGET_MS, measure_server_ticks


def test_server_tick_handles_eight_players_and_two_hundred_mobs() -> None:
    result = measure_server_ticks(ticks=30)

    assert result.players == 8
    assert result.mobs == 200
    assert result.p95_ms <= SERVER_TICK_BUDGET_MS
