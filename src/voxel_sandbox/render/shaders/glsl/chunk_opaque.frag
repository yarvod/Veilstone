#version 330 core

uniform sampler2D texture_atlas;
uniform vec3 camera_position;
uniform vec3 day_tint;
uniform vec3 fog_color;
uniform float daylight;
uniform float fog_start;
uniform float fog_end;
uniform int fog_enabled;
uniform sampler2DShadow shadow_map;
uniform int shadows_enabled;
uniform float shadow_bias;
uniform float shadow_texel_size;

in vec2 vertex_uv;
in float vertex_directional;
in float vertex_sky_light;
in float vertex_block_light;
in float vertex_ao;
in vec3 vertex_world_position;
in vec4 vertex_atlas_rect;
in vec4 vertex_shadow_position;

out vec4 frag_color;

float sample_shadow() {
    if (shadows_enabled == 0) {
        return 1.0;
    }
    vec3 projected = vertex_shadow_position.xyz / vertex_shadow_position.w;
    projected = projected * 0.5 + 0.5;
    if (projected.z <= 0.0 || projected.z >= 1.0
            || projected.x <= 0.0 || projected.x >= 1.0
            || projected.y <= 0.0 || projected.y >= 1.0) {
        return 1.0;
    }
    float visibility = 0.0;
    for (int x = -1; x <= 1; ++x) {
        for (int y = -1; y <= 1; ++y) {
            vec2 offset = vec2(x, y) * shadow_texel_size;
            visibility += texture(
                shadow_map,
                vec3(projected.xy + offset, projected.z - max(shadow_bias, 0.004))
            );
        }
    }
    return visibility / 9.0;
}

void main() {
    vec2 tile_uv = fract(vertex_uv);
    vec2 atlas_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, tile_uv);
    vec4 base_color = texture(texture_atlas, atlas_uv);
    if (base_color.a < 0.5) {
        discard;
    }
    float sky = vertex_sky_light * daylight;
    float shadow = mix(0.34, 1.0, sample_shadow());
    float sun_light = sky * vertex_directional * shadow;
    float ambient_sky = sky * 0.36;
    float light_level = max(max(sun_light, ambient_sky), max(vertex_block_light, 0.12));
    vec3 block_warmth = vec3(1.0, 0.66, 0.34) * vertex_block_light * 0.32;
    float readable_ao = mix(0.72, 1.0, vertex_ao);
    vec3 lit_color = base_color.rgb * day_tint * light_level * readable_ao;
    lit_color += base_color.rgb * block_warmth * readable_ao;
    float distance_to_camera = length(vertex_world_position - camera_position);
    float fog_factor = fog_enabled == 1
        ? smoothstep(fog_start, max(fog_start + 0.1, fog_end), distance_to_camera)
        : 0.0;
    frag_color = vec4(mix(lit_color, fog_color, fog_factor), base_color.a);
}
