#version 330 core

uniform vec3 entity_color;

in float vertex_shade;

out vec4 frag_color;

void main() {
    frag_color = vec4(entity_color * vertex_shade, 1.0);
}
