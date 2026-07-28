import { useEffect, useRef } from 'react';
import { useJarvisStore } from '../../store/jarvisStore';

export function Background() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const aiState = useJarvisStore((s) => s.aiState);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = window.innerWidth;
    let height = window.innerHeight;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener('resize', resize);
    resize();

    // Node grid for neural background
    const nodes: { x: number; y: number; vx: number; vy: number; radius: number; pulseOff: number }[] = [];
    const NODE_COUNT = Math.floor((width * height) / 25000);

    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.2,
        vy: (Math.random() - 0.5) * 0.2,
        radius: Math.random() * 1.5 + 0.5,
        pulseOff: Math.random() * Math.PI * 2,
      });
    }

    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);
      
      // Background gradient
      const gradient = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, Math.max(width, height));
      gradient.addColorStop(0, 'rgba(2, 10, 30, 0.4)');
      gradient.addColorStop(1, 'rgba(2, 4, 8, 0.9)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // State specific adjustments
      let connectionDistance = 150;
      let alphaMult = 0.05;

      if (aiState === 'thinking') {
        alphaMult = 0.1;
        connectionDistance = 180;
      } else if (aiState === 'executing') {
        alphaMult = 0.15;
        connectionDistance = 200;
      } else if (aiState === 'error') {
        alphaMult = 0.08;
      }

      ctx.lineWidth = 0.5;

      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        
        // Move nodes
        node.x += node.vx * (aiState === 'executing' ? 3 : 1);
        node.y += node.vy * (aiState === 'executing' ? 3 : 1);

        if (node.x < 0) node.x = width;
        if (node.x > width) node.x = 0;
        if (node.y < 0) node.y = height;
        if (node.y > height) node.y = 0;

        // Draw connections
        for (let j = i + 1; j < nodes.length; j++) {
          const other = nodes[j];
          const dx = node.x - other.x;
          const dy = node.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < connectionDistance) {
            const alpha = (1 - dist / connectionDistance) * alphaMult;
            
            // Color based on state
            if (aiState === 'thinking') {
              ctx.strokeStyle = `rgba(124, 58, 237, ${alpha})`; // Violet
            } else if (aiState === 'error') {
              ctx.strokeStyle = `rgba(239, 68, 68, ${alpha})`; // Red
            } else {
              ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`; // Cyan
            }
            
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(other.x, other.y);
            ctx.stroke();
          }
        }

        // Draw node
        const pulse = (Math.sin(time * 0.002 + node.pulseOff) + 1) * 0.5;
        ctx.fillStyle = `rgba(0, 212, 255, ${0.1 + pulse * 0.3})`;
        if (aiState === 'error') ctx.fillStyle = `rgba(239, 68, 68, ${0.1 + pulse * 0.3})`;
        
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + pulse, 0, Math.PI * 2);
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw(0);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [aiState]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none -z-10"
    />
  );
}