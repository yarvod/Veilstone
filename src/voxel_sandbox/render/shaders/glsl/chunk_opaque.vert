#version 330 core

uniform mat4 camera_matrix;
uniform mat4 shadow_matrix;
uniform vec3 section_origin;

in vec3 in_position;
in vec2 in_uv;
in vec3 in_normal;
in float in_sky_light;
in float in_block_light;
in float in_ao;
in vec4 in_atlas_rect;

out vec2 vertex_uv;
out float vertex_directional;
out float vertex_sky_light;
out float vertex_block_light;
out float vertex_ao;
out vec3 vertex_world_position;
out vec4 vertex_atlas_rect;
out vec4 vertex_shadow_position;

void main() {
    vec3 sun_direction = normalize(vec3(0.4, 0.8, 0.25));
    vertex_uv = in_uv;
    vertex_directional = 0.48 + 0.52 * max(dot(in_normal, sun_direction), 0.0);
    vertex_sky_light = in_sky_light;
    vertex_block_light = in_block_light;
    vertex_ao = in_ao;
    vertex_atlas_rect = in_atlas_rect;
    vertex_world_position = in_position + section_origin;
    vertex_shadow_position = shadow_matrix * vec4(vertex_world_position, 1.0);
    gl_Position = camera_matrix * vec4(vertex_world_position, 1.0);
}
