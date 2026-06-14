#version 330 core

uniform mat4 light_matrix;
uniform vec3 entity_position;
uniform vec3 entity_scale;
uniform float animation_time;
uniform int is_item;

in vec3 in_position;

void main() {
    vec3 local = in_position * entity_scale;
    if (is_item == 1) {
        float angle = animation_time * 1.8;
        local.xz = mat2(cos(angle), -sin(angle), sin(angle), cos(angle)) * local.xz;
        local.y += 0.12 + sin(animation_time * 2.5 + entity_position.x) * 0.06;
    }
    gl_Position = light_matrix * vec4(entity_position + local, 1.0);
}
