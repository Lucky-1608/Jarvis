import { Canvas } from '@react-three/fiber';
import { EffectComposer, Bloom, ChromaticAberration, Vignette } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import { LeftPanel } from '../components/ui/LeftPanel';
import { RightPanel } from '../components/ui/RightPanel';
import { Background } from '../components/core/Background';
import { ArcReactor } from '../components/core/ArcReactor';
import { ConversationInput } from '../components/ui/ConversationInput';
import { ChatHistory } from '../components/ui/ChatHistory';
import { StateIndicator } from '../components/ui/StateIndicator';
import { WebGLErrorBoundary, webGLAvailable } from '../components/core/WebGLErrorBoundary';
import { WebGLFallbackBlob } from '../components/core/WebGLFallbackBlob';
import { MobileHeader } from '../components/ui/MobileHeader';
import { Suspense, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useJarvisStore } from '../store/jarvisStore';
import { checkBackendHealth } from '../lib/api';
import * as THREE from 'three';

function LoadingScreen() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#020408] z-50">
      <motion.div 
        className="flex flex-col items-center gap-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="relative w-16 h-16">
          <motion.div 
            className="absolute inset-0 rounded-full border-t-2 border-r-2 border-[var(--accent-cyan)]"
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
          />
          <motion.div 
            className="absolute inset-2 rounded-full border-b-2 border-l-2 border-[var(--accent-violet)]"
            animate={{ rotate: -360 }}
            transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse shadow-[0_0_10px_white]" />
          </div>
        </div>
        <div className="text-[var(--accent-cyan)] text-xs font-mono tracking-[0.3em] animate-pulse">
          INITIALIZING CORE
        </div>
      </motion.div>
    </div>
  );
}

export function Home() {
  const [hasWebGL, setHasWebGL] = useState<boolean | null>(null);

  const connectWebSocket = useJarvisStore(s => s.connectWebSocket);
  const updateVisionStatus = useJarvisStore(s => s.updateVisionStatus);
  const setBackendConnected = useJarvisStore(s => s.setBackendConnected);
  const addLog = useJarvisStore(s => s.addLog);

  useEffect(() => {
    setHasWebGL(webGLAvailable());
    connectWebSocket();

    // Check backend health on mount
    checkBackendHealth().then(connected => {
      setBackendConnected(connected);
      if (connected) {
        addLog({ message: 'Backend API reachable.' });
      } else {
        addLog({ message: 'Backend API unreachable — start with: python -m jarvis serve', type: 'warning' });
      }
    });
  }, [connectWebSocket, updateVisionStatus, setBackendConnected, addLog]);

  return (
    <div className="w-full h-[100dvh] flex overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)] selection:bg-[var(--accent-cyan)] selection:text-black">
      {/* 2D Background canvas */}
      <Background />
      
      {/* Left Sidebar */}
      <LeftPanel />
      
      {/* Main Stage */}
      <div className="flex-1 relative h-full flex flex-col">
        <MobileHeader />
        
        {/* Subtle Wordmark */}
        <div className="hidden lg:block absolute top-6 left-1/2 -translate-x-1/2 z-10 opacity-30 pointer-events-none">
          <h2 className="text-[10px] font-bold tracking-[0.5em] text-center">J.A.R.V.I.S.</h2>
          <p className="text-[8px] tracking-widest text-[var(--accent-cyan)] text-center mt-1">OPERATING SYSTEM</p>
        </div>

        <StateIndicator />
        
        {/* 3D Scene — WebGL when available, CSS canvas fallback otherwise */}
        <div className="absolute inset-0 w-full h-full pointer-events-auto">
          {hasWebGL === null ? (
            <LoadingScreen />
          ) : hasWebGL ? (
            <WebGLErrorBoundary fallback={<WebGLFallbackBlob />}>
              <Suspense fallback={<LoadingScreen />}>
                <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
                  <ambientLight intensity={0.2} />
                  <ArcReactor />
                  <EffectComposer>
                    <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} intensity={1.5} />
                    <ChromaticAberration blendFunction={BlendFunction.NORMAL} offset={new THREE.Vector2(0.002, 0.002)} radialModulation={false} modulationOffset={0} />
                    <Vignette eskil={false} offset={0.1} darkness={0.6} />
                  </EffectComposer>
                </Canvas>
              </Suspense>
            </WebGLErrorBoundary>
          ) : (
            <WebGLFallbackBlob />
          )}
        </div>
        <ChatHistory />
        <ConversationInput />
      </div>
      
      {/* Right Sidebar */}
      <RightPanel />
    </div>
  );
}