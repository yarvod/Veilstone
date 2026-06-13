#version 330 core

uniform mat4 camera_matrix;

in vec3 in_position;
in vec2 in_uv;
in vec3 in_normal;

out vec2 vertex_uv;
out float vertex_light;

void main() {
    vec3 sun_direction = normalize(vec3(0.4, 0.8, 0.25));
    vertex_uv = in_uv;
    vertex_light = 0.35 + 0.65 * max(dot(in_normal, sun_direction), 0.0);
    gl_Position = camera_matrix * vec4(in_position, 1.0);
}
