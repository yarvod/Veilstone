#version 330 core

uniform mat4 camera_matrix;
uniform vec3 block_origin;

in vec3 in_position;

void main() {
    vec3 expanded = (in_position - vec3(0.5)) * 1.004 + vec3(0.5);
    gl_Position = camera_matrix * vec4(expanded + block_origin, 1.0);
}
