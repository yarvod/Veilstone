#version 330 core

uniform sampler2D texture_atlas;

in vec2 vertex_uv;
in float vertex_light;

out vec4 frag_color;

void main() {
    vec4 base_color = texture(texture_atlas, vertex_uv);
    frag_color = vec4(base_color.rgb * vertex_light, base_color.a);
}
