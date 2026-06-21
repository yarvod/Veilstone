#version 330 core

in vec3 v_normal;

uniform vec3 part_color;

out vec4 frag_color;

void main() {
    vec3 light_direction = normalize(vec3(-0.35, 0.8, 0.45));
    float light = 0.68 + 0.32 * max(dot(normalize(v_normal), light_direction), 0.0);
    frag_color = vec4(part_color * light, 1.0);
}
