import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Folder, Brain, Wrench, Users, Network,
  Eye, Mic, Settings 
} from 'lucide-react';
import { Link, useLocation } from 'wouter';

const navItems = [
  { id: 'projects', icon: Folder, label: 'Projects', path: '/' },
  { id: 'memory', icon: Brain, label: 'Memory', path: '/memory' },
  { id: 'vision', icon: Eye, label: 'Vision', path: '/vision' },
  { id: 'voice', icon: Mic, label: 'Voice', path: '/voice' },
  { id: 'tools', icon: Wrench, label: 'Tools', path: '/tools' },
  { id: 'agents', icon: Users, label: 'Agents', path: '/agents' },
  { id: 'workflows', icon: Network, label: 'Workflows', path: '/workflows' },
];

export function LeftPanel() {
  const [location] = useLocation();
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <motion.div 
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.1 }}
      className="w-64 h-full border-r border-[var(--border-subtle)] bg-[var(--bg-panel)] backdrop-blur-xl flex flex-col z-10 shrink-0"
    >
      {/* Header */}
      <div className="h-16 flex items-center px-6 border-b border-[var(--border-subtle)]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[var(--accent-cyan)] to-[var(--accent-blue)] flex items-center justify-center shadow-[0_0_15px_rgba(0,212,255,0.4)]">
            <div className="w-6 h-6 rounded-full bg-[#020408] flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-[var(--accent-cyan)] animate-pulse" />
            </div>
          </div>
          <div>
            <h1 className="text-[var(--text-primary)] font-semibold tracking-wider text-sm">JARVIS OS</h1>
            <p className="text-[var(--text-muted)] text-[10px] tracking-widest uppercase">v0.1.0-alpha</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-3 flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive = location === item.path;
          const isHovered = hovered === item.id;
          
          return (
            <Link key={item.id} href={item.path} className="block w-full">
              <motion.div
                onHoverStart={() => setHovered(item.id)}
                onHoverEnd={() => setHovered(null)}
                className={`
                  relative flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-colors duration-300
                  ${isActive ? 'bg-[rgba(0,212,255,0.1)] text-[var(--accent-cyan)]' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.03)]'}
                `}
                whileHover={{ x: 4 }}
              >
                {isActive && (
                  <motion.div 
                    layoutId="activeNav"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[var(--accent-cyan)] rounded-r-full shadow-[0_0_10px_rgba(0,212,255,0.8)]"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <item.icon size={18} className={isActive ? 'drop-shadow-[0_0_8px_rgba(0,212,255,0.6)]' : ''} />
                <span className="text-sm font-medium tracking-wide">{item.label}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="mt-auto p-4 border-t border-[var(--border-subtle)]">
        
        <div className="mt-4 flex items-center gap-3 px-3 py-2 bg-[rgba(0,0,0,0.3)] rounded-lg border border-[rgba(255,255,255,0.05)]">
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center overflow-hidden border border-zinc-700">
              <span className="text-xs font-bold text-zinc-400">TR</span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-[#060a14]" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-[var(--text-primary)]">Admin User</p>
            <p className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)]" />
              GPT-4o
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}