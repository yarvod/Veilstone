#version 330 core

uniform mat4 camera_matrix;
uniform vec3 section_origin;

in vec3 in_position;
in vec2 in_uv;
in vec3 in_normal;
in float in_light;
in float in_ao;

out vec2 vertex_uv;
out float vertex_light;

void main() {
    vec3 sun_direction = normalize(vec3(0.4, 0.8, 0.25));
    vertex_uv = in_uv;
    float directional = 0.48 + 0.52 * max(dot(in_normal, sun_direction), 0.0);
    vertex_light = max(in_light, 0.08) * directional * in_ao;
    gl_Position = camera_matrix * vec4(in_position + section_origin, 1.0);
}
