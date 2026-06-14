from __future__ import annotations

import math
from dataclasses import dataclass
from time import perf_counter

from voxel_sandbox.engine.ecs import EntitySimulation, MobKind
from voxel_sandbox.network.protocol import Message, encode_frame

SERVER_TICK_BUDGET_MS = 50.0


@dataclass(frozen=True, slots=True)
class ServerBenchmarkResult:
    players: int
    mobs: int
    ticks: int
    average_ms: float
    p95_ms: float
    maximum_ms: float


def measure_server_ticks(
    *,
    ticks: int = 300,
    player_count: int = 8,
    mob_count: int = 200,
) -> ServerBenchmarkResult:
    simulation = EntitySimulation(seed=14)
    players = tuple(
        (float(index) * 1.5, 32.0, float(index % 2) * 4.0) for index in range(player_count)
    )
    for index in range(mob_count):
        angle = math.tau * index / mob_count
        radius = 8.0 + float(index % 12)
        simulation.spawn_mob(
            MobKind.HOSTILE if index % 3 == 0 else MobKind.PASSIVE,
            (math.cos(angle) * radius, 32.0, math.sin(angle) * radius),
        )

    timings: list[float] = []
    for tick in range(ticks):
        start = perf_counter()
        focus = players[tick % len(players)]
        simulation.update(0.05, focus, _flat_height, _never_hazard)
        transforms = tuple(simulation.world.transforms.items())
        for player_id, player in enumerate(players, start=1):
            visible = {
                entity: {"position": list(transform.position)}
                for entity, transform in transforms
                if _distance_squared(player, transform.position) <= 64.0**2
            }
            message: Message = {
                "type": "entity_snapshot",
                "sequence": tick + 1,
                "player_id": player_id,
                "entities": visible,
            }
            encode_frame(message)
        timings.append((perf_counter() - start) * 1000.0)

    ordered = sorted(timings)
    p95_index = min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)
    return ServerBenchmarkResult(
        player_count,
        mob_count,
        ticks,
        sum(timings) / len(timings),
        ordered[p95_index],
        max(timings),
    )


def run_benchmark() -> int:
    result = measure_server_ticks()
    print(
        f"server {result.players} players/{result.mobs} mobs/{result.ticks} ticks: "
        f"avg={result.average_ms:.2f} ms p95={result.p95_ms:.2f} ms "
        f"max={result.maximum_ms:.2f} ms budget={SERVER_TICK_BUDGET_MS:.1f} ms"
    )
    return 0 if result.p95_ms <= SERVER_TICK_BUDGET_MS else 1


def _flat_height(x: int, z: int) -> int:
    del x, z
    return 32


def _never_hazard(x: int, y: int, z: int) -> bool:
    del x, y, z
    return False


def _distance_squared(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    return sum((first[index] - second[index]) ** 2 for index in range(3))
