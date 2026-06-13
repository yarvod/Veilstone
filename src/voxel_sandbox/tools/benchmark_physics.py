from __future__ import annotations

from time import perf_counter

from voxel_sandbox.engine.physics import PlayerController, PlayerInput


def _benchmark_world(x: int, y: int, z: int) -> int:
    return int(y <= 0 or (x == 4 and 1 <= y <= 3 and -8 <= z <= 8))


def run_benchmark(ticks: int = 20_000) -> int:
    player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
    start = perf_counter()
    for tick in range(ticks):
        player.update(
            PlayerInput(forward=1.0, right=0.25, jump=tick % 180 == 0),
            -20.0,
            1.0 / 60.0,
            _benchmark_world,
        )
    elapsed = perf_counter() - start
    print(
        f"player physics {ticks} ticks: total={elapsed * 1000.0:.2f} ms "
        f"avg={elapsed * 1_000_000.0 / ticks:.3f} us/tick"
    )
    return 0
