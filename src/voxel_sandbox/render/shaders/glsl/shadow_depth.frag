#version 330 core

uniform sampler2D texture_atlas;

in vec2 vertex_uv;
in vec4 vertex_atlas_rect;

void main() {
    vec2 atlas_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, fract(vertex_uv));
    if (texture(texture_atlas, atlas_uv).a < 0.5) {
        discard;
    }
}
