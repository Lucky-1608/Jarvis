import { useState, useRef, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Mic, Volume2, Download, Trash2, Settings2, Activity, MessageSquare, Square, Play, WifiOff, Loader2 } from 'lucide-react';
import { api, getBaseUrl } from '../lib/api';

interface TranscriptEntry {
  id: string;
  speaker: 'USER' | 'JARVIS';
  text: string;
  time: string;
  conf?: number;
}

export function VoicePage() {
  const [isRecording, setIsRecording] = useState(false);
  const [ttsText, setTtsText] = useState('');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [voices, setVoices] = useState<{ name: string; gender: string }[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('en-US-GuyNeural');
  const [sttResult, setSttResult] = useState<string>('');
  const [ttsLoading, setTtsLoading] = useState(false);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  // Check backend on mount
  useEffect(() => {
    api.get<any>('/api/voice/voices').then(res => {
      if (res.ok) {
        setBackendConnected(true);
        if (res.data.voices) {
          setVoices(res.data.voices);
        }
      } else {
        setBackendConnected(false);
      }
    });
  }, []);

  // -- Microphone recording (STT) -------------------------------------------

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks.current = [];

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4',
      });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Stop all tracks on the stream
        stream.getTracks().forEach(t => t.stop());

        const blob = new Blob(audioChunks.current, { type: recorder.mimeType });
        await transcribeAudio(blob);
      };

      recorder.start();
      mediaRecorder.current = recorder;
      setIsRecording(true);
      toast({ title: 'Recording', description: 'Microphone active. Speak now...' });
    } catch (err: any) {
      toast({ title: 'Mic Error', description: err?.message || 'Cannot access microphone.' });
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
      mediaRecorder.current.stop();
      setIsRecording(false);
    }
  }, []);

  const transcribeAudio = async (blob: Blob) => {
    const formData = new FormData();
    formData.append('file', blob, 'recording.webm');

    try {
      const base = await getBaseUrl();
      const res = await fetch(`${base}/api/voice/transcribe`, {
        method: 'POST',
        headers: { 'X-API-Key': 'JARVIS_DEV_KEY' },
        body: formData,
      });
      const data = await res.json();
      if (data.text) {
        const text = data.text.trim();
        const entry: TranscriptEntry = {
          id: Math.random().toString(36).slice(2, 8),
          speaker: 'USER',
          text,
          time: new Date().toLocaleTimeString(),
        };
        setTranscripts(prev => [...prev, entry]);
        setSttResult(text);
        await runJarvisCommand(text);
      } else {
        toast({ title: 'No speech detected', description: 'Try speaking louder or closer to the mic.' });
      }
    } catch {
      toast({ title: 'Backend not connected', description: 'Cannot transcribe without backend API.' });
    }
  };

  const runJarvisCommand = async (text: string) => {
    const res = await api.post<any>('/api/chat', {
      message: text,
      stream: false,
    });

    if (!res.ok) {
      setBackendConnected(res.status !== 0);
      toast({ title: 'Command failed', description: res.detail || 'Jarvis could not process the voice command.' });
      return;
    }

    setBackendConnected(true);
    const reply = res.data.content || 'Done.';
    setTranscripts(prev => [...prev, {
      id: Math.random().toString(36).slice(2, 8),
      speaker: 'JARVIS',
      text: reply,
      time: new Date().toLocaleTimeString(),
    }]);
    setTtsText(reply);

    const speech = await api.post<{ audio_base64: string }>('/api/voice/speak', {
      text: reply,
      voice: selectedVoice,
    });
    if (speech.ok && speech.data.audio_base64) {
      const audio = new Audio(`data:audio/mp3;base64,${speech.data.audio_base64}`);
      await audio.play();
    }
  };

  // -- TTS (Speak) -----------------------------------------------------------

  const handleSpeak = async () => {
    if (!ttsText.trim()) return;
    setTtsLoading(true);
    const res = await api.post<{ audio_base64: string }>('/api/voice/speak', {
      text: ttsText,
      voice: selectedVoice,
    });
    if (res.ok && res.data.audio_base64) {
      const audio = new Audio(`data:audio/mp3;base64,${res.data.audio_base64}`);
      await audio.play();
      setTranscripts(prev => [...prev, {
        id: Math.random().toString(36).slice(2, 8),
        speaker: 'JARVIS',
        text: ttsText,
        time: new Date().toLocaleTimeString(),
      }]);
      toast({ title: 'Playing Audio', description: 'TTS synthesis complete.' });
    } else if (!res.ok) {
      toast({ title: 'Backend not connected', description: 'Cannot synthesize speech without backend.' });
    }
    setTtsLoading(false);
  };

  // -- Helpers ---------------------------------------------------------------

  const clearTranscript = () => {
    setTranscripts([]);
    setSttResult('');
    toast({ title: 'Cleared', description: 'Transcript history cleared.' });
  };

  const wordCount = transcripts.reduce((sum, t) => sum + t.text.split(/\s+/).filter(Boolean).length, 0);

  return (
    <PageShell>
      <PageHeader
        title="Voice Interface"
        description="Real-time audio processing and synthesis"
        actions={
          <button
            onClick={() => {
              if (backendConnected) {
                toast({ title: 'Voice Settings', description: `Default voice: ${selectedVoice}. ${voices.length} voices available.` });
              } else {
                toast({ title: 'Backend not connected', description: 'Start the backend to configure voice settings.' });
              }
            }}
            className="p-2 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-white rounded-md hover:bg-[rgba(255,255,255,0.1)] transition-colors">
            <Settings2 size={16} />
          </button>
        }
      />

      {/* Backend offline banner */}
      {backendConnected === false && (
        <div className="mx-6 -mt-4 mb-2 flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
          <WifiOff size={16} />
          <span className="font-medium">Backend offline</span>
          <span className="text-red-400/70 text-xs">Voice features need the backend running on port 8000</span>
        </div>
      )}

      <div className="flex-1 flex flex-col xl:flex-row p-6 gap-6 max-w-6xl mx-auto w-full h-full">

        {/* Left Column - Audio Controls */}
        <div className="w-full md:w-[40%] flex flex-col gap-6">

          {/* Main Mic Panel */}
          <div className="bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-xl p-8 flex flex-col items-center justify-center relative overflow-hidden">
            <div className="absolute top-4 left-4 text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold flex items-center gap-2">
              <Activity size={12} className={isRecording ? 'text-red-400 animate-pulse' : ''} /> {isRecording ? 'RECORDING' : 'INPUT STREAM'}
            </div>

            <div className="my-10 relative">
              {isRecording && (
                <motion.div
                  className="absolute inset-0 bg-red-500 rounded-full blur-2xl opacity-20"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.2, 0.4, 0.2] }}
                  transition={{ repeat: Infinity, duration: 2 }}
                />
              )}

              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`w-32 h-32 rounded-full flex items-center justify-center relative z-10 transition-all duration-500 shadow-2xl ${
                  isRecording
                    ? 'bg-[rgba(239,68,68,0.15)] border-2 border-red-500 text-red-500 shadow-[0_0_30px_rgba(239,68,68,0.3)]'
                    : 'bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-zinc-400 hover:text-white hover:bg-[rgba(255,255,255,0.08)]'
                }`}
              >
                {isRecording ? <Square size={32} /> : <Mic size={48} />}
              </button>
            </div>

            {sttResult && (
              <div className="w-full mt-2 px-4 py-2 bg-[rgba(0,0,0,0.4)] border border-[rgba(255,255,255,0.05)] rounded-lg text-xs text-zinc-300 text-center">
                "{sttResult}"
              </div>
            )}

            {/* Visualizer bars */}
            <div className="flex items-end justify-center gap-1 h-12 w-full mt-4">
              {Array.from({ length: 15 }).map((_, i) => (
                <motion.div
                  key={i}
                  className={`w-2 rounded-t-sm ${isRecording ? 'bg-red-400' : 'bg-zinc-800'}`}
                  animate={isRecording ? { height: ['20%', '80%', '40%', '100%', '30%'] } : { height: '10%' }}
                  transition={isRecording ? { repeat: Infinity, duration: 0.5 + Math.random(), ease: "easeInOut", times: [0, 0.2, 0.5, 0.8, 1] } : {}}
                />
              ))}
            </div>
          </div>

          {/* TTS Panel */}
          <div className="bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-xl p-5 flex flex-col flex-1">
            <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-4 flex items-center gap-2"><Volume2 size={14} /> Text to Speech</h3>

            {/* Voice selector */}
            <div className="flex items-center gap-2 mb-3">
              <select
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                className="flex-1 bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-[var(--accent-violet)]"
              >
                {voices.length > 0 ? voices.map(v => (
                  <option key={v.name} value={v.name}>{v.name} ({v.gender})</option>
                )) : (
                  <option value="en-US-GuyNeural">en-US-GuyNeural (Default)</option>
                )}
              </select>
              <span className="text-[10px] text-zinc-500">Voice</span>
            </div>

            <textarea
              value={ttsText}
              onChange={(e) => setTtsText(e.target.value)}
              placeholder="Enter text for Jarvis to synthesize..."
              className="flex-1 min-h-[80px] bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded-lg p-3 text-sm text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-[var(--accent-violet)] transition-colors mb-4"
            />

            <div className="flex items-center justify-between">
              <div className="flex gap-2 text-[10px] text-zinc-500">
                <span className="px-2 py-1 bg-[rgba(255,255,255,0.05)] rounded border border-[rgba(255,255,255,0.05)]">{ttsText.length} chars</span>
              </div>
              <button
                onClick={handleSpeak}
                disabled={ttsLoading || !ttsText.trim()}
                className="px-4 py-2 bg-[var(--accent-violet)] text-white rounded font-medium text-sm hover:bg-violet-500 transition-colors shadow-[0_0_15px_rgba(124,58,237,0.3)] disabled:opacity-50 flex items-center gap-2"
              >
                {ttsLoading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                Speak
              </button>
            </div>
          </div>
        </div>

        {/* Right Column - Transcript */}
        <div className="w-full md:w-[60%] flex flex-col">
          <div className="flex-1 bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-xl flex flex-col overflow-hidden">

            {/* Header */}
            <div className="p-4 border-b border-[rgba(255,255,255,0.05)] flex items-center justify-between bg-[rgba(0,0,0,0.2)]">
              <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold flex items-center gap-2"><MessageSquare size={14} /> Live Session</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    const text = transcripts.map(t => `[${t.speaker}] ${t.text}`).join('\n');
                    if (text) {
                      navigator.clipboard.writeText(text).then(() =>
                        toast({ title: 'Exported', description: 'Transcript copied to clipboard.' })
                      );
                    } else {
                      toast({ title: 'Nothing to export', description: 'No transcript entries yet.' });
                    }
                  }}
                  className="p-1.5 text-zinc-400 hover:text-white transition-colors" title="Export transcript"><Download size={14} /></button>
                <button
                  onClick={clearTranscript}
                  className="p-1.5 text-zinc-400 hover:text-red-400 transition-colors" title="Clear transcript"><Trash2 size={14} /></button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {transcripts.length === 0 && !isRecording && (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <Volume2 size={32} className="mb-3 opacity-20" />
                  <span className="text-xs">Tap the microphone to start speaking,</span>
                  <span className="text-xs">or type text below and click Speak.</span>
                </div>
              )}
              {transcripts.map(msg => (
                <div key={msg.id} className={`flex flex-col ${msg.speaker === 'USER' ? 'items-end' : 'items-start'}`}>
                  <div className={`text-[10px] font-bold mb-1 flex items-center gap-2 ${msg.speaker === 'USER' ? 'text-[var(--accent-cyan)] flex-row-reverse' : 'text-[var(--accent-violet)]'}`}>
                    {msg.speaker} <span className="text-zinc-600 font-normal">{msg.time}</span>
                  </div>
                  <div className={`max-w-[80%] p-3 rounded-xl text-sm leading-relaxed ${
                    msg.speaker === 'USER' ? 'bg-[rgba(0,212,255,0.1)] text-white border border-[rgba(0,212,255,0.2)] rounded-tr-sm' :
                    'bg-[rgba(255,255,255,0.05)] text-zinc-200 border border-[rgba(255,255,255,0.05)] rounded-tl-sm'
                  }`}>
                    {msg.text}
                  </div>
                  {msg.conf && (
                    <div className="w-16 h-0.5 mt-1 bg-zinc-800 rounded overflow-hidden ml-1">
                       <div className="h-full bg-[var(--accent-violet)]" style={{width: `${msg.conf}%`}} />
                    </div>
                  )}
                </div>
              ))}

              {isRecording && (
                <div className="flex flex-col items-end">
                  <div className="text-[10px] font-bold mb-1 flex items-center gap-2 text-red-400 flex-row-reverse">
                    USER <span className="text-zinc-600 font-normal">Recording...</span>
                  </div>
                  <div className="max-w-[80%] p-3 rounded-xl bg-[rgba(239,68,68,0.05)] border border-dashed border-red-500/30 rounded-tr-sm flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" />
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" style={{animationDelay: '100ms'}} />
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" style={{animationDelay: '200ms'}} />
                  </div>
                </div>
              )}
            </div>

            {/* Stats Footer */}
            <div className="p-3 border-t border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.3)] flex justify-between text-[10px] font-mono text-zinc-500">
              <span className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${backendConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                {backendConnected ? 'ONLINE' : 'OFFLINE'}
              </span>
              <span>WORDS: {wordCount}</span>
              <span>SEGMENTS: {transcripts.length}</span>
              <span>VOICE: {selectedVoice.split('-')[2] || 'Guy'}</span>
            </div>

          </div>
        </div>

      </div>
    </PageShell>
  );
}
