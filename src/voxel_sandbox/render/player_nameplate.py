from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_nameplate import (
    PlayerNameplateSnapshot,
    build_player_nameplate_snapshot,
)


@dataclass(frozen=True, slots=True)
class PlayerNameplateRenderData:
    text: str
    world_position: tuple[float, float, float]
    alpha: float


def build_player_nameplate_render_data(
    snapshot: PlayerNameplateSnapshot,
) -> PlayerNameplateRenderData | None:
    if not snapshot.visible:
        return None
    return PlayerNameplateRenderData(
        text=snapshot.name,
        world_position=snapshot.world_position,
        alpha=snapshot.alpha,
    )


def build_remote_player_nameplate_render_data(
    *,
    player_id: int,
    name: str,
    player_position: tuple[float, float, float],
    camera_position: tuple[float, float, float],
) -> PlayerNameplateRenderData | None:
    snapshot = build_player_nameplate_snapshot(
        player_id=player_id,
        name=name,
        player_position=player_position,
        camera_position=camera_position,
    )
    return build_player_nameplate_render_data(snapshot)
