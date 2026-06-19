"""Tests for mob spawning validation, AI obstacle avoidance, and attack height check."""

from __future__ import annotations

from voxel_sandbox.engine.ecs.components import MobKind, MobState
from voxel_sandbox.engine.ecs.simulation import EntitySimulation

STONE = 1


class TestMobSpawnValidation:
    def _make_sim(self) -> EntitySimulation:
        return EntitySimulation(seed=42)

    def test_spawn_skips_blocked_positions(self):
        sim = self._make_sim()

        def ground_height(x: int, z: int) -> int:
            return 30

        def is_hazard(x: int, y: int, z: int) -> bool:
            return False

        def is_solid(x: int, y: int, z: int) -> bool:
            if y < 30:
                return True
            return y in (30, 31)

        sim.maintain_population(
            (8.0, 32.0, 8.0),
            ground_height,
            is_hazard,
            passive_count=5,
            hostile_count=0,
            is_solid=is_solid,
        )
        count = len(sim.world.mob_ai)
        assert count == 0

    def test_spawn_works_with_clearance(self):
        sim = self._make_sim()

        def ground_height(x: int, z: int) -> int:
            return 30

        def is_hazard(x: int, y: int, z: int) -> bool:
            return False

        def is_solid(x: int, y: int, z: int) -> bool:
            return y < 30

        sim.maintain_population(
            (8.0, 32.0, 8.0),
            ground_height,
            is_hazard,
            passive_count=3,
            hostile_count=0,
            is_solid=is_solid,
        )
        count = len(sim.world.mob_ai)
        assert count == 3

    def test_spawn_without_is_solid_still_works(self):
        sim = self._make_sim()

        def ground_height(x: int, z: int) -> int:
            return 30

        def is_hazard(x: int, y: int, z: int) -> bool:
            return False

        sim.maintain_population(
            (8.0, 32.0, 8.0),
            ground_height,
            is_hazard,
            passive_count=3,
            hostile_count=0,
        )
        count = len(sim.world.mob_ai)
        assert count == 3


class TestZombieAttackHeightCheck:
    def _ground(self, x: int, z: int) -> int:
        return 30

    def _hazard(self, x: int, y: int, z: int) -> bool:
        return False

    def _solid(self, x: int, y: int, z: int) -> bool:
        return y < 30

    def test_zombie_cannot_attack_player_above(self):
        sim = EntitySimulation(seed=42)
        sim.spawn_mob(MobKind.HOSTILE, (5.0, 30.0, 5.0))

        player_above = (5.0, 35.0, 5.0)
        damage = sim.update(1 / 60, player_above, self._ground, self._hazard, is_solid=self._solid)
        assert damage == 0.0

    def test_zombie_can_attack_player_at_same_height(self):
        sim = EntitySimulation(seed=42)
        entity = sim.spawn_mob(MobKind.HOSTILE, (5.0, 30.0, 5.0))
        ai = sim.world.mob_ai[entity]
        ai.state = MobState.CHASE
        ai.attack_cooldown = 0.0

        transform = sim.world.transforms[entity]
        player_pos = (transform.x + 0.5, transform.y, transform.z)

        damage = sim.update(1 / 60, player_pos, self._ground, self._hazard, is_solid=self._solid)
        assert damage > 0.0

    def test_zombie_cannot_attack_player_2_blocks_below(self):
        sim = EntitySimulation(seed=42)
        entity = sim.spawn_mob(MobKind.HOSTILE, (5.0, 35.0, 5.0))
        ai = sim.world.mob_ai[entity]
        ai.state = MobState.CHASE
        ai.attack_cooldown = 0.0

        transform = sim.world.transforms[entity]
        player_below = (transform.x + 0.5, 30.0, transform.z)

        damage = sim.update(1 / 60, player_below, self._ground, self._hazard, is_solid=self._solid)
        assert damage == 0.0

    def test_attack_animation_resets_on_each_hit(self):
        sim = EntitySimulation(seed=42)
        entity = sim.spawn_mob(MobKind.HOSTILE, (5.0, 30.0, 5.0))
        ai = sim.world.mob_ai[entity]
        ai.state = MobState.CHASE
        ai.attack_cooldown = 0.0

        transform = sim.world.transforms[entity]
        player_pos = (transform.x + 0.5, transform.y, transform.z)

        sim.update(1 / 60, player_pos, self._ground, self._hazard, is_solid=self._solid)
        anim = sim.world.animations[entity]
        assert anim.state_phase == 0.0


class TestMobObstacleAvoidance:
    def test_mob_does_not_reverse_immediately_on_wall(self):
        sim = EntitySimulation(seed=42)
        entity = sim.spawn_mob(MobKind.PASSIVE, (5.0, 30.0, 5.0))
        ai = sim.world.mob_ai[entity]
        ai.state = MobState.WANDER
        ai.direction_x = 1.0
        ai.direction_z = 0.0
        ai.state_time = 5.0

        def ground_height(x: int, z: int) -> int:
            return 30

        def is_hazard(x: int, y: int, z: int) -> bool:
            return False

        def is_solid(x: int, y: int, z: int) -> bool:
            if y < 30:
                return True
            return x >= 6

        for _ in range(10):
            sim.update(1 / 60, (100.0, 100.0, 100.0), ground_height, is_hazard, is_solid=is_solid)

        assert not (ai.direction_x == -1.0 and ai.direction_z == 0.0), (
            "Mob should try to go around, not just reverse"
        )
