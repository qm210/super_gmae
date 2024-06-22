#version 330 core
out vec4 out_color;

uniform sampler2D iPixelData;
uniform vec2 iResolution;
uniform float iTime;
uniform float aEffectA;
uniform float aEffectB;
uniform float aEffectC;
uniform float aEffectD;
uniform float aEffectGreenBlob;

const float pi = 3.14159265358979323846;
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
	xy = .5*(1.-cos(pi *xy));
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

//////////////////////// https://www.shadertoy.com/view/M3cSzH

float hash12(vec2 p)
{
	vec3 p3  = fract(vec3(p.xyx) * .1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

// Low-Frequency noise (value-type)
float lfnoise(vec2 t)
{
    vec2 i = floor(t);
    t = fract(t);
    t = smoothstep(c.yy, c.xx, t);
    vec2 v1 = vec2(hash12(i), hash12(i+c.xy)),
        v2 = vec2(hash12(i+c.yx), hash12(i+c.xx));
    v1 = c.zz+2.*mix(v1, v2, t.y);
    return mix(v1.x, v1.y, t.x);
}

// Convert RGB to HSV
vec3 rgb2hsv(vec3 cc)
{
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(cc.bg, K.wz), vec4(cc.gb, K.xy), step(cc.b, cc.g));
    vec4 q = mix(vec4(p.xyw, cc.r), vec4(cc.r, p.yzx), step(p.x, cc.r));

    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

// Convert HSV to RGB
vec3 hsv2rgb(vec3 cc)
{
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(cc.xxx + K.xyz) * 6.0 - K.www);
    return cc.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), cc.y);
}

void effectA(inout vec3 col, in vec3 orig_col, in vec2 uv)
{
    vec3 c1 = rgb2hsv(col);
    c1.r = mod(c1.r - lfnoise(.3 * iTime * c.xx), 2. * pi);
    col = mix(
        col,
        hsv2rgb(c1),
        aEffectA
    );
}

//////////////////////// https://www.shadertoy.com/view/lXcSzH (blur)

const float gold = 2.4;

void blur(out vec3 fragColor, vec2 fragCoord) {
    vec2 uv = (fragCoord - .5 * iResolution.xy) / iResolution.y,
        unit = 1./iResolution.xy,
        uvn = fragCoord * unit;

    // Vogel-ordered Gauss DOF.
    vec3 col = c.yyy;
    float sampleCount = 432.;
    for(float i = .5; i < sampleCount; i += 1.) {
        float x = i / sampleCount;
        float p = gold * i;
        vec2 z =
            // Pixel size.
            2. / iResolution.y
            // Vogel order.
            * sqrt(x) * vec2(cos(p), sin(p))
            // Adjust width for DOF effect.
            * 62.
            // * (1. + 4.5 * smoothstep(0., 1., 2. * abs(uv.y)))
        ;

        x *= pi * pi;
        col +=
            // Unnormalized Gauss kernel.
            exp( -x / 2.)
            // Remap to texture coordinates.
            * texture(iPixelData, ((uv - z) * iResolution.y + .5 * iResolution.xy) / iResolution.xy).xyz;
    }
    fragColor = col / sampleCount * pi * pi / sqrt(2. * pi) * 1.25;
}

void effectB(inout vec3 col, in vec3 orig_col, in vec2 uv)
{
    vec3 new_col = col;
    blur(new_col, gl_FragCoord.xy);
    col = mix(
        col,
        new_col,
        aEffectB
    );
}

//////////////////////// https://www.shadertoy.com/view/M3cSzH (gamma flicker)

void effectC(inout vec3 col, in vec3 orig_col, in vec2 uv)
{
    col = mix(
        col,
        pow(col, 1. + (1. * (hash12(.7 * floor(4. * iTime) * c.xx))) * c.xxx),
        aEffectC
    );
}

//////////////////////// https://www.shadertoy.com/view/M33XzHb

const float AMOUNT_COLOR = 8.;
const int MAX_LEVEL = 4;

float GetBayerFromCoordLevel(vec2 pixelpos)
{
    ivec2 ppos = ivec2(pixelpos);
    int sum = 0;
    for(int i = 0; i<MAX_LEVEL; i++)
    {
         ivec2 t = ppos & 1;
         sum = sum * 4 | (t.x ^ t.y) * 2 | t.x;
         ppos /= 2;
    }
    return float(sum) / float(1 << (2 * MAX_LEVEL));
}

// Blends the nearest two palette colors with dithering.
float GetDitheredPalette(float x, vec2 pixel)
{
	float idx = clamp(x,0.0,1.0)*AMOUNT_COLOR-1.;

	float c1 = 0.;
	float c2 = 0.;

	c1 = floor(x*AMOUNT_COLOR-1.)/AMOUNT_COLOR;

    c2 =c1+1./(AMOUNT_COLOR);
    float dith = GetBayerFromCoordLevel(pixel);
    float mixAmt = float(fract(idx) > dith);

	return mix(c1,c2,mixAmt);
}

void effectD(inout vec3 col, in vec3 orig_col, in vec2 _uv)
{
    float DOWN_SCALE = 32. * (.001+aEffectD);
    vec2 fragCoord = floor(gl_FragCoord.xy / DOWN_SCALE) * DOWN_SCALE;
	vec2 uv = fragCoord.xy/iResolution.xy;

    float outColor1 = GetDitheredPalette(texture(iPixelData, uv).x, fragCoord / DOWN_SCALE);
    float outColor2 = GetDitheredPalette(texture(iPixelData, uv).y, fragCoord / DOWN_SCALE);
    float outColor3 = GetDitheredPalette(texture(iPixelData, uv).z, fragCoord / DOWN_SCALE);

    vec3 new_col = vec3(outColor1,outColor2,outColor3);
    col = mix(col, new_col, aEffectD);
}

////////////////////////////////////////////////////////////

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
    vec3 orig_col = col;

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
	col.y += aEffectGreenBlob *
        exp(-bobble_size * bobble_distance * bobble_distance);

	effectA(col, orig_col, uv);
    effectB(col, orig_col, uv);
	effectC(col, orig_col, uv);
    effectD(col, orig_col, uv);

    out_color = vec4(clamp(col, c.yyy, c.xxx), 1.0);
}
