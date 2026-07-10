#version 330 core

uniform mat4 camera_matrix;
uniform vec3 section_origin;
uniform float animation_time;

in vec3 in_position;
in vec2 in_uv;
in vec3 in_normal;
in float in_sky_light;
in float in_block_light;
in float in_shore_factor;
in vec4 in_atlas_rect;

out vec2 vertex_uv;
out float vertex_light;
out vec3 vertex_world_position;
out vec4 vertex_atlas_rect;
out vec3 vertex_normal;
out float vertex_shore_factor;

void main() {
    vec3 world_position = in_position + section_origin;
    if (in_normal.y > 0.5) {
        world_position.y += sin(world_position.x * 0.55 + world_position.z * 0.42 + animation_time) * 0.025;
    }
    vertex_uv = in_uv + vec2(animation_time * 0.015, animation_time * 0.009);
    vertex_light = max(max(in_sky_light, in_block_light), 0.20);
    vertex_world_position = world_position;
    vertex_atlas_rect = in_atlas_rect;
    vertex_normal = in_normal;
    vertex_shore_factor = in_shore_factor;
    gl_Position = camera_matrix * vec4(world_position, 1.0);
}
