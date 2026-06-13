# pyright: reportUnknownMemberType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import moderngl

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ShaderFiles:
    vertex: Path
    fragment: Path

    @classmethod
    def from_directory(cls, directory: str | Path, name: str) -> ShaderFiles:
        root = Path(directory)
        return cls(vertex=root / f"{name}.vert", fragment=root / f"{name}.frag")

    def read(self) -> tuple[str, str]:
        return (
            self.vertex.read_text(encoding="utf-8"),
            self.fragment.read_text(encoding="utf-8"),
        )

    def signature(self) -> tuple[int, int]:
        return self.vertex.stat().st_mtime_ns, self.fragment.stat().st_mtime_ns


class ShaderProgram:
    def __init__(self, context: moderngl.Context, files: ShaderFiles) -> None:
        self.context = context
        self.files = files
        self.program: moderngl.Program | None = None
        self._signature: tuple[int, int] | None = None
        self.reload(force=True)

    def reload_if_changed(self) -> bool:
        return self.reload(force=False)

    def reload(self, *, force: bool) -> bool:
        signature = self.files.signature()
        if not force and signature == self._signature:
            return False

        vertex_source, fragment_source = self.files.read()
        try:
            replacement = self.context.program(
                vertex_shader=vertex_source,
                fragment_shader=fragment_source,
            )
        except moderngl.Error:
            LOGGER.exception("Shader reload failed; keeping the previous program")
            return False

        previous = self.program
        self.program = replacement
        self._signature = signature
        if previous is not None:
            previous.release()
        LOGGER.info("Loaded shaders %s and %s", self.files.vertex.name, self.files.fragment.name)
        return True

    def release(self) -> None:
        if self.program is not None:
            self.program.release()
            self.program = None
