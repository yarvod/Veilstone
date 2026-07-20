from __future__ import annotations

from typing import Any

import moderngl
import numpy as np

from voxel_sandbox.render import block_highlight


class _FakeUniform:
    def __init__(self) -> None:
        self.value: object = None
        self.written: bytes | None = None

    def write(self, value: bytes) -> None:
        self.written = value


class _FakeProgram:
    def __init__(self) -> None:
        self.uniforms = {
            "camera_matrix": _FakeUniform(),
            "block_origin": _FakeUniform(),
        }

    def __getitem__(self, name: str) -> _FakeUniform:
        return self.uniforms[name]


class _FakeShader:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.program = _FakeProgram()

    def release(self) -> None:
        pass


class _FakeResource:
    def release(self) -> None:
        pass


class _FakeVertexArray(_FakeResource):
    def __init__(self) -> None:
        self.render_modes: list[int] = []

    def render(self, mode: int) -> None:
        self.render_modes.append(mode)


class _FakeContext:
    def __init__(self) -> None:
        self.vertex_array_resource = _FakeVertexArray()

    def buffer(self, _data: bytes) -> _FakeResource:
        return _FakeResource()

    def vertex_array(self, _program: object, _content: object) -> _FakeVertexArray:
        return self.vertex_array_resource


def test_highlight_geometry_contains_only_the_twelve_cube_edges() -> None:
    edges = block_highlight.EDGES.reshape(12, 2, 3)
    normalized = {tuple(sorted((tuple(start), tuple(end)))) for start, end in edges}

    assert block_highlight.EDGES.shape == (24, 3)
    assert len(normalized) == 12
    assert all(np.count_nonzero(start != end) == 1 for start, end in edges)


def test_highlight_render_uses_lines_without_filled_faces(monkeypatch: Any) -> None:
    monkeypatch.setattr(block_highlight, "ShaderProgram", _FakeShader)
    context = _FakeContext()
    renderer = block_highlight.BlockHighlightRenderer(context)  # type: ignore[arg-type]

    renderer.render(np.eye(4, dtype=np.float32), (4, 5, 6))

    assert context.vertex_array_resource.render_modes == [moderngl.LINES]
