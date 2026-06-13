#version 330 core

uniform sampler2D texture_atlas;
uniform vec3 camera_position;
uniform vec3 day_tint;
uniform vec3 fog_color;
uniform float daylight;
uniform float fog_start;
uniform float fog_end;
uniform int fog_enabled;

in vec2 vertex_uv;
in float vertex_directional;
in float vertex_sky_light;
in float vertex_block_light;
in float vertex_ao;
in vec3 vertex_world_position;
in vec4 vertex_atlas_rect;

out vec4 frag_color;

void main() {
    vec2 tile_uv = fract(vertex_uv);
    vec3 block_cell = floor(vertex_world_position + vec3(0.001));
    float variation = fract(sin(dot(block_cell, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
    if (variation > 0.5) {
        tile_uv.x = 1.0 - tile_uv.x;
    }
    if (variation > 0.75 || variation < 0.25) {
        tile_uv.y = 1.0 - tile_uv.y;
    }
    vec2 atlas_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, tile_uv);
    vec4 base_color = texture(texture_atlas, atlas_uv);
    float sky = vertex_sky_light * daylight;
    float light_level = max(max(sky, vertex_block_light), 0.07);
    vec3 block_warmth = vec3(1.0, 0.66, 0.34) * vertex_block_light * 0.32;
    vec3 lit_color = base_color.rgb * day_tint * light_level * vertex_directional * vertex_ao;
    lit_color += base_color.rgb * block_warmth * vertex_ao;
    float distance_to_camera = length(vertex_world_position - camera_position);
    float fog_factor = fog_enabled == 1
        ? smoothstep(fog_start, max(fog_start + 0.1, fog_end), distance_to_camera)
        : 0.0;
    frag_color = vec4(mix(lit_color, fog_color, fog_factor), base_color.a);
}
