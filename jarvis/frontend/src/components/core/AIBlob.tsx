import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useJarvisStore } from '../../store/jarvisStore';
import * as THREE from 'three';

export function AIBlob() {
  const coreRef = useRef<THREE.Mesh>(null);
  const innerRingRef = useRef<THREE.Mesh>(null);
  const midMeshRef = useRef<THREE.Mesh>(null);
  const outerRingRef = useRef<THREE.Group>(null);
  const groupRef = useRef<THREE.Group>(null);
  
  const aiState = useJarvisStore((s) => s.aiState);
  const alertActive = useJarvisStore((s) => s.alertActive);

  // Materials
  const coreMaterial = useMemo(() => new THREE.MeshBasicMaterial({ 
    color: 0xffffff,
    transparent: true,
    opacity: 0.9
  }), []);

  const innerMaterial = useMemo(() => new THREE.MeshBasicMaterial({ 
    color: 0x00d2ff, 
    wireframe: true,
    transparent: true,
    opacity: 0.8
  }), []);

  const midMaterial = useMemo(() => new THREE.MeshBasicMaterial({ 
    color: 0x0088ff, 
    wireframe: true,
    transparent: true,
    opacity: 0.3
  }), []);

  const outerMaterial = useMemo(() => new THREE.MeshBasicMaterial({ 
    color: 0x00aaff,
    transparent: true,
    opacity: 0.5
  }), []);

  useFrame((state) => {
    if (!groupRef.current || !innerRingRef.current || !midMeshRef.current || !coreRef.current) return;
    
    const isAlert = alertActive || aiState === 'error';
    const isThinking = aiState === 'thinking' || aiState === 'executing';
    
    // Update colors
    const targetColor = isAlert ? new THREE.Color(0xff0000) : new THREE.Color(0x00d2ff);
    const midColor = isAlert ? new THREE.Color(0xff0000) : new THREE.Color(0x0088ff);
    const outerColor = isAlert ? new THREE.Color(0xff3333) : new THREE.Color(0x00aaff);
    
    innerMaterial.color.lerp(targetColor, 0.1);
    midMaterial.color.lerp(midColor, 0.1);
    outerMaterial.color.lerp(outerColor, 0.1);

    // Speed calculation
    const baseRotationSpeed = 0.01;
    const currentSpeed = isThinking ? baseRotationSpeed * 5 : baseRotationSpeed;
    
    // Rotate elements
    groupRef.current.rotation.z -= currentSpeed;
    innerRingRef.current.rotation.x += currentSpeed * 2;
    innerRingRef.current.rotation.y += currentSpeed * 2;
    midMeshRef.current.rotation.x -= currentSpeed;
    midMeshRef.current.rotation.y += currentSpeed * 1.5;
    
    // Core pulsing effect
    const time = state.clock.elapsedTime;
    const pulse = Math.sin(time * (isThinking ? 10 : 2)) * 0.1 + 1;
    coreRef.current.scale.set(pulse, pulse, pulse);
  });

  return (
    <group ref={groupRef}>
      {/* 1. Center Core (Glowing Sphere) */}
      <mesh ref={coreRef} material={coreMaterial}>
        <sphereGeometry args={[1, 32, 32]} />
      </mesh>

      {/* 2. Inner Ring (Wireframe Torus) */}
      <mesh ref={innerRingRef} material={innerMaterial}>
        <torusGeometry args={[1.8, 0.1, 16, 100]} />
      </mesh>

      {/* 3. Middle Geometry (Icosahedron) */}
      <mesh ref={midMeshRef} material={midMaterial}>
        <icosahedronGeometry args={[2.5, 1]} />
      </mesh>

      {/* 4. Outer Ring */}
      <group ref={outerRingRef}>
        <mesh material={outerMaterial}>
          <torusGeometry args={[3.5, 0.05, 16, 100]} />
        </mesh>
      </group>
    </group>
  );
}