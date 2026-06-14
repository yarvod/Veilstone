#version 330 core

uniform sampler2D entity_texture;
uniform vec3 entity_color;
uniform int use_texture;

in vec2 vertex_uv;
in float vertex_shade;

out vec4 frag_color;

void main() {
    vec3 surface = use_texture == 1 ? texture(entity_texture, vertex_uv).rgb : vec3(1.0);
    frag_color = vec4(surface * entity_color * vertex_shade, 1.0);
}
