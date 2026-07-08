#version 330 core

uniform mat4 camera_matrix;
uniform mat4 shadow_matrix;
uniform vec3 section_origin;
uniform vec3 light_direction;
uniform float vegetation_wind_time;
uniform int vegetation_wind_enabled;

in vec3 in_position;
in vec2 in_uv;
in vec3 in_normal;
in float in_sky_light;
in float in_block_light;
in float in_ao;
in vec4 in_atlas_rect;
in float in_wind_motion;

out vec2 vertex_uv;
out float vertex_directional;
out float vertex_sky_light;
out float vertex_block_light;
out float vertex_ao;
out vec3 vertex_world_position;
out vec4 vertex_atlas_rect;
out vec4 vertex_shadow_position;

vec3 apply_vegetation_wind(vec3 world_position) {
    if (vegetation_wind_enabled == 0 || in_wind_motion < 0.5) {
        return world_position;
    }
    float phase = dot(world_position.xz, vec2(0.31, 0.47)) + vegetation_wind_time * 1.7;
    float cross_weight = clamp(in_uv.y, 0.0, 1.0);
    float strength = in_wind_motion > 1.5 ? 0.045 * cross_weight : 0.015;
    vec2 sway = vec2(sin(phase), cos(phase * 0.73)) * strength;
    return world_position + vec3(sway.x, 0.0, sway.y);
}

void main() {
    vertex_uv = in_uv;
    vertex_directional = 0.48 + 0.52 * max(dot(in_normal, normalize(light_direction)), 0.0);
    vertex_sky_light = in_sky_light;
    vertex_block_light = in_block_light;
    vertex_ao = in_ao;
    vertex_atlas_rect = in_atlas_rect;
    vertex_world_position = apply_vegetation_wind(in_position + section_origin);
    vertex_shadow_position = shadow_matrix * vec4(vertex_world_position, 1.0);
    gl_Position = camera_matrix * vec4(vertex_world_position, 1.0);
}
