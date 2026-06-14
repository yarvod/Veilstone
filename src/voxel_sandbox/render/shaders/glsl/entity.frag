#version 330 core

uniform sampler2D entity_texture;
uniform vec3 entity_color;
uniform int use_texture;
uniform vec3 day_tint;
uniform float daylight;
uniform float entity_sky_light;
uniform float entity_block_light;
uniform vec3 light_direction;
uniform sampler2DShadow shadow_map;
uniform int shadows_enabled;
uniform float shadow_bias;
uniform float shadow_texel_size;

in vec2 vertex_uv;
in vec3 vertex_world_normal;
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
            visibility += texture(shadow_map, vec3(projected.xy + offset, projected.z - shadow_bias));
        }
    }
    return visibility / 9.0;
}

void main() {
    vec3 surface = use_texture == 1 ? texture(entity_texture, vertex_uv).rgb : vec3(1.0);
    float directional = 0.48 + 0.52
        * max(dot(vertex_world_normal, normalize(light_direction)), 0.0);
    float sky = entity_sky_light * daylight;
    float shadow = mix(0.58, 1.0, sample_shadow());
    float sun_light = sky * directional * shadow;
    float ambient_sky = sky * 0.50;
    float light_level = max(max(sun_light, ambient_sky), max(entity_block_light, 0.10));
    vec3 block_warmth = vec3(1.0, 0.66, 0.34) * entity_block_light * 0.32;
    vec3 lit_color = surface * entity_color * day_tint * light_level;
    lit_color += surface * entity_color * block_warmth;
    frag_color = vec4(lit_color, 1.0);
}
