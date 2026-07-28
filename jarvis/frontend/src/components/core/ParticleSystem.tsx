import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useJarvisStore } from '../../store/jarvisStore';

const PARTICLE_COUNT = 2000;
const LINE_NODE_COUNT = 150; // Subset of particles used for connecting lines to maintain 60fps

export function ParticleSystem() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const linesRef = useRef<THREE.LineSegments>(null);
  const aiState = useJarvisStore((s) => s.aiState);
  
  // Store initial particle data
  const particles = useMemo(() => {
    const temp = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const r = 2.5 + Math.random() * 2.5;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);
      
      temp.push({
        position: new THREE.Vector3(x, y, z),
        baseRadius: r,
        angle: Math.random() * Math.PI * 2,
        speed: (Math.random() - 0.5) * 0.02,
        offsetY: Math.random() * Math.PI * 2,
        axis: new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize(),
        isNode: i < LINE_NODE_COUNT
      });
    }
    return temp;
  }, []);

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colorDummy = useMemo(() => new THREE.Color(), []);
  const colorArray = useMemo(() => new Float32Array(PARTICLE_COUNT * 3), []);
  
  // Pre-allocate buffer for lines (max 500 lines)
  const linePositions = useMemo(() => new Float32Array(1500 * 6), []);
  const lineColors = useMemo(() => new Float32Array(1500 * 6), []);

  useEffect(() => {
    if (!meshRef.current) return;
    
    // Initialize colors
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      colorDummy.setHSL(0.55 + Math.random() * 0.1, 0.8, 0.5 + Math.random() * 0.5);
      colorDummy.toArray(colorArray, i * 3);
    }
    meshRef.current.instanceColor = new THREE.InstancedBufferAttribute(colorArray, 3);
  }, []);

  useFrame((state) => {
    if (!meshRef.current || !linesRef.current) return;
    
    const time = state.clock.elapsedTime;
    
    // Adjust speed and radius based on AI State
    let speedMult = 1.0;
    let radiusPull = 0;
    
    if (aiState === 'listening') {
      radiusPull = -0.5;
      speedMult = 1.5;
    } else if (aiState === 'thinking') {
      speedMult = 2.5;
    } else if (aiState === 'executing') {
      speedMult = 4.0;
      radiusPull = Math.sin(time * 5) * 0.5;
    } else if (aiState === 'error') {
      speedMult = 5.0;
    }

    const nodePositions: THREE.Vector3[] = [];

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const p = particles[i];
      
      // Orbit mechanics
      p.angle += p.speed * speedMult;
      const radius = p.baseRadius + radiusPull;
      
      dummy.position.copy(p.position).normalize().multiplyScalar(radius);
      dummy.position.applyAxisAngle(p.axis, p.speed * speedMult);
      p.position.copy(dummy.position);
      
      dummy.position.y += Math.sin(time * 2.0 + p.offsetY) * 0.2;
      
      const scale = 0.02 + Math.max(0, Math.sin(time * 3.0 + i)) * 0.02;
      dummy.scale.set(scale, scale, scale);
      
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      if (p.isNode) {
        nodePositions.push(dummy.position.clone());
      }
    }
    
    meshRef.current.instanceMatrix.needsUpdate = true;
    meshRef.current.rotation.y = time * 0.05;
    
    // Update lines
    let lineIdx = 0;
    let maxDist = aiState === 'thinking' || aiState === 'executing' ? 2.5 : 1.5;
    
    // Base color for lines based on state
    const baseColor = new THREE.Color(
      aiState === 'thinking' ? 0x7c3aed : 
      aiState === 'error' ? 0xef4444 : 
      0x00d4ff
    );

    for (let i = 0; i < nodePositions.length; i++) {
      for (let j = i + 1; j < nodePositions.length; j++) {
        const dist = nodePositions[i].distanceTo(nodePositions[j]);
        if (dist < maxDist && lineIdx < 1500) {
          const alpha = 1.0 - (dist / maxDist);
          
          linePositions[lineIdx * 6] = nodePositions[i].x;
          linePositions[lineIdx * 6 + 1] = nodePositions[i].y;
          linePositions[lineIdx * 6 + 2] = nodePositions[i].z;
          linePositions[lineIdx * 6 + 3] = nodePositions[j].x;
          linePositions[lineIdx * 6 + 4] = nodePositions[j].y;
          linePositions[lineIdx * 6 + 5] = nodePositions[j].z;
          
          lineColors[lineIdx * 6] = baseColor.r;
          lineColors[lineIdx * 6 + 1] = baseColor.g;
          lineColors[lineIdx * 6 + 2] = baseColor.b;
          lineColors[lineIdx * 6 + 3] = baseColor.r;
          lineColors[lineIdx * 6 + 4] = baseColor.g;
          lineColors[lineIdx * 6 + 5] = baseColor.b;
          
          lineIdx++;
        }
      }
    }
    
    const geom = linesRef.current.geometry as THREE.BufferGeometry;
    geom.setDrawRange(0, lineIdx * 2);
    geom.attributes.position.needsUpdate = true;
    geom.attributes.color.needsUpdate = true;
    
    linesRef.current.rotation.y = time * 0.05;
  });

  return (
    <group>
      <instancedMesh ref={meshRef} args={[undefined, undefined, PARTICLE_COUNT]}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshBasicMaterial 
          color={0xffffff} 
          transparent 
          opacity={0.6}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </instancedMesh>
      
      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
          <bufferAttribute attach="attributes-color" args={[lineColors, 3]} />
        </bufferGeometry>
        <lineBasicMaterial 
          vertexColors 
          transparent 
          opacity={0.15} 
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>
    </group>
  );
}