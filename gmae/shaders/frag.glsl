#version 330 core
out vec4 out_color;

uniform sampler2D iPixelData;
uniform vec2 iResolution;
uniform float iTime;

vec3 c = vec3(1., 0., -1.);

void main()
{
    // invert y because different convention...
    float u = gl_FragCoord.x / iResolution.x;
    float v = 1. - gl_FragCoord.y / iResolution.y;
    vec2 uv = vec2(u, v);

    // this is upside down:
    // uv = gl_FragCoord.xy / iResolution.xy;

    // for now: just pass through
    out_color = texture(iPixelData, uv);

    vec3 col = out_color.xyz;
    float r = col.x;
    col.x *= 1.2 * r;
    col.y *= 0.3 * r + 0.6 * sin(2. * 3.141 * 2. * iTime);
    col.z *= 0.3 + 0.6 * sin(2. * 3.141 * 2. * iTime);
    col = clamp(col, c.yyy, c.xxx);

    // basic test: cyan means "all good"
    // out_color = vec4(0.5, 1.0, 1.0, 1.0);
    out_color = vec4(col, 1.0);
}
