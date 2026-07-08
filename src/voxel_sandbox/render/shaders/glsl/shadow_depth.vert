#version 330 core

uniform mat4 light_matrix;
uniform vec3 section_origin;
uniform float vegetation_wind_time;
uniform int vegetation_wind_enabled;

in vec3 in_position;
in vec2 in_uv;
in vec4 in_atlas_rect;
in float in_wind_motion;

out vec2 vertex_uv;
out vec4 vertex_atlas_rect;

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
    vertex_atlas_rect = in_atlas_rect;
    gl_Position = light_matrix * vec4(apply_vegetation_wind(in_position + section_origin), 1.0);
}
