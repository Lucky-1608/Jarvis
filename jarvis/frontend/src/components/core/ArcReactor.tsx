import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useJarvisStore } from '../../store/jarvisStore';
import * as THREE from 'three';

export function ArcReactor() {
  const groupRef = useRef<THREE.Group>(null);
  const innerRingRef = useRef<THREE.Mesh>(null);
  const midMeshRef = useRef<THREE.Mesh>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  const aiState = useJarvisStore((s) => s.aiState);
  const alertActive = useJarvisStore((s) => s.alertActive);

  // Colors
  const normalColor = useMemo(() => new THREE.Color(0x00d2ff), []);
  const alertColor = useMemo(() => new THREE.Color(0xff0000), []);
  const midNormalColor = useMemo(() => new THREE.Color(0x0088ff), []);
  const outerNormalColor = useMemo(() => new THREE.Color(0x00aaff), []);

  const isThinking = aiState === 'thinking';
  const baseRotationSpeed = 0.01;

  useFrame(({ clock }) => {
    if (!groupRef.current || !innerRingRef.current || !midMeshRef.current || !coreRef.current) return;

    const currentSpeed = isThinking ? baseRotationSpeed * 5 : baseRotationSpeed;

    groupRef.current.rotation.z -= currentSpeed;
    innerRingRef.current.rotation.x += currentSpeed * 2;
    innerRingRef.current.rotation.y += currentSpeed * 2;
    midMeshRef.current.rotation.x -= currentSpeed;
    midMeshRef.current.rotation.y += currentSpeed * 1.5;

    const time = clock.getElapsedTime();
    const pulse = Math.sin(time * (isThinking ? 10 : 2)) * 0.1 + 1;
    coreRef.current.scale.set(pulse, pulse, pulse);
  });

  return (
    <group ref={groupRef} scale={0.5}>
      {/* 1. Center Core (Glowing Sphere) */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial 
          color={alertActive ? alertColor : 0xffffff} 
          transparent 
          opacity={0.9} 
        />
      </mesh>

      {/* 2. Inner Ring (Wireframe Torus) */}
      <mesh ref={innerRingRef}>
        <torusGeometry args={[1.8, 0.1, 16, 100]} />
        <meshBasicMaterial 
          color={alertActive ? alertColor : normalColor} 
          wireframe 
          transparent 
          opacity={0.8} 
        />
      </mesh>

      {/* 3. Middle Geometry (Icosahedron) */}
      <mesh ref={midMeshRef}>
        <icosahedronGeometry args={[2.5, 1]} />
        <meshBasicMaterial 
          color={alertActive ? alertColor : midNormalColor} 
          wireframe 
          transparent 
          opacity={0.3} 
        />
      </mesh>

      {/* 4. Outer Ring (Dashed Torus or Particles) */}
      <mesh>
        <torusGeometry args={[3.5, 0.05, 16, 100]} />
        <meshBasicMaterial 
          color={alertActive ? alertColor : outerNormalColor} 
          transparent 
          opacity={0.5} 
        />
      </mesh>
    </group>
  );
}
