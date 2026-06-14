#version 330 core

uniform mat4 light_matrix;
uniform vec3 section_origin;

in vec3 in_position;

void main() {
    gl_Position = light_matrix * vec4(in_position + section_origin, 1.0);
}
