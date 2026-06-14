#version 330 core

uniform float aspect_ratio;
uniform float field_of_view;
uniform float yaw;
uniform float pitch;
uniform float daylight;
uniform float time_of_day;
uniform float animation_time;
uniform int clouds_enabled;

in vec2 screen_uv;
out vec4 frag_color;

float hash(vec2 value) {
    return fract(sin(dot(value, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 value) {
    vec2 cell = floor(value);
    vec2 local = fract(value);
    local = local * local * (3.0 - 2.0 * local);
    return mix(
        mix(hash(cell), hash(cell + vec2(1.0, 0.0)), local.x),
        mix(hash(cell + vec2(0.0, 1.0)), hash(cell + 1.0), local.x),
        local.y
    );
}

vec3 camera_ray() {
    vec2 ndc = screen_uv * 2.0 - 1.0;
    float scale = tan(radians(field_of_view) * 0.5);
    vec3 ray = normalize(vec3(1.0, ndc.y * scale, ndc.x * aspect_ratio * scale));
    float cp = cos(pitch);
    float sp = sin(pitch);
    ray = vec3(
        cp * ray.x - sp * ray.y,
        sp * ray.x + cp * ray.y,
        ray.z
    );
    float cy = cos(yaw);
    float sy = sin(yaw);
    return normalize(vec3(
        cy * ray.x - sy * ray.z,
        ray.y,
        sy * ray.x + cy * ray.z
    ));
}

void main() {
    vec3 ray = camera_ray();
    float horizon = smoothstep(-0.18, 0.45, ray.y);
    vec3 day_horizon = vec3(0.62, 0.72, 0.82);
    vec3 day_zenith = vec3(0.12, 0.30, 0.58);
    vec3 night_horizon = vec3(0.035, 0.045, 0.095);
    vec3 night_zenith = vec3(0.006, 0.010, 0.032);
    vec3 day_color = mix(day_horizon, day_zenith, horizon);
    vec3 night_color = mix(night_horizon, night_zenith, horizon);
    vec3 color = mix(night_color, day_color, daylight);

    float angle = time_of_day * 6.28318530718;
    vec3 sun_direction = normalize(vec3(cos(angle), sin(angle), 0.28));
    vec3 moon_direction = -sun_direction;
    float sun = smoothstep(0.9991, 0.99975, dot(ray, sun_direction));
    float sun_glow = pow(max(dot(ray, sun_direction), 0.0), 96.0);
    float moon = smoothstep(0.9993, 0.99982, dot(ray, moon_direction));
    color += vec3(1.0, 0.72, 0.30) * (sun * 1.8 + sun_glow * 0.32) * daylight;
    color += vec3(0.58, 0.68, 0.92) * moon * (1.0 - daylight * 0.7);

    if (clouds_enabled == 1 && ray.y > 0.08) {
        vec2 cloud_position = ray.xz / max(ray.y, 0.08) * 0.65;
        cloud_position += vec2(animation_time * 0.006, animation_time * 0.003);
        float cloud_noise = noise(cloud_position * 1.7) * 0.65;
        cloud_noise += noise(cloud_position * 3.4) * 0.35;
        float cloud = smoothstep(0.56, 0.72, cloud_noise) * smoothstep(0.08, 0.24, ray.y);
        vec3 cloud_color = mix(vec3(0.22, 0.25, 0.34), vec3(0.88, 0.90, 0.92), daylight);
        color = mix(color, cloud_color, cloud * 0.72);
    }
    frag_color = vec4(color, 1.0);
}
