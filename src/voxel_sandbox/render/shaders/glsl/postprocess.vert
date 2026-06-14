#version 330 core

out vec2 screen_uv;

void main() {
    vec2 position = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    screen_uv = position;
    gl_Position = vec4(position * 2.0 - 1.0, 0.0, 1.0);
}
