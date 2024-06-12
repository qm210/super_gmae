#version 330 core
out vec4 out_color;

uniform sampler2D iPixelData;
uniform vec2 iResolution;
uniform float iTime;

vec3 c = vec3(1., 0., -1.);

float iAspectRatio = iResolution.x / iResolution.y;

void main()
{
    // image coordinates are:
    // TOP: y=0, BOTTOM: y=1, LEFT: x=0, RIGHT: x=1
    vec2 image_coord = vec2(
        gl_FragCoord.x / iResolution.x,
        1. - gl_FragCoord.y / iResolution.y
    );
    vec3 col = texture(iPixelData, image_coord).xyz;

    // and some neighbor, for Schabernack
    vec3 col_offset = texture(iPixelData, image_coord + vec2(0.003)).xyz;

    // for our postprocessing, it might make more sense to have
    // CENTER = (0,0), TOP=1, BOTTOM=-1 and LEFT/RIGHT according to pixel ratio
    vec2 uv = gl_FragCoord.xy / iResolution.y - vec2(0.5 * iAspectRatio, 0.5);

    // this is upside down:
    // uv = gl_FragCoord.xy / iResolution.xy;

    // sine wave distortion
    uv.x += 0.8 * sin(2. * 3.141593 * 10. * iTime * (1. + 3. * uv.y));

    float r = col.x;

    float scan_pos = 2. * mod(0.1 * iTime, 1.) - 1.;
    float scan_distance = abs(uv.x * (1. + 3. * uv.y) - scan_pos);
    float scan_strength = exp(-.1 * scan_distance * scan_distance);
    col.y = col.z - scan_strength * col.y;

    // some funny colorizations based on a very stupid condition
    if (abs(col.z - 0.32 - 0.04 * sin(uv.x)) < 0.02) {
        col.x = 1.;
        col.z = 1.;
    }

    // was the first basic test: one bright cyan to annoy them all
    // col = vec3(0.0, 1.0, 1.0);

    vec3 annoying_offset = clamp(
        col_offset * col_offset.x * col_offset,
        0., 1.
    );
    col = max(col, annoying_offset);

    out_color = vec4(clamp(col, c.yyy, c.xxx), 1.0);
}
