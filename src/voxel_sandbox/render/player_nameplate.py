from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_nameplate import PlayerNameplateSnapshot


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
