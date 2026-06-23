#version 330 core

uniform mat4 light_matrix;
uniform vec3 section_origin;

in vec3 in_position;
in vec2 in_uv;
in vec4 in_atlas_rect;

out vec2 vertex_uv;
out vec4 vertex_atlas_rect;

void main() {
    vertex_uv = in_uv;
    vertex_atlas_rect = in_atlas_rect;
    gl_Position = light_matrix * vec4(in_position + section_origin, 1.0);
}
