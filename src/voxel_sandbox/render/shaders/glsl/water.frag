#version 330 core

uniform sampler2D texture_atlas;
uniform vec3 camera_position;
uniform vec3 fog_color;
uniform float fog_start;
uniform float fog_end;
uniform int fog_enabled;
uniform vec3 sky_color;
uniform float animation_time;
uniform int water_detail_enabled;

in vec2 vertex_uv;
in float vertex_light;
in vec3 vertex_world_position;
in vec4 vertex_atlas_rect;
in vec3 vertex_normal;
in float vertex_shore_factor;

out vec4 frag_color;

void main() {
    vec2 first_wave = fract(vertex_uv + vec2(animation_time * 0.006, -animation_time * 0.004));
    vec2 second_wave = fract(vertex_uv.yx * 1.7 + vec2(-animation_time * 0.004, animation_time * 0.007));
    vec2 first_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, first_wave);
    vec2 second_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, second_wave);
    vec3 water_color = mix(texture(texture_atlas, first_uv).rgb, texture(texture_atlas, second_uv).rgb, 0.42);
    float surface = smoothstep(0.45, 0.9, vertex_normal.y);
    float water_detail = float(water_detail_enabled);
    vec3 base_normal = normalize(vertex_normal);
    float ripple_x = cos(vertex_world_position.x * 1.8 + vertex_world_position.z * 0.35
        + animation_time * 0.9)
        + cos(vertex_world_position.x * 0.7 - vertex_world_position.z * 2.1
            - animation_time * 1.1) * 0.55;
    float ripple_z = sin(vertex_world_position.z * 1.6 - vertex_world_position.x * 0.4
        - animation_time * 0.75)
        + sin(vertex_world_position.z * 0.65 + vertex_world_position.x * 2.2
            + animation_time * 1.2) * 0.5;
    vec3 ripple_normal = normalize(vec3(-ripple_x * 0.14, 1.0, -ripple_z * 0.14));
    vec3 water_normal = normalize(mix(base_normal, ripple_normal, surface * water_detail));
    vec3 view_direction = normalize(camera_position - vertex_world_position);
    float fresnel = pow(1.0 - max(dot(water_normal, view_direction), 0.0), 4.0);
    vec3 deep_tint = vec3(0.045, 0.20, 0.28);
    vec3 lit_color = mix(deep_tint, water_color, 0.58 + surface * 0.18) * vertex_light;
    float reflection_strength = fresnel * surface * (0.68 + water_detail * 0.12);
    lit_color = mix(lit_color, sky_color, reflection_strength);
    float crest_wave = sin(vertex_world_position.x * 3.7 + animation_time * 1.25)
        + sin(vertex_world_position.z * 4.1 - animation_time * 1.55);
    float crest = smoothstep(0.42, 0.95, crest_wave * 0.5 + 0.5) * surface;
    crest *= water_detail;
    vec3 highlight_color = mix(vec3(0.16, 0.42, 0.56), sky_color, 0.72);
    lit_color += highlight_color * crest * (0.05 + fresnel * 0.22) * vertex_light;
    float shoreline = smoothstep(0.08, 0.9, vertex_shore_factor) * surface * water_detail;
    float shore_ripple = 0.72 + 0.28 * sin(
        (vertex_world_position.x + vertex_world_position.z) * 5.2 - animation_time * 1.8
    );
    vec3 shore_color = mix(vec3(0.20, 0.48, 0.60), sky_color, 0.76);
    lit_color += shore_color * shoreline * shore_ripple * 0.10 * vertex_light;
    float distance_to_camera = length(vertex_world_position - camera_position);
    float fog_factor = fog_enabled == 1
        ? smoothstep(fog_start, max(fog_start + 0.1, fog_end), distance_to_camera)
        : 0.0;
    float alpha = mix(
        0.62,
        0.44 + fresnel * 0.24 + crest * 0.05 + shoreline * 0.04,
        surface
    );
    frag_color = vec4(mix(lit_color, fog_color, fog_factor), alpha);
}
