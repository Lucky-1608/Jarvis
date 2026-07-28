import { motion, AnimatePresence } from 'framer-motion';
import { useJarvisStore } from '../../store/jarvisStore';

const stateLabels = {
  idle: 'SYSTEM STANDBY',
  listening: 'LISTENING',
  thinking: 'ANALYZING',
  executing: 'EXECUTING',
  speaking: 'SYNTHESIZING',
  error: 'SYSTEM FAULT',
  success: 'TASK COMPLETE'
};

const stateColors = {
  idle: 'text-zinc-400 bg-zinc-900/50 border-zinc-800',
  listening: 'text-[var(--accent-cyan)] bg-[rgba(0,212,255,0.1)] border-[rgba(0,212,255,0.3)] shadow-[0_0_15px_rgba(0,212,255,0.2)]',
  thinking: 'text-[var(--accent-violet)] bg-[rgba(124,58,237,0.1)] border-[rgba(124,58,237,0.3)] shadow-[0_0_15px_rgba(124,58,237,0.2)]',
  executing: 'text-white bg-white/10 border-white/30 shadow-[0_0_20px_rgba(255,255,255,0.3)]',
  speaking: 'text-[var(--accent-cyan)] bg-[rgba(0,212,255,0.1)] border-[rgba(0,212,255,0.3)] shadow-[0_0_15px_rgba(0,212,255,0.2)]',
  error: 'text-red-400 bg-red-500/10 border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]',
  success: 'text-[var(--accent-gold)] bg-[rgba(245,158,11,0.1)] border-[rgba(245,158,11,0.3)] shadow-[0_0_15px_rgba(245,158,11,0.2)]'
};

export function StateIndicator() {
  const aiState = useJarvisStore((s) => s.aiState);

  return (
    <motion.div 
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.3 }}
      className="absolute top-24 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 pointer-events-none"
    >
      <div className={`px-4 py-1.5 rounded-full border backdrop-blur-md transition-all duration-500 flex items-center gap-2 ${stateColors[aiState]}`}>
        {aiState !== 'idle' && aiState !== 'error' && aiState !== 'success' && (
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-1 h-1 rounded-full bg-current"
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.5, 1, 0.5]
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  delay: i * 0.2
                }}
              />
            ))}
          </div>
        )}
        <AnimatePresence mode="wait">
          <motion.span
            key={aiState}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="text-xs font-bold tracking-[0.2em]"
          >
            {stateLabels[aiState]}
          </motion.span>
        </AnimatePresence>
      </div>
      
      {/* Subtle JARVIS wordmark at the very top, part of the main stage, not the pill */}
    </motion.div>
  );
}