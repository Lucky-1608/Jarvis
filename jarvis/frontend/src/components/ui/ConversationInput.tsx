import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Paperclip, Send, Square, X, File as FileIcon } from 'lucide-react';
import { useJarvisStore } from '../../store/jarvisStore';
import { apiFetch } from '../../lib/api';
import { useVoiceRecorder } from '../../hooks/useVoiceRecorder';
import { useToast } from '../../hooks/use-toast';

export function ConversationInput() {
  const [value, setValue] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const setAIState = useJarvisStore((s) => s.setAIState);
  const aiState = useJarvisStore((s) => s.aiState);
  const { toast } = useToast();
  
  // Track if we should auto-send after recording stops
  const shouldAutoSend = useRef(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
    // reset input so same file can be selected again
    e.target.value = '';
  };

  const removeFile = (idx: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSend = useCallback(async (textToSend: string = value, isVoiceInteraction: boolean = false) => {
    let finalMessage = textToSend.trim();
    if (!finalMessage && selectedFiles.length === 0) return;

    let userDisplayMessage = finalMessage;
    if (selectedFiles.length > 0) {
      userDisplayMessage += `\n\n[Attached ${selectedFiles.length} file(s)]`;
      
      const fileContents = await Promise.all(selectedFiles.map(async (file) => {
        return new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            const content = e.target?.result as string;
            resolve(`\n\n--- File: ${file.name} ---\n${content}\n--- End of ${file.name} ---`);
          };
          reader.onerror = () => resolve(`\n\n--- File: ${file.name} (Could not read) ---`);
          
          if (file.type.startsWith('image/') || file.type.startsWith('video/') || file.type.startsWith('audio/')) {
            reader.readAsDataURL(file);
          } else {
            reader.readAsText(file);
          }
        });
      }));
      finalMessage += fileContents.join('');
    }

    if (!finalMessage.trim()) return;

    setValue('');
    setSelectedFiles([]);
    setAIState('thinking');

    const store = useJarvisStore.getState();
    store.addMessage(userDisplayMessage, true);
    store.addLog({ message: `User command received${selectedFiles.length > 0 ? ` with ${selectedFiles.length} files` : ''}.` });

    const result = await apiFetch<{ content: string; provider?: string; model?: string }>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: finalMessage, stream: false })
    });

    if (result.ok && result.data.content) {
      setAIState('idle');
      store.addMessage(result.data.content, false);
      store.addLog({ message: 'Command executed successfully.' });
      
      if (isVoiceInteraction) {
        store.addLog({ message: 'Synthesizing voice response...' });
        try {
          const ttsResult = await apiFetch<{ audio_base64: string; format: string }>('/api/voice/speak', {
            method: 'POST',
            body: JSON.stringify({ text: result.data.content, voice: 'en-US-GuyNeural' })
          });
          if (ttsResult.ok && ttsResult.data.audio_base64) {
            const audio = new Audio(`data:audio/${ttsResult.data.format};base64,${ttsResult.data.audio_base64}`);
            audio.play().catch(e => console.error("Audio play failed:", e));
          }
        } catch (e) {
          console.error("TTS fetch failed:", e);
        }
      }

      if (store.aiState === 'error') {
        setAIState('idle');
      }
    } else if (!result.ok) {
      setAIState('idle');
      store.addMessage('I am JARVIS. I am currently running in offline demo mode. Please start the backend server to enable AI capabilities.', false);
      store.addLog({ message: 'Backend not reachable — running in offline mode.', type: 'warning' });
    }
  }, [value, selectedFiles, setAIState]);

  const initialTextRef = useRef('');

  const { isRecording, startRecording, stopRecording, error } = useVoiceRecorder((text: string) => {
    const finalVal = (initialTextRef.current ? initialTextRef.current + ' ' : '') + text;
    setValue(finalVal);
    
    if (shouldAutoSend.current) {
      shouldAutoSend.current = false;
      if (finalVal.trim() || selectedFiles.length > 0) {
        handleSend(finalVal, true);
      }
    }
  });

  useEffect(() => {
    if (error) {
      toast({
        title: "Voice Error",
        description: error,
        variant: "destructive"
      });
      if (aiState === 'listening') setAIState('idle');
    }
  }, [error, toast, aiState, setAIState]);

  useEffect(() => {
    if (isRecording && aiState !== 'listening') {
      setAIState('listening');
    } else if (!isRecording && aiState === 'listening') {
      // It will quickly transition to 'thinking' if auto-sending, otherwise idle
      setAIState('idle');
    }
  }, [isRecording, aiState, setAIState]);

  const toggleRecording = async () => {
    if (isRecording) {
      shouldAutoSend.current = true;
      await stopRecording();
    } else {
      shouldAutoSend.current = false;
      initialTextRef.current = value;
      await startRecording();
    }
  };

  useEffect(() => {
    if (!isRecording && shouldAutoSend.current) {
      shouldAutoSend.current = false;
      if (value.trim() || selectedFiles.length > 0) {
        handleSend(value, true);
      }
    }
  }, [isRecording, value, selectedFiles.length, handleSend]);
  const isGenerating = aiState === 'thinking' || aiState === 'executing' || aiState === 'listening';

  return (
    <motion.div 
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.4 }}
      className="absolute bottom-12 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-20"
    >
      <div className="relative group">
        
        {/* Selected Files Row */}
        <AnimatePresence>
          {selectedFiles.length > 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: 10, height: 0 }}
              className="absolute bottom-full left-0 mb-3 flex flex-wrap gap-2 w-full"
            >
              {selectedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center gap-1.5 bg-[rgba(10,15,30,0.8)] backdrop-blur-xl border border-[rgba(255,255,255,0.1)] px-3 py-1.5 rounded-lg shadow-xl">
                  <FileIcon size={12} className="text-[var(--accent-cyan)]" />
                  <span className="text-xs text-zinc-300 max-w-[150px] truncate">{file.name}</span>
                  <button 
                    onClick={() => removeFile(idx)}
                    className="ml-1 text-zinc-500 hover:text-red-400 transition-colors"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Animated border glow */}
        <div className={`absolute -inset-0.5 rounded-2xl blur-md opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200 ${isGenerating || isRecording ? 'bg-gradient-to-r from-[var(--accent-cyan)] via-[var(--accent-violet)] to-[var(--accent-cyan)] animate-pulse' : 'bg-[var(--accent-cyan)]'}`} />
        
        <div className="relative flex items-center bg-[rgba(10,15,30,0.6)] backdrop-blur-xl border border-[rgba(255,255,255,0.1)] rounded-2xl p-2 shadow-2xl">
          
          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple 
            accept="*/*"
            className="hidden" 
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="p-3 text-zinc-400 hover:text-[var(--accent-cyan)] transition-colors rounded-xl hover:bg-[rgba(255,255,255,0.05)]"
          >
            <Paperclip size={20} />
          </button>
          
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isRecording ? "Listening..." : (isGenerating ? "Processing instruction..." : "Ask Jarvis anything...")}
            disabled={isGenerating || isRecording}
            className="flex-1 bg-transparent border-none outline-none text-white placeholder-zinc-500 px-2 font-medium tracking-wide disabled:opacity-50"
          />
          
          <div className="flex items-center gap-2 pr-1">
            <button 
              onClick={toggleRecording}
              disabled={isGenerating && !isRecording}
              className={`p-3 transition-colors rounded-xl ${isRecording ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.4)] animate-pulse' : 'text-zinc-400 hover:text-[var(--accent-cyan)] hover:bg-[rgba(255,255,255,0.05)]'} disabled:opacity-50`}
            >
              {isRecording ? <Square size={20} className="fill-current" /> : <Mic size={20} />}
            </button>
            <button 
              onClick={() => handleSend(value)}
              disabled={isGenerating || (!value.trim() && !isRecording && selectedFiles.length === 0)}
              className={`p-3 rounded-xl transition-all duration-300 ${(value.trim() || isRecording || selectedFiles.length > 0) && !isGenerating ? 'bg-[var(--accent-cyan)] text-black shadow-[0_0_15px_rgba(0,212,255,0.4)]' : 'bg-[rgba(255,255,255,0.05)] text-zinc-500'}`}
            >
              <Send size={20} className={(value.trim() || isRecording || selectedFiles.length > 0) && !isGenerating ? 'translate-x-0.5 -translate-y-0.5' : ''} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}