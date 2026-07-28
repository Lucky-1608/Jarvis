import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useJarvisStore } from '../../store/jarvisStore';

const STATE_COLORS: Record<string, { primary: string; secondary: string; glow: string }> = {
  idle:      { primary: '#00d4ff', secondary: '#0055ff', glow: 'rgba(0,212,255,0.4)' },
  listening: { primary: '#00ffff', secondary: '#0088ff', glow: 'rgba(0,255,255,0.5)' },
  thinking:  { primary: '#7c3aed', secondary: '#d946ef', glow: 'rgba(124,58,237,0.5)' },
  executing: { primary: '#ffffff', secondary: '#00d4ff', glow: 'rgba(255,255,255,0.6)' },
  speaking:  { primary: '#00d4ff', secondary: '#00aaff', glow: 'rgba(0,212,255,0.5)' },
  error:     { primary: '#ff3333', secondary: '#ff8800', glow: 'rgba(255,50,50,0.6)' },
  success:   { primary: '#00ffaa', secondary: '#f59e0b', glow: 'rgba(0,255,170,0.5)' },
};

export function WebGLFallbackBlob() {
  const aiState = useJarvisStore((s) => s.aiState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  const colors = STATE_COLORS[aiState] ?? STATE_COLORS.idle;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const SIZE = 600;
    canvas.width = SIZE;
    canvas.height = SIZE;
    const cx = SIZE / 2;
    const cy = SIZE / 2;

    function hexToRgb(hex: string) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return { r, g, b };
    }

    function drawBlob(t: number) {
      ctx!.clearRect(0, 0, SIZE, SIZE);

      const stateColors = STATE_COLORS[aiState] ?? STATE_COLORS.idle;
      const c1 = hexToRgb(stateColors.primary);
      const c2 = hexToRgb(stateColors.secondary);

      const speedMap: Record<string, number> = {
        idle: 0.4, listening: 0.9, thinking: 2.2, executing: 3.0, speaking: 1.4, error: 4.0, success: 0.7,
      };
      const speed = speedMap[aiState] ?? 0.4;
      const elapsed = t * speed;

      // --- outer glow rings ---
      for (let ring = 3; ring >= 1; ring--) {
        const ringRadius = 180 + ring * 18;
        const ringAlpha = (0.04 - ring * 0.01) * (1 + 0.3 * Math.sin(elapsed * 0.6));
        const grd = ctx!.createRadialGradient(cx, cy, ringRadius - 8, cx, cy, ringRadius + 8);
        grd.addColorStop(0, `rgba(${c1.r},${c1.g},${c1.b},${ringAlpha * 2})`);
        grd.addColorStop(1, `rgba(${c1.r},${c1.g},${c1.b},0)`);
        ctx!.beginPath();
        ctx!.arc(cx, cy, ringRadius, 0, Math.PI * 2);
        ctx!.strokeStyle = grd;
        ctx!.lineWidth = 16;
        ctx!.stroke();
      }

      // --- ambient glow behind blob ---
      const bgGrd = ctx!.createRadialGradient(cx, cy, 0, cx, cy, 240);
      bgGrd.addColorStop(0, `rgba(${c1.r},${c1.g},${c1.b},0.15)`);
      bgGrd.addColorStop(0.5, `rgba(${c2.r},${c2.g},${c2.b},0.06)`);
      bgGrd.addColorStop(1, 'rgba(0,0,0,0)');
      ctx!.beginPath();
      ctx!.arc(cx, cy, 240, 0, Math.PI * 2);
      ctx!.fillStyle = bgGrd;
      ctx!.fill();

      // --- main blob shape (organic path) ---
      const R = 150;
      const POINTS = 12;
      const strengthMap: Record<string, number> = {
        idle: 0.12, listening: 0.18, thinking: 0.35, executing: 0.4, speaking: 0.22, error: 0.5, success: 0.1,
      };
      const noiseStr = strengthMap[aiState] ?? 0.12;

      ctx!.beginPath();
      for (let i = 0; i <= POINTS; i++) {
        const angle = (i / POINTS) * Math.PI * 2 - Math.PI / 2;
        const freqs = [1, 2, 3.7, 5.3];
        const noise = freqs.reduce((acc, f, idx) => {
          const phase = elapsed * (0.5 + idx * 0.3) + idx * 1.1;
          return acc + Math.sin(angle * f + phase) * (noiseStr / (idx + 1));
        }, 0);
        const r = R * (1 + noise);
        const px = cx + Math.cos(angle) * r;
        const py = cy + Math.sin(angle) * r;
        if (i === 0) ctx!.moveTo(px, py);
        else ctx!.lineTo(px, py);
      }
      ctx!.closePath();

      // fill gradient
      const fillGrd = ctx!.createRadialGradient(cx - 30, cy - 40, 0, cx, cy, R * 1.1);
      fillGrd.addColorStop(0, `rgba(${c1.r},${c1.g},${c1.b},0.95)`);
      fillGrd.addColorStop(0.4, `rgba(${Math.round((c1.r+c2.r)/2)},${Math.round((c1.g+c2.g)/2)},${Math.round((c1.b+c2.b)/2)},0.7)`);
      fillGrd.addColorStop(1, `rgba(${c2.r},${c2.g},${c2.b},0.3)`);

      ctx!.fillStyle = fillGrd;
      ctx!.fill();

      // fresnel-style bright edge
      ctx!.save();
      ctx!.clip();
      const edgeGrd = ctx!.createRadialGradient(cx, cy, R * 0.6, cx, cy, R * 1.05);
      edgeGrd.addColorStop(0, 'rgba(255,255,255,0)');
      edgeGrd.addColorStop(0.85, `rgba(${c1.r},${c1.g},${c1.b},0.15)`);
      edgeGrd.addColorStop(1, `rgba(${c1.r},${c1.g},${c1.b},0.6)`);
      ctx!.fillStyle = edgeGrd;
      ctx!.fillRect(0, 0, SIZE, SIZE);

      // internal volumetric light
      const lightX = cx + Math.cos(elapsed * 0.4) * 40;
      const lightY = cy + Math.sin(elapsed * 0.3) * 30;
      const innerGrd = ctx!.createRadialGradient(lightX, lightY, 0, lightX, lightY, 100);
      innerGrd.addColorStop(0, `rgba(255,255,255,0.35)`);
      innerGrd.addColorStop(0.4, `rgba(${c1.r},${c1.g},${c1.b},0.15)`);
      innerGrd.addColorStop(1, 'rgba(0,0,0,0)');
      ctx!.fillStyle = innerGrd;
      ctx!.fillRect(0, 0, SIZE, SIZE);
      ctx!.restore();

      // chromatic aberration hint — red channel offset
      ctx!.save();
      ctx!.globalAlpha = 0.06;
      ctx!.globalCompositeOperation = 'screen';
      ctx!.translate(2, 1);
      ctx!.beginPath();
      for (let i = 0; i <= POINTS; i++) {
        const angle = (i / POINTS) * Math.PI * 2 - Math.PI / 2;
        const freqs = [1, 2, 3.7, 5.3];
        const noise = freqs.reduce((acc, f, idx) => {
          const phase = elapsed * (0.5 + idx * 0.3) + idx * 1.1;
          return acc + Math.sin(angle * f + phase) * (noiseStr / (idx + 1));
        }, 0);
        const r = R * (1 + noise);
        const px = cx + Math.cos(angle) * r;
        const py = cy + Math.sin(angle) * r;
        if (i === 0) ctx!.moveTo(px, py);
        else ctx!.lineTo(px, py);
      }
      ctx!.closePath();
      ctx!.fillStyle = 'rgba(255,0,0,0.5)';
      ctx!.fill();
      ctx!.restore();

      // --- particles ---
      const particleCount = 40;
      for (let i = 0; i < particleCount; i++) {
        const orbitAngle = (i / particleCount) * Math.PI * 2 + elapsed * (0.15 + (i % 3) * 0.05);
        const orbitR = 175 + Math.sin(elapsed * 0.7 + i * 0.8) * 20;
        const px = cx + Math.cos(orbitAngle) * orbitR;
        const py = cy + Math.sin(orbitAngle) * orbitR;
        const alpha = 0.3 + 0.4 * Math.abs(Math.sin(elapsed * 0.5 + i));
        const size = 1.2 + Math.abs(Math.sin(elapsed + i)) * 1.5;

        ctx!.beginPath();
        ctx!.arc(px, py, size, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(${c1.r},${c1.g},${c1.b},${alpha})`;
        ctx!.fill();

        // connect nearby
        for (let j = i + 1; j < Math.min(i + 3, particleCount); j++) {
          const angle2 = (j / particleCount) * Math.PI * 2 + elapsed * (0.15 + (j % 3) * 0.05);
          const r2 = 175 + Math.sin(elapsed * 0.7 + j * 0.8) * 20;
          const px2 = cx + Math.cos(angle2) * r2;
          const py2 = cy + Math.sin(angle2) * r2;
          const dist = Math.hypot(px2 - px, py2 - py);
          if (dist < 70) {
            ctx!.beginPath();
            ctx!.moveTo(px, py);
            ctx!.lineTo(px2, py2);
            ctx!.strokeStyle = `rgba(${c1.r},${c1.g},${c1.b},${(1 - dist / 70) * 0.3})`;
            ctx!.lineWidth = 0.5;
            ctx!.stroke();
          }
        }
      }
    }

    let lastTime = performance.now();
    function loop(now: number) {
      const dt = (now - lastTime) / 1000;
      lastTime = now;
      timeRef.current += dt;
      drawBlob(timeRef.current);
      animRef.current = requestAnimationFrame(loop);
    }
    animRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animRef.current);
  }, [aiState]);

  return (
    <div className="relative flex items-center justify-center w-full h-full scale-50">
      {/* glow behind canvas */}
      <motion.div
        className="absolute rounded-full pointer-events-none"
        style={{
          width: 360,
          height: 360,
          background: `radial-gradient(circle, ${colors.glow} 0%, transparent 70%)`,
          filter: 'blur(40px)',
        }}
        animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
      />
      <canvas
        ref={canvasRef}
        style={{ width: 400, height: 400 }}
        className="relative z-10 cursor-pointer"
        onClick={() => {
          const { setAIState } = useJarvisStore.getState();
          const states = ['idle', 'listening', 'thinking', 'executing', 'speaking', 'success', 'error'] as const;
          const cur = useJarvisStore.getState().aiState;
          const next = states[(states.indexOf(cur) + 1) % states.length];
          setAIState(next);
        }}
      />
    </div>
  );
}
