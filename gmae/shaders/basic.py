# Load shaders
vertex_shader_source = """
#version 330 core
layout (location = 0) in vec3 aPos;

void main()
{
   gl_Position = vec4(aPos, 1.0);
}
"""

fragment_shader_source = """
#version 330 core
out vec4 FragColor;

uniform sampler2D textureSampler;
uniform vec2 iResolution;

void main()
{
    FragColor = vec4(0.5, 1.0, 1.0, 1.0);  
    // FragColor = texture(textureSampler, TexCoords);
}
"""
