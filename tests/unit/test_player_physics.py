from __future__ import annotations

from voxel_sandbox.engine.physics import PlayerController, PlayerInput


def flat_world(x: int, y: int, z: int) -> int:
    del x, z
    return 1 if y <= 0 else 0


def test_player_falls_onto_floor() -> None:
    player = PlayerController(x=0.5, y=3.0, z=0.5)

    for _ in range(120):
        player.update(PlayerInput(), 0.0, 1.0 / 60.0, flat_world)

    assert 0.99 < player.y < 1.01
    assert player.on_ground
    assert player.velocity_y == 0.0


def test_player_cannot_walk_through_wall() -> None:
    def world(x: int, y: int, z: int) -> int:
        return 1 if y <= 0 or (x == 2 and 1 <= y <= 2 and z == 0) else 0

    player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
    for _ in range(60):
        player.update(PlayerInput(forward=1.0), 0.0, 1.0 / 60.0, world)

    assert player.x < 1.71


def test_player_can_swim_out_of_water_onto_one_block_shore() -> None:
    def world(x: int, y: int, z: int) -> int:
        del z
        if y <= 0:
            return 1
        return 1 if x >= 1 and y == 1 else 0

    def is_fluid(x: int, y: int, z: int) -> bool:
        del z
        return x <= 0 and y == 1

    player = PlayerController(x=0.35, y=1.05, z=0.5, in_water=True)
    dt = 1.0 / 60.0

    for _ in range(45):
        player.update(
            PlayerInput(forward=1.0, jump=True),
            0.0,
            dt,
            world,
            is_fluid=is_fluid,
        )

    assert player.x > 1.15
    assert player.y >= 1.95


def test_swim_jump_buoyancy_stays_capped() -> None:
    def world(x: int, y: int, z: int) -> int:
        del x, z
        return 1 if y <= 0 else 0

    def is_solid(x: int, y: int, z: int) -> bool:
        return world(x, y, z) != 0

    def is_fluid(x: int, y: int, z: int) -> bool:
        del x, z
        return 1 <= y <= 3

    player = PlayerController(x=0.5, y=1.0, z=0.5, velocity_y=3.9, in_water=True)

    player.update(
        PlayerInput(jump=True),
        0.0,
        1.0 / 60.0,
        world,
        is_solid=is_solid,
        is_fluid=is_fluid,
    )

    assert player.in_water
    assert 0.0 < player.velocity_y <= 4.0


def test_swimming_without_jump_sinks_slowly_instead_of_freefalling() -> None:
    def world(x: int, y: int, z: int) -> int:
        del x, z
        return 1 if y <= 0 else 0

    def is_solid(x: int, y: int, z: int) -> bool:
        return world(x, y, z) != 0

    def is_fluid(x: int, y: int, z: int) -> bool:
        del x, z
        return 1 <= y <= 3

    player = PlayerController(x=0.5, y=2.0, z=0.5, in_water=True)

    player.update(
        PlayerInput(),
        0.0,
        1.0 / 60.0,
        world,
        is_solid=is_solid,
        is_fluid=is_fluid,
    )

    assert player.in_water
    assert -1.0 < player.velocity_y < 0.0


def test_swim_step_up_does_not_clip_through_higher_shore_wall() -> None:
    def world(x: int, y: int, z: int) -> int:
        del z
        if y <= 0:
            return 1
        if x >= 2 and 1 <= y <= 2:
            return 1
        return 1 if x >= 1 and y == 1 else 0

    def is_solid(x: int, y: int, z: int) -> bool:
        block = world(x, y, z)
        return block != 0

    def is_fluid(x: int, y: int, z: int) -> bool:
        del z
        return x <= 0 and y == 1

    player = PlayerController(x=0.35, y=1.05, z=0.5, in_water=True)
    dt = 1.0 / 60.0

    for _ in range(60):
        player.update(
            PlayerInput(forward=1.0, jump=True),
            0.0,
            dt,
            world,
            is_solid=is_solid,
            is_fluid=is_fluid,
        )

    assert 1.05 < player.x < 1.71
    assert player.y >= 1.95
    assert not player.in_water


def test_player_jumps_only_from_ground() -> None:
    player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
    player.update(PlayerInput(jump=True), 0.0, 1.0 / 60.0, flat_world)
    first_velocity = player.velocity_y
    player.update(PlayerInput(jump=True), 0.0, 1.0 / 60.0, flat_world)

    assert first_velocity > 0.0
    assert player.velocity_y < first_velocity


def _ledge_world(x: int, y: int, z: int) -> int:
    """Ground exists only for x < 2; infinite drop beyond."""
    del z
    if y <= 0 and x < 2:
        return 1
    return 0


def _walk_off_ledge(start_x: float = 1.8) -> PlayerController:
    """Return a player that has just walked off the ledge (in air with coyote active)."""
    player = PlayerController(x=start_x, y=1.0, z=0.5, on_ground=True)
    dt = 1.0 / 60.0
    # Walk until fully off the ledge (back edge past x=2, i.e. player.x >= 2.3)
    for _ in range(20):
        player.update(PlayerInput(forward=1.0), 0.0, dt, _ledge_world)
        if not player.on_ground:
            break
    return player


def test_coyote_time_allows_jump_after_leaving_ledge() -> None:
    player = _walk_off_ledge()
    assert not player.on_ground
    assert player._coyote_timer > 0.0
    # Jump within the coyote window
    dt = 1.0 / 60.0
    player.update(PlayerInput(forward=1.0, jump=True), 0.0, dt, _ledge_world)
    assert player.velocity_y > 0.0


def test_coyote_time_expires_before_jump() -> None:
    player = _walk_off_ledge()
    assert not player.on_ground
    dt = 1.0 / 60.0
    # Wait for coyote window to expire
    for _ in range(20):
        player.update(PlayerInput(), 0.0, dt, _ledge_world)
    assert player._coyote_timer == 0.0
    # Now press jump: should NOT fire (no ground, no coyote)
    before_vy = player.velocity_y
    player.update(PlayerInput(jump=True), 0.0, dt, _ledge_world)
    assert player.velocity_y <= before_vy  # gravity only, no jump boost


def test_jump_buffer_fires_on_landing() -> None:
    # Player just above ground: pressing jump mid-air fires on contact
    player = PlayerController(x=0.5, y=1.1, z=0.5)
    dt = 1.0 / 60.0
    # One tap of jump while in air
    player.update(PlayerInput(jump=True), 0.0, dt, flat_world)
    # Release jump and fall toward ground
    for _ in range(10):
        player.update(PlayerInput(), 0.0, dt, flat_world)
    # Buffer should have fired on landing
    assert player.velocity_y > 0.0


def test_jump_buffer_expires_before_landing() -> None:
    # Player far above ground: buffer expires before landing
    player = PlayerController(x=0.5, y=3.0, z=0.5)
    dt = 1.0 / 60.0
    player.update(PlayerInput(jump=True), 0.0, dt, flat_world)
    # Fall long enough for buffer to expire, then land
    for _ in range(120):
        player.update(PlayerInput(), 0.0, dt, flat_world)
    assert player.on_ground
    assert player.velocity_y == 0.0  # landed quietly, no jump


def test_variable_jump_height_shorter_when_released() -> None:
    # Holding jump all the way gives more height than tapping
    def max_height_with_hold() -> float:
        player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
        dt = 1.0 / 60.0
        player.update(PlayerInput(jump=True), 0.0, dt, flat_world)
        for _ in range(30):
            player.update(PlayerInput(jump=True), 0.0, dt, flat_world)
        return player.y

    def max_height_with_tap() -> float:
        player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
        dt = 1.0 / 60.0
        player.update(PlayerInput(jump=True), 0.0, dt, flat_world)
        # Immediately release
        for _ in range(30):
            player.update(PlayerInput(), 0.0, dt, flat_world)
        return player.y

    assert max_height_with_hold() > max_height_with_tap()


def test_sprint_moves_faster_than_walk() -> None:
    def travel(sprint: bool) -> float:
        player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
        dt = 1.0 / 60.0
        for _ in range(60):
            player.update(PlayerInput(forward=1.0, sprint=sprint), 0.0, dt, flat_world)
        return player.x

    assert travel(sprint=True) > travel(sprint=False)


def test_player_intersection_prevents_placing_inside_body() -> None:
    player = PlayerController(x=0.5, y=1.0, z=0.5)
    assert player.intersects_block((0, 1, 0))
    assert not player.intersects_block((2, 1, 0))


def test_player_reports_collision_at_current_position() -> None:
    player = PlayerController(x=0.5, y=0.5, z=0.5)
    assert player.collides(flat_world)
