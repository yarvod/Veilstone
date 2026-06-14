#version 330 core

uniform sampler2D scene_color;

in vec2 screen_uv;
out vec4 frag_color;

void main() {
    vec3 color = texture(scene_color, screen_uv).rgb;
    color = color / (color + vec3(1.0));
    color = pow(color, vec3(1.0 / 2.2));
    vec2 centered = screen_uv * 2.0 - 1.0;
    float vignette = 1.0 - smoothstep(0.45, 1.35, dot(centered, centered));
    color *= mix(0.82, 1.0, vignette);
    frag_color = vec4(color, 1.0);
}
