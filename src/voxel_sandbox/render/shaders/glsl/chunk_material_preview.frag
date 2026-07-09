#version 330 core

uniform sampler2D texture_atlas;
uniform sampler2D u_material_normal_atlas;
uniform sampler2D u_material_specular_atlas;
uniform sampler2D u_material_emissive_atlas;
uniform sampler2D u_material_mer_atlas;
uniform int u_material_has_normal;
uniform int u_material_has_specular;
uniform int u_material_has_emissive;
uniform int u_material_has_mer;
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
uniform float tile_uv_margin;

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
    float receiver_bias = max(shadow_bias, 0.0015);
    float visibility = 0.0;
    for (int x = -2; x <= 2; ++x) {
        for (int y = -2; y <= 2; ++y) {
            vec2 offset = vec2(x, y) * shadow_texel_size;
            visibility += texture(
                shadow_map,
                vec3(projected.xy + offset, projected.z - receiver_bias)
            );
        }
    }
    float filtered_visibility = visibility / 25.0;
    return filtered_visibility;
}

void main() {
    vec2 tile_uv = clamp(
        fract(vertex_uv),
        vec2(tile_uv_margin),
        vec2(1.0 - tile_uv_margin)
    );
    vec2 atlas_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, tile_uv);
    vec4 base_color = texture(texture_atlas, atlas_uv);
    if (base_color.a < 0.5) {
        discard;
    }

    vec3 normal_sample = u_material_has_normal == 1
        ? texture(u_material_normal_atlas, atlas_uv).rgb * 2.0 - 1.0
        : vec3(0.0, 0.0, 1.0);
    float specular_strength = u_material_has_specular == 1
        ? texture(u_material_specular_atlas, atlas_uv).r
        : 0.0;
    vec3 emissive_color = u_material_has_emissive == 1
        ? texture(u_material_emissive_atlas, atlas_uv).rgb
        : vec3(0.0);
    vec3 mer_sample = u_material_has_mer == 1
        ? texture(u_material_mer_atlas, atlas_uv).rgb
        : vec3(0.0);

    float sky = vertex_sky_light * daylight;
    float shadow = mix(0.48, 1.0, sample_shadow());
    // Zero-mean tangent detail keeps overall brightness matched with
    // chunk_opaque; normals only modulate the sun-facing term.
    float normal_detail = clamp(
        (normal_sample.x + normal_sample.y) * 0.10 + mer_sample.r * 0.04,
        -0.12,
        0.12
    );
    float sun_light = sky * clamp(vertex_directional + normal_detail, 0.0, 1.0) * shadow;
    float ambient_sky = sky * 0.36;
    float light_level = max(max(sun_light, ambient_sky), max(vertex_block_light, 0.12));
    vec3 block_warmth = vec3(1.0, 0.66, 0.34) * vertex_block_light * 0.32;
    float readable_ao = mix(0.72, 1.0, vertex_ao);
    vec3 lit_color = base_color.rgb * day_tint * light_level * readable_ao;
    lit_color += base_color.rgb * block_warmth * readable_ao;
    lit_color += base_color.rgb * specular_strength * sky * shadow * 0.12;
    lit_color += emissive_color * (0.25 + vertex_block_light * 0.5);
    float distance_to_camera = length(vertex_world_position - camera_position);
    float fog_factor = fog_enabled == 1
        ? smoothstep(fog_start, max(fog_start + 0.1, fog_end), distance_to_camera)
        : 0.0;
    frag_color = vec4(mix(lit_color, fog_color, fog_factor), base_color.a);
}
