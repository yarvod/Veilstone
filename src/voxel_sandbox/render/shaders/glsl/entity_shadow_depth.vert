#version 330 core

uniform mat4 light_matrix;
uniform vec3 entity_position;
uniform float entity_yaw;
uniform vec3 part_offset;
uniform vec3 part_scale;
uniform vec3 part_pivot;
uniform vec3 part_rotation;

in vec3 in_position;

vec3 rotate_part(vec3 value) {
    float cx = cos(part_rotation.x); float sx = sin(part_rotation.x);
    float cy = cos(part_rotation.y); float sy = sin(part_rotation.y);
    float cz = cos(part_rotation.z); float sz = sin(part_rotation.z);
    value.yz = mat2(cx, sx, -sx, cx) * value.yz;
    value.xz = mat2(cy, -sy, sy, cy) * value.xz;
    value.xy = mat2(cz, sz, -sz, cz) * value.xy;
    return value;
}

void main() {
    vec3 pivot = part_pivot * part_scale;
    vec3 local = rotate_part(in_position * part_scale - pivot) + pivot + part_offset;
    local.xz = mat2(cos(entity_yaw), sin(entity_yaw), -sin(entity_yaw), cos(entity_yaw)) * local.xz;
    gl_Position = light_matrix * vec4(entity_position + local, 1.0);
}
