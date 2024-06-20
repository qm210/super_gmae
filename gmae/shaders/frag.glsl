#version 330 core
out vec4 out_color;

uniform sampler2D iPixelData;
uniform vec2 iResolution;
uniform float iTime;

#define PI 3.14159265358979323846
vec3 c = vec3(1., 0., -1.);

float iAspectRatio = iResolution.x / iResolution.y;

float rand(vec2 c){
	return fract(sin(dot(c.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

float somewhat_random(float x) {
    return rand(vec2(x, x + 0.5));
}

float noise(vec2 p, float freq ){
	float unit = iResolution.x/freq;
	vec2 ij = floor(p/unit);
	vec2 xy = mod(p,unit)/unit;
	//xy = 3.*xy*xy-2.*xy*xy*xy;
	xy = .5*(1.-cos(PI*xy));
	float a = rand((ij+vec2(0.,0.)));
	float b = rand((ij+vec2(1.,0.)));
	float c = rand((ij+vec2(0.,1.)));
	float d = rand((ij+vec2(1.,1.)));
	float x1 = mix(a, b, xy.x);
	float x2 = mix(c, d, xy.x);
	return mix(x1, x2, xy.y);
}

float pNoise(vec2 p, int res){
	float persistance = .5;
	float n = 0.;
	float normK = 0.;
	float f = 4.;
	float amp = 1.;
	int iCount = 0;
	for (int i = 0; i<50; i++){
		n+=amp*noise(p, f);
		f*=2.;
		normK+=amp;
		amp*=persistance;
		if (iCount == res) break;
		iCount++;
	}
	float nf = n/normK;
	return nf*nf*nf*nf;
}

vec2 random_vec(float x) {
    return vec2(
		4. * noise(vec2(x, x + 0.5), 2. * iResolution.x) - 2.,
		2. * noise(vec2(x-0.3, x + 0.1), 2. * iResolution.y) - 1.
	);
}

void main()
{
    // image coordinates are:
    // TOP: y=0, BOTTOM: y=1, LEFT: x=0, RIGHT: x=1
    vec2 image_coord = vec2(
        gl_FragCoord.x / iResolution.x,
        1. - gl_FragCoord.y / iResolution.y
    );

	// some global distortion (vertical wave)
	// image_coord.x += 0.2 * cos(2. * image_coord.y - 0.08 * iTime);

	float pixelizor_scale = 0.01 + 0.0025 * cos(iTime * 0.82);
	float distance_to_center = distance(image_coord, 0.5 * iResolution);
	float pd = pixelizor_scale * (exp(-0.5 * distance_to_center));
	pd = 0.002 * (1. + sin(iTime));
	image_coord = floor(image_coord / pd) * pd;

    vec3 col = texture(iPixelData, image_coord).xyz;

    // and some neighbor, for Schabernack
    vec3 col_offset = texture(iPixelData, image_coord + vec2(0.003)).xyz;

    // for our postprocessing, it might make more sense to have
    // CENTER = (0,0), TOP=1, BOTTOM=-1 and LEFT/RIGHT according to pixel ratio
    vec2 uv = gl_FragCoord.xy / iResolution.y - vec2(0.5 * iAspectRatio, 0.5);

    // this is upside down:
    // uv = gl_FragCoord.xy / iResolution.xy;

    // sine wave distortion
    //uv.x += 0.8 * sin(2. * 3.141593 * 10. * iTime * (1. + 3. * uv.y));

    float r = col.x;

    float scan_pos = 2. * mod(0.1 * iTime, 1.) - 1.;
    float scan_distance = abs(uv.x * (1. + 3. * uv.y) - scan_pos);
    float scan_strength = exp(-.1 * scan_distance * scan_distance);
    col.y = col.z - scan_strength * col.y;

    // some funny colorizations based on a very stupid condition
    /*
    if (abs(col.z - 0.32 - 0.04 * sin(uv.x)) < 0.02) {
        col.x = 1.;
        col.z = 1.;
    }
    */

    vec3 annoying_offset = clamp(
        col_offset * col_offset.x * col_offset,
        0., 1.
    );
    col = max(col, annoying_offset);

    vec2 bobble_center = 0.3 * random_vec(0.43 * iTime);
	float bobble_distance = distance(uv, bobble_center);
	float bobble_size = 13.5 + 7. * sin(iTime) * sin(3. * iTime + 0.2) + uv.y * cos(0.23 * iTime + 0.01);
	col.y += exp(-bobble_size * bobble_distance * bobble_distance);

    out_color = vec4(clamp(col, c.yyy, c.xxx), 1.0);
}
