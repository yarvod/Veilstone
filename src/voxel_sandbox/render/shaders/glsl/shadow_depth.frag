#version 330 core

uniform sampler2D texture_atlas;
uniform float tile_uv_margin;

in vec2 vertex_uv;
in vec4 vertex_atlas_rect;

void main() {
    vec2 tile_uv = clamp(
        fract(vertex_uv),
        vec2(tile_uv_margin),
        vec2(1.0 - tile_uv_margin)
    );
    vec2 atlas_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, tile_uv);
    if (texture(texture_atlas, atlas_uv).a < 0.5) {
        discard;
    }
}
