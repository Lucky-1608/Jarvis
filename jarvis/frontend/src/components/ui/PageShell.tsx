import { useEffect, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { LeftPanel } from './LeftPanel';
import { RightPanel } from './RightPanel';
import { Background } from '../core/Background';

export function PageShell({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  return (
    <div className="w-full h-screen flex overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)] selection:bg-[var(--accent-cyan)] selection:text-black">
      <Background />
      <LeftPanel />
      <main className="flex-1 h-full overflow-y-auto overflow-x-hidden relative flex flex-col bg-[rgba(2,4,8,0.3)] backdrop-blur-sm z-10">
        <motion.div 
          className="flex-1 flex flex-col w-full h-full"
          initial={{ opacity: 0, y: 10 }} 
          animate={{ opacity: 1, y: 0 }} 
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        >
          {children}
        </motion.div>
      </main>
      <RightPanel />
    </div>
  );
}