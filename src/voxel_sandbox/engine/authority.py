from collections.abc import Callable
from typing import Any, Protocol

from voxel_sandbox.domain.blocks.structures import StructureWorld
from voxel_sandbox.network import ClientSession

type HeldItemPayload = dict[str, object]


class WorldAuthority(Protocol):
    @property
    def structure_world(self) -> StructureWorld: ...

    def apply_block_action(self, block: tuple[int, int, int], block_id: int) -> None: ...

    def toggle_structure(self, entity_id: int) -> Any: ...

    def send_input(
        self,
        position: tuple[float, float, float],
        yaw: float,
        held_item: HeldItemPayload | None = None,
    ) -> None: ...

    def send_chat(self, text: str) -> None: ...

    def set_player_name(self, name: str) -> None: ...

    def request_chunk(self, x: int, z: int) -> None: ...

    def close(self) -> None: ...


class LocalWorldAuthority:
    def __init__(
        self,
        structure_world: StructureWorld,
        block_action_sink: Callable[[tuple[int, int, int], int], None],
    ) -> None:
        self._structure_world = structure_world
        self._block_action_sink = block_action_sink

    @property
    def structure_world(self) -> StructureWorld:
        return self._structure_world

    def apply_block_action(self, block: tuple[int, int, int], block_id: int) -> None:
        self._block_action_sink(block, block_id)

    def toggle_structure(self, entity_id: int) -> Any:
        return self._structure_world.toggle(entity_id)

    def send_input(
        self,
        position: tuple[float, float, float],
        yaw: float,
        held_item: HeldItemPayload | None = None,
    ) -> None:
        del held_item

    def send_chat(self, text: str) -> None:
        pass

    def set_player_name(self, name: str) -> None:
        pass

    def request_chunk(self, x: int, z: int) -> None:
        pass

    def close(self) -> None:
        pass


class NetworkWorldAuthority:
    def __init__(self, session: ClientSession, structure_world: StructureWorld) -> None:
        self._session = session
        self._structure_world = structure_world

    @property
    def structure_world(self) -> StructureWorld:
        return self._structure_world

    def apply_block_action(self, block: tuple[int, int, int], block_id: int) -> None:
        self._session.send({"type": "block_action", "position": list(block), "block_id": block_id})

    def toggle_structure(self, entity_id: int) -> Any:
        self._session.send({"type": "structure_toggle", "id": entity_id})
        return None

    def send_input(
        self,
        position: tuple[float, float, float],
        yaw: float,
        held_item: HeldItemPayload | None = None,
    ) -> None:
        self._session.send(
            {
                "type": "input",
                "position": list(position),
                "yaw": yaw,
                "held_item": held_item,
            }
        )

    def send_chat(self, text: str) -> None:
        self._session.send({"type": "chat", "text": text})

    def set_player_name(self, name: str) -> None:
        self._session.send({"type": "rename", "name": name})

    def request_chunk(self, x: int, z: int) -> None:
        self._session.send({"type": "request_chunk", "coord": [x, z]})

    def close(self) -> None:
        pass
