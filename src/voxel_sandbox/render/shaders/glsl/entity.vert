#version 330 core

uniform mat4 camera_matrix;
uniform vec3 entity_position;
uniform vec3 entity_scale;
uniform float animation_time;
uniform int is_item;

in vec3 in_position;

out float vertex_shade;

void main() {
    vec3 local = in_position * entity_scale;
    if (is_item == 1) {
        float angle = animation_time * 1.8;
        local.xz = mat2(cos(angle), -sin(angle), sin(angle), cos(angle)) * local.xz;
        local.y += 0.12 + sin(animation_time * 2.5 + entity_position.x) * 0.06;
    }
    vertex_shade = 0.72 + in_position.y * 0.28;
    gl_Position = camera_matrix * vec4(entity_position + local, 1.0);
}
