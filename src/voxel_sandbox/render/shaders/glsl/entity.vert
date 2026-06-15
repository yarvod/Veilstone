#version 330 core

uniform mat4 camera_matrix;
uniform vec3 entity_position;
uniform float entity_yaw;
uniform vec3 part_offset;
uniform vec3 part_scale;
uniform vec3 part_pivot;
uniform vec3 part_rotation;
uniform vec4 texture_rect_front;
uniform vec4 texture_rect_back;
uniform vec4 texture_rect_left;
uniform vec4 texture_rect_right;
uniform vec4 texture_rect_top;
uniform vec4 texture_rect_bottom;
uniform mat4 shadow_matrix;

in vec3 in_position;
in vec2 in_uv;
in float in_face;
in vec3 in_normal;

out vec2 vertex_uv;
out vec3 vertex_world_normal;
out vec4 vertex_shadow_position;

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
    mat2 yaw_rotation = mat2(
        cos(entity_yaw), sin(entity_yaw),
        -sin(entity_yaw), cos(entity_yaw)
    );
    local.xz = yaw_rotation * local.xz;
    vec3 normal = rotate_part(in_normal);
    normal.xz = yaw_rotation * normal.xz;
    vec4 texture_rect = texture_rect_front;
    int face = int(in_face + 0.5);
    if (face == 1) texture_rect = texture_rect_back;
    else if (face == 2) texture_rect = texture_rect_left;
    else if (face == 3) texture_rect = texture_rect_right;
    else if (face == 4) texture_rect = texture_rect_top;
    else if (face == 5) texture_rect = texture_rect_bottom;
    vertex_uv = texture_rect.xy + in_uv * texture_rect.zw;
    vec3 world_position = entity_position + local;
    vertex_world_normal = normalize(normal);
    vertex_shadow_position = shadow_matrix * vec4(world_position, 1.0);
    gl_Position = camera_matrix * vec4(world_position, 1.0);
}
