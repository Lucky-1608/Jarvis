import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, Paperclip, Send } from 'lucide-react';
import { useJarvisStore } from '../../store/jarvisStore';
import { apiFetch } from '../../lib/api';

export function ConversationInput() {
  const [value, setValue] = useState('');
  const setAIState = useJarvisStore((s) => s.setAIState);
  const aiState = useJarvisStore((s) => s.aiState);

  const handleSend = async () => {
    if (!value.trim()) return;

    const userText = value.trim();
    setValue('');
    setAIState('thinking');

    const store = useJarvisStore.getState();
    store.addMessage(userText, true);
    store.addLog({ message: `User command received: ${userText.substring(0, 20)}...` });

    const result = await apiFetch<{ content: string; provider?: string; model?: string }>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: userText, stream: false })
    });

    if (result.ok && result.data.content) {
      setAIState('idle');
      store.addMessage(result.data.content, false);
      store.addLog({ message: 'Command executed successfully.' });
      // Reset error state if it was set by a previous failed call
      if (store.aiState === 'error') {
        setAIState('idle');
      }
    } else if (!result.ok) {
      setAIState('idle');
      store.addMessage('I am JARVIS. I am currently running in offline demo mode. Please start the backend server to enable AI capabilities.', false);
      store.addLog({ message: 'Backend not reachable — running in offline mode.', type: 'warning' });
    }
  };

  const isGenerating = aiState === 'thinking' || aiState === 'executing' || aiState === 'listening';

  return (
    <motion.div 
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.4 }}
      className="absolute bottom-12 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-20"
    >
      <div className="relative group">
        {/* Animated border glow */}
        <div className={`absolute -inset-0.5 rounded-2xl blur-md opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200 ${isGenerating ? 'bg-gradient-to-r from-[var(--accent-cyan)] via-[var(--accent-violet)] to-[var(--accent-cyan)] animate-pulse' : 'bg-[var(--accent-cyan)]'}`} />
        
        <div className="relative flex items-center bg-[rgba(10,15,30,0.6)] backdrop-blur-xl border border-[rgba(255,255,255,0.1)] rounded-2xl p-2 shadow-2xl">
          
          <button className="p-3 text-zinc-400 hover:text-[var(--accent-cyan)] transition-colors rounded-xl hover:bg-[rgba(255,255,255,0.05)]">
            <Paperclip size={20} />
          </button>
          
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isGenerating ? "Processing instruction..." : "Ask Jarvis anything..."}
            disabled={isGenerating}
            className="flex-1 bg-transparent border-none outline-none text-white placeholder-zinc-500 px-2 font-medium tracking-wide disabled:opacity-50"
          />
          
          <div className="flex items-center gap-2 pr-1">
            <button className="p-3 text-zinc-400 hover:text-[var(--accent-cyan)] transition-colors rounded-xl hover:bg-[rgba(255,255,255,0.05)]">
              <Mic size={20} />
            </button>
            <button 
              onClick={handleSend}
              disabled={isGenerating || !value.trim()}
              className={`p-3 rounded-xl transition-all duration-300 ${value.trim() && !isGenerating ? 'bg-[var(--accent-cyan)] text-black shadow-[0_0_15px_rgba(0,212,255,0.4)]' : 'bg-[rgba(255,255,255,0.05)] text-zinc-500'}`}
            >
              <Send size={20} className={value.trim() && !isGenerating ? 'translate-x-0.5 -translate-y-0.5' : ''} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}