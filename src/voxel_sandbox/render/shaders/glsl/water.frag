#version 330 core

uniform sampler2D texture_atlas;
uniform vec3 camera_position;
uniform vec3 fog_color;
uniform float fog_start;
uniform float fog_end;
uniform int fog_enabled;
uniform vec3 sky_color;
uniform float animation_time;

in vec2 vertex_uv;
in float vertex_light;
in vec3 vertex_world_position;
in vec4 vertex_atlas_rect;
in vec3 vertex_normal;

out vec4 frag_color;

void main() {
    vec2 first_wave = fract(vertex_uv + vec2(animation_time * 0.006, -animation_time * 0.004));
    vec2 second_wave = fract(vertex_uv.yx * 1.7 + vec2(-animation_time * 0.004, animation_time * 0.007));
    vec2 first_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, first_wave);
    vec2 second_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, second_wave);
    vec3 water_color = mix(texture(texture_atlas, first_uv).rgb, texture(texture_atlas, second_uv).rgb, 0.42);
    vec3 view_direction = normalize(camera_position - vertex_world_position);
    float fresnel = pow(1.0 - max(dot(normalize(vertex_normal), view_direction), 0.0), 4.0);
    float surface = smoothstep(0.45, 0.9, vertex_normal.y);
    vec3 deep_tint = vec3(0.045, 0.20, 0.28);
    vec3 lit_color = mix(deep_tint, water_color, 0.58 + surface * 0.18) * vertex_light;
    lit_color = mix(lit_color, sky_color, fresnel * surface * 0.68);
    float distance_to_camera = length(vertex_world_position - camera_position);
    float fog_factor = fog_enabled == 1
        ? smoothstep(fog_start, max(fog_start + 0.1, fog_end), distance_to_camera)
        : 0.0;
    float alpha = mix(0.62, 0.38 + fresnel * 0.20, surface);
    frag_color = vec4(mix(lit_color, fog_color, fog_factor), alpha);
}
