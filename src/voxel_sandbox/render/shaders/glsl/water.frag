#version 330 core

uniform sampler2D texture_atlas;
uniform vec3 camera_position;
uniform vec3 fog_color;
uniform float fog_start;
uniform float fog_end;
uniform int fog_enabled;

in vec2 vertex_uv;
in float vertex_light;
in vec3 vertex_world_position;
in vec4 vertex_atlas_rect;

out vec4 frag_color;

void main() {
    vec2 atlas_uv = mix(vertex_atlas_rect.xy, vertex_atlas_rect.zw, fract(vertex_uv));
    vec4 base_color = texture(texture_atlas, atlas_uv);
    vec3 lit_color = base_color.rgb * vertex_light;
    float distance_to_camera = length(vertex_world_position - camera_position);
    float fog_factor = fog_enabled == 1
        ? smoothstep(fog_start, max(fog_start + 0.1, fog_end), distance_to_camera)
        : 0.0;
    frag_color = vec4(mix(lit_color, fog_color, fog_factor), 0.58);
}
