from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from voxel_sandbox.render.material_binding import MaterialAtlasBinding
from voxel_sandbox.render.material_shader_setup import MaterialShaderSetup
from voxel_sandbox.render.shaders.loader import ShaderFiles


@dataclass(frozen=True, slots=True)
class MaterialShaderRuntimeWiring:
    chunk_shader_name: str
    material_shader_files: ShaderFiles | None
    material_bindings: tuple[MaterialAtlasBinding, ...]

    @property
    def uses_material_shader(self) -> bool:
        return self.material_shader_files is not None


def build_material_shader_runtime_wiring(
    setup: MaterialShaderSetup,
    shader_root: Path,
) -> MaterialShaderRuntimeWiring:
    if not setup.uses_material_shader:
        return MaterialShaderRuntimeWiring(
            chunk_shader_name=setup.shader.shader_name,
            material_shader_files=None,
            material_bindings=(),
        )

    return MaterialShaderRuntimeWiring(
        chunk_shader_name=setup.shader.shader_name,
        material_shader_files=ShaderFiles.from_directory(
            shader_root,
            setup.shader.shader_name,
        ),
        material_bindings=setup.binding_plan.bindings,
    )
