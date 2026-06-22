#version 330 core

in vec3 v_normal;
in vec2 v_uv;

uniform vec3 part_color;
uniform bool use_texture;
uniform sampler2D viewmodel_texture;
uniform vec4 uv_rect;

out vec4 frag_color;

void main() {
    vec3 light_direction = normalize(vec3(-0.35, 0.8, 0.45));
    float light = 0.68 + 0.32 * max(dot(normalize(v_normal), light_direction), 0.0);
    vec3 base_color = part_color;
    if (use_texture) {
        vec2 atlas_uv = mix(uv_rect.xy, uv_rect.zw, v_uv);
        base_color = texture(viewmodel_texture, atlas_uv).rgb;
    }
    frag_color = vec4(base_color * light, 1.0);
}
