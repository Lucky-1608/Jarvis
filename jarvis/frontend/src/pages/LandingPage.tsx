import { motion } from 'framer-motion';
import { useLocation } from 'wouter';
import { Bot, Brain, Shield, Zap, Terminal } from 'lucide-react';
import { Background } from '../components/core/Background';

export function LandingPage() {
  const [, setLocation] = useLocation();

  const handleLaunch = () => {
    setLocation('/app');
  };

  return (
    <div className="w-full min-h-screen flex flex-col bg-[#020408] text-white selection:bg-[var(--accent-cyan)] selection:text-black overflow-x-hidden relative font-sans">
      <Background />
      
      {/* Navbar */}
      <nav className="w-full flex items-center justify-between p-6 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full border border-[var(--accent-cyan)] flex items-center justify-center bg-black/50 shadow-[0_0_15px_rgba(0,255,255,0.2)]">
            <Bot size={16} className="text-[var(--accent-cyan)]" />
          </div>
          <span className="font-bold tracking-widest text-sm">JARVIS OS</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium text-zinc-400">
          <a href="#/privacy" className="hover:text-white transition-colors">Privacy</a>
          <a href="#/terms" className="hover:text-white transition-colors">Terms</a>
          <button 
            onClick={handleLaunch}
            className="px-4 py-2 rounded-md bg-white/10 hover:bg-white/20 border border-white/10 transition-colors text-white"
          >
            Sign In
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 z-10 text-center mt-12 mb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-4xl mx-auto flex flex-col items-center"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent-cyan)]/10 border border-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] text-xs font-mono mb-8">
            <Terminal size={14} />
            <span>SYSTEM v0.1.0 ONLINE</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-zinc-500">
            The AI Operating System <br /> of the Future
          </h1>
          
          <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mb-10 leading-relaxed">
            Jarvis OS is an advanced, centralized artificial intelligence interface designed to automate tasks, manage workflows, and act as your ultimate digital companion.
          </p>

          <div className="flex flex-col sm:flex-row gap-4">
            <button 
              onClick={handleLaunch}
              className="px-8 py-4 rounded-xl bg-white text-black font-semibold hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2"
            >
              Launch System
              <Zap size={18} />
            </button>
          </div>
        </motion.div>

        {/* Features Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto w-full mt-32"
        >
          <FeatureCard 
            icon={<Brain className="text-purple-400" size={24} />}
            title="Cognitive Architecture"
            description="Powered by advanced LLMs, Jarvis understands context, retains memory across sessions, and learns from your interactions."
          />
          <FeatureCard 
            icon={<Shield className="text-emerald-400" size={24} />}
            title="Secure & Private"
            description="Your data remains under your control. Authentication is required to access the core system features and personal memory banks."
          />
          <FeatureCard 
            icon={<Zap className="text-yellow-400" size={24} />}
            title="Agentic Workflows"
            description="Delegate complex, multi-step tasks to autonomous agents that plan, execute, and report back to you seamlessly."
          />
        </motion.div>
      </main>
      
      <footer className="w-full text-center py-6 text-zinc-600 text-xs z-10 border-t border-white/5 bg-black/20">
        &copy; {new Date().getFullYear()} Jarvis OS. All rights reserved.
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="flex flex-col items-start p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-colors text-left">
      <div className="p-3 rounded-lg bg-black/50 border border-white/10 mb-4 shadow-inner">
        {icon}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-zinc-400 leading-relaxed">{description}</p>
    </div>
  );
}
