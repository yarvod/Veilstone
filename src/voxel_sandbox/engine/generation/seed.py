from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorldSeed:
    value: int

    @classmethod
    def parse(cls, value: int | str) -> WorldSeed:
        if isinstance(value, int):
            return cls(value & 0xFFFFFFFFFFFFFFFF)
        digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
        return cls(int.from_bytes(digest, "little"))
