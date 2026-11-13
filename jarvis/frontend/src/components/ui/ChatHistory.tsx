import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock } from 'lucide-react';
import { useJarvisStore } from '../../store/jarvisStore';

const ThinkingIndicator = () => (
  <div className="flex gap-2 items-center h-6 px-1 py-1">
    {[0, 0.2, 0.4].map((delay, i) => (
      <motion.div 
        key={i}
        animate={{ 
          y: [0, -6, 0], 
          scale: [1, 1.2, 1],
          opacity: [0.4, 1, 0.4] 
        }} 
        transition={{ repeat: Infinity, duration: 0.8, delay, ease: "easeInOut" }} 
        className="w-2 h-2 rounded-full"
        style={{
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))',
          boxShadow: '0 0 8px var(--accent-cyan)'
        }}
      />
    ))}
  </div>
);

const ListeningIndicator = () => (
  <div className="flex gap-1.5 items-center h-6 px-1 py-1">
    {[0, 0.2, 0.4, 0.1, 0.3].map((delay, i) => (
      <motion.div 
        key={i}
        animate={{ 
          height: [6, 18, 6],
          backgroundColor: ['#ef4444', '#f87171', '#ef4444'],
          boxShadow: ['0 0 5px rgba(239,68,68,0.3)', '0 0 12px rgba(239,68,68,0.8)', '0 0 5px rgba(239,68,68,0.3)']
        }} 
        transition={{ repeat: Infinity, duration: 0.7, delay, ease: "easeInOut" }} 
        className="w-1 rounded-full"
      />
    ))}
  </div>
);

const TypewriterText = ({ text, shouldAnimate, onUpdate }: { text: string, shouldAnimate: boolean, onUpdate: () => void }) => {
  const [displayedText, setDisplayedText] = useState(shouldAnimate ? '' : text);
  
  useEffect(() => {
    if (!shouldAnimate) return;
    
    // Split text by spaces but retain the spaces in the final join
    const words = text.split(' ');
    let current = 0;
    
    const interval = setInterval(() => {
      current += 1;
      setDisplayedText(words.slice(0, current).join(' '));
      onUpdate();
      if (current >= words.length) {
        clearInterval(interval);
      }
    }, 40); // 40ms per word
    
    return () => clearInterval(interval);
  }, [text, shouldAnimate, onUpdate]);

  return <>{displayedText}</>;
};

const extractImagesFromText = (text: string) => {
  const images: { alt: string; url: string }[] = [];
  const mdRegex = /!\[([^\]]*)\]\((https?:\/\/[^\s\)]+)\)/g;
  let match;
  while ((match = mdRegex.exec(text)) !== null) {
    images.push({ alt: match[1] || 'Image', url: match[2] });
  }
  const cleanText = text.replace(mdRegex, '').trim();
  return { cleanText, images };
};

export function ChatHistory() {
  const messages = useJarvisStore(s => s.messages);
  const aiState = useJarvisStore(s => s.aiState);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, aiState, scrollToBottom]);

  if (messages.length === 0 && aiState !== 'thinking' && aiState !== 'listening') return null;

  return (
    <div className="absolute bottom-[5.5rem] left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-20 pointer-events-none">
      <div 
        ref={scrollRef}
        className="max-h-[60vh] overflow-y-auto pointer-events-auto pr-2"
        style={{
          maskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)'
        }}
      >
        <div className="flex flex-col gap-4 py-8">
          <AnimatePresence initial={false}>
            {messages.map((msg, idx) => (
              <motion.div 
                key={msg.id} 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex flex-col gap-1 text-sm py-2 px-4 rounded-xl backdrop-blur-md border border-[rgba(255,255,255,0.05)] w-fit max-w-[85%] ${
                  msg.role === 'user' 
                    ? 'self-end bg-[rgba(0,100,255,0.15)] text-blue-100 border-[rgba(0,100,255,0.2)]' 
                    : 'self-start bg-[rgba(10,15,30,0.8)] text-zinc-200 shadow-[0_0_15px_rgba(0,212,255,0.1)]'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-semibold uppercase text-[10px] ${msg.role === 'user' ? 'text-blue-400' : 'text-[var(--accent-cyan)]'}`}>
                    {msg.role === 'user' ? 'You' : 'JARVIS'}
                  </span>
                  <span className="text-[10px] opacity-50 flex items-center gap-1">
                    <Clock size={10} />{msg.timestamp}
                  </span>
                </div>
                <div className="break-words leading-relaxed whitespace-pre-wrap">
                  {msg.role === 'jarvis' ? (
                    (() => {
                      const { cleanText, images } = extractImagesFromText(msg.text);
                      return (
                        <div className="flex flex-col gap-2">
                          {cleanText ? (
                            <TypewriterText 
                              text={cleanText} 
                              shouldAnimate={idx === messages.length - 1} 
                              onUpdate={scrollToBottom} 
                            />
                          ) : null}
                          {images.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {images.map((img, imgIdx) => (
                                <a 
                                  key={imgIdx} 
                                  href={img.url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="group/img relative block overflow-hidden rounded-lg border border-[rgba(255,255,255,0.1)] hover:border-[var(--accent-cyan)] transition-all max-w-[280px]"
                                >
                                  <img 
                                    src={img.url} 
                                    alt={img.alt} 
                                    className="max-h-52 w-auto object-cover rounded-lg group-hover/img:scale-105 transition-transform duration-300" 
                                    loading="lazy"
                                    onLoad={scrollToBottom}
                                  />
                                  {img.alt && img.alt !== 'Image' && (
                                    <div className="absolute bottom-0 inset-x-0 bg-black/70 backdrop-blur-sm px-2 py-1 text-[11px] text-zinc-300 truncate">
                                      {img.alt}
                                    </div>
                                  )}
                                </a>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })()
                  ) : (
                    msg.text
                  )}
                </div>
              </motion.div>
            ))}

            {(aiState === 'thinking' || aiState === 'listening') && (
              <motion.div 
                key="thinking-indicator"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                className={`flex flex-col gap-1 text-sm py-2 px-4 rounded-xl backdrop-blur-md border w-fit self-start bg-[rgba(10,15,30,0.8)] text-zinc-200 transition-all duration-500 ${aiState === 'listening' ? 'shadow-[0_0_20px_rgba(239,68,68,0.15)] border-red-500/20' : 'shadow-[0_0_20px_rgba(0,212,255,0.15)] border-[var(--accent-cyan)]/20'}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-semibold uppercase text-[10px] ${aiState === 'listening' ? 'text-red-500' : 'text-[var(--accent-cyan)]'}`}>JARVIS</span>
                  <span className="text-[10px] opacity-50 flex items-center gap-1">
                    {aiState === 'listening' ? 'Listening...' : 'Thinking...'}
                  </span>
                </div>
                {aiState === 'listening' ? <ListeningIndicator /> : <ThinkingIndicator />}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
