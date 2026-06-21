#version 330 core

in vec3 in_position;
in vec3 in_normal;

uniform vec3 part_position;
uniform vec3 part_scale;
uniform vec3 part_rotation_degrees;
uniform float aspect_ratio;

out vec3 v_normal;

mat3 rotate_x(float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return mat3(
        1.0, 0.0, 0.0,
        0.0, c, -s,
        0.0, s, c
    );
}

mat3 rotate_y(float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return mat3(
        c, 0.0, s,
        0.0, 1.0, 0.0,
        -s, 0.0, c
    );
}

mat3 rotate_z(float angle) {
    float c = cos(angle);
    float s = sin(angle);
    return mat3(
        c, -s, 0.0,
        s, c, 0.0,
        0.0, 0.0, 1.0
    );
}

void main() {
    vec3 radians_rotation = radians(part_rotation_degrees);
    mat3 rotation =
        rotate_z(radians_rotation.z) *
        rotate_y(radians_rotation.y) *
        rotate_x(radians_rotation.x);
    vec3 local_position = rotation * (in_position * part_scale);
    vec3 clip_position = part_position + local_position;
    clip_position.x /= max(aspect_ratio, 0.001);
    gl_Position = vec4(clip_position, 1.0);
    v_normal = normalize(rotation * in_normal);
}
