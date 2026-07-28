varying vec2 vUv;
varying vec3 vPosition;
varying vec3 vNormal;
varying vec3 vViewPosition;

uniform float uTime;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform float uFresnelPower;
uniform float uGlowStrength;
uniform vec3 uMouseDirection;

void main() {
  vec3 viewDir = normalize(vViewPosition);
  vec3 normal = normalize(vNormal);
  
  // Fresnel effect for glassy edge glow
  float fresnel = dot(viewDir, normal);
  fresnel = clamp(1.0 - fresnel, 0.0, 1.0);
  fresnel = pow(fresnel, uFresnelPower);
  
  // Mix colors based on position and time
  float mixVal = smoothstep(-1.0, 1.0, vPosition.y + sin(vPosition.x * 2.0 + uTime) * 0.5);
  vec3 baseColor = mix(uColor1, uColor2, mixVal);
  
  // Add light from mouse direction
  float mouseGlow = dot(normal, normalize(uMouseDirection)) * 0.5 + 0.5;
  mouseGlow = pow(mouseGlow, 2.0) * 0.3;
  
  // Volumetric glow
  float glow = fresnel * uGlowStrength + mouseGlow;
  
  vec3 finalColor = baseColor + vec3(glow);
  
  // Slight chromatic aberration at edges
  float r = baseColor.r + fresnel * 0.5;
  float g = baseColor.g + fresnel * 0.2;
  float b = baseColor.b + fresnel * 0.8;
  
  vec3 caColor = vec3(r, g, b);
  finalColor = mix(finalColor, caColor, fresnel * 0.5);
  
  gl_FragColor = vec4(finalColor, 0.85 + fresnel * 0.15);
}