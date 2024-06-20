#version 330 core
out vec4 out_color;

uniform sampler2D iPixelData;
uniform vec2 iResolution;

vec3 c = vec3(1., 0., -1.);

void main()
{
    // image coordinates are:
    // TOP: y=0, BOTTOM: y=1, LEFT: x=0, RIGHT: x=1
    vec2 image_coord = vec2(
        gl_FragCoord.x / iResolution.x,
        1. - gl_FragCoord.y / iResolution.y
    );

    vec3 col = texture(iPixelData, image_coord).xyz;

    out_color = vec4(clamp(col, c.yyy, c.xxx), 1.0);

    // was the first basic test: one bright cyan to annoy them all
    // out_color = vec3(0.0, 1.0, 1.0, 1.0);
}
