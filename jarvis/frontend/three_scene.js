import * as THREE from 'three';

let scene, camera, renderer;
let arcGroup;
let isThinking = false;
let baseRotationSpeed = 0.01;

export function initThreeScene(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Scene setup
  scene = new THREE.Scene();
  
  // Camera setup
  const width = container.clientWidth || 400;
  const height = container.clientHeight || 400;
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.z = 10;

  // Renderer setup
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.insertBefore(renderer.domElement, container.firstChild); // Insert before status text

  // Group to hold all reactor parts
  arcGroup = new THREE.Group();
  scene.add(arcGroup);

  // 1. Center Core (Glowing Sphere)
  const coreGeometry = new THREE.SphereGeometry(1, 32, 32);
  const coreMaterial = new THREE.MeshBasicMaterial({ 
    color: 0xffffff,
    transparent: true,
    opacity: 0.9
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  arcGroup.add(core);

  // 2. Inner Ring (Wireframe Torus)
  const innerGeometry = new THREE.TorusGeometry(1.8, 0.1, 16, 100);
  const innerMaterial = new THREE.MeshBasicMaterial({ 
    color: 0x00d2ff, 
    wireframe: true,
    transparent: true,
    opacity: 0.8
  });
  const innerRing = new THREE.Mesh(innerGeometry, innerMaterial);
  arcGroup.add(innerRing);

  // 3. Middle Geometry (Icosahedron)
  const midGeometry = new THREE.IcosahedronGeometry(2.5, 1);
  const midMaterial = new THREE.MeshBasicMaterial({ 
    color: 0x0088ff, 
    wireframe: true,
    transparent: true,
    opacity: 0.3
  });
  const midMesh = new THREE.Mesh(midGeometry, midMaterial);
  arcGroup.add(midMesh);

  // 4. Outer Ring (Dashed Torus or Particles)
  const outerGeometry = new THREE.TorusGeometry(3.5, 0.05, 16, 100);
  const outerMaterial = new THREE.MeshBasicMaterial({ 
    color: 0x00aaff,
    transparent: true,
    opacity: 0.5
  });
  const outerRing = new THREE.Mesh(outerGeometry, outerMaterial);
  arcGroup.add(outerRing);

  // Handle window resize
  window.addEventListener('resize', () => {
    const w = container.clientWidth || 400;
    const h = container.clientHeight || 400;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  });

  // Animation Loop
  function animate() {
    requestAnimationFrame(animate);
    
    // Determine rotation speed
    const currentSpeed = isThinking ? baseRotationSpeed * 5 : baseRotationSpeed;
    
    // Rotate elements
    arcGroup.rotation.z -= currentSpeed;
    innerRing.rotation.x += currentSpeed * 2;
    innerRing.rotation.y += currentSpeed * 2;
    midMesh.rotation.x -= currentSpeed;
    midMesh.rotation.y += currentSpeed * 1.5;
    
    // Core pulsing effect
    const time = Date.now() * 0.001;
    const pulse = Math.sin(time * (isThinking ? 10 : 2)) * 0.1 + 1;
    core.scale.set(pulse, pulse, pulse);

    renderer.render(scene, camera);
  }
  
  animate();
}

export function setThinkingState(state) {
  isThinking = state;
}

export function triggerAlert(isAlert) {
  if (!arcGroup) return;
  
  // Change color to red if alert
  arcGroup.children.forEach(child => {
    if (child.material && child.material.color) {
      if (isAlert) {
        // Save original color if not saved
        if (!child.userData.origColor) {
          child.userData.origColor = child.material.color.getHex();
        }
        child.material.color.setHex(0xff0000);
      } else {
        if (child.userData.origColor) {
          child.material.color.setHex(child.userData.origColor);
        }
      }
    }
  });
}
