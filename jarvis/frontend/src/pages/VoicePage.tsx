import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Download,
  Trash2,
  Settings2,
  Activity,
  MessageSquare,
  Square,
  Play,
  Pause,
  WifiOff,
  Loader2,
  Sparkles,
  Radio,
  RotateCcw
} from 'lucide-react';
import { api } from '../lib/api';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';

interface TranscriptEntry {
  id: string;
  speaker: 'USER' | 'JARVIS';
  text: string;
  time: string;
  audioBase64?: string;
}

export function VoicePage() {
  const [ttsText, setTtsText] = useState('');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [voices, setVoices] = useState<{ name: string; gender: string; locale?: string }[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('en-US-GuyNeural');
  const [ttsLoading, setTtsLoading] = useState(false);
  const [isJarvisThinking, setIsJarvisThinking] = useState(false);
  const [isJarvisSpeaking, setIsJarvisSpeaking] = useState(false);
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(() => {
    return localStorage.getItem('JARVIS_VOICE_OUTPUT') !== 'false';
  });
  const [handsFreeMode, setHandsFreeMode] = useState(false);

  // Audio playback ref
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const processUserSpeechRef = useRef<(text: string) => Promise<void>>(async () => {});
  const isProcessingSpeechRef = useRef(false);

  const submitVoiceSpeech = useCallback(async (text: string) => {
    if (isProcessingSpeechRef.current) return;
    if (text && text.trim()) {
      isProcessingSpeechRef.current = true;
      try {
        await processUserSpeechRef.current(text.trim());
      } finally {
        isProcessingSpeechRef.current = false;
      }
    }
  }, []);

  // Real-time voice recorder hook with automatic pause/stop detection
  const {
    isRecording,
    transcript,
    interimTranscript,
    fullTranscript,
    audioLevel,
    startRecording,
    stopRecording,
    cancelRecording,
    error: micError,
  } = useVoiceRecorder({
    autoStopOnSilence: true,
    silenceDurationMs: 2200,
    onSilence: (finalText: string) => {
      submitVoiceSpeech(finalText);
    },
  });

  // Check backend and load voices on mount
  useEffect(() => {
    api.get<any>('/api/voice/voices').then(res => {
      if (res.ok) {
        setBackendConnected(true);
        if (res.data?.voices && res.data.voices.length > 0) {
          setVoices(res.data.voices);
          // Default to GuyNeural or first voice
          const hasGuy = res.data.voices.some((v: any) => v.name === 'en-US-GuyNeural');
          if (hasGuy) {
            setSelectedVoice('en-US-GuyNeural');
          } else {
            setSelectedVoice(res.data.voices[0].name);
          }
        }
      } else {
        setBackendConnected(false);
      }
    });
  }, []);

  // Sync voice output setting to localStorage
  const toggleVoiceOutput = () => {
    const next = !voiceOutputEnabled;
    setVoiceOutputEnabled(next);
    localStorage.setItem('JARVIS_VOICE_OUTPUT', String(next));
    if (!next && currentAudioRef.current) {
      currentAudioRef.current.pause();
      setIsJarvisSpeaking(false);
    }
    toast({
      title: next ? 'Voice Output Enabled' : 'Voice Output Muted',
      description: next ? 'Jarvis will speak responses aloud.' : 'Responses will be text only.',
    });
  };

  // Stop speaking
  const stopJarvisSpeech = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsJarvisSpeaking(false);
  }, []);

  // Speak text using backend TTS with SpeechSynthesis fallback
  const speakText = useCallback(async (text: string): Promise<string | undefined> => {
    if (!voiceOutputEnabled || !text || !text.trim()) return undefined;

    stopJarvisSpeech();
    setIsJarvisSpeaking(true);

    try {
      const res = await api.post<{ audio_base64: string; format?: string }>('/api/voice/speak', {
        text,
        voice: selectedVoice,
      });

      if (res.ok && res.data?.audio_base64) {
        const mime = res.data.format === 'wav' ? 'audio/wav' : 'audio/mpeg';
        const audio = new Audio(`data:${mime};base64,${res.data.audio_base64}`);
        currentAudioRef.current = audio;

        audio.onended = () => {
          setIsJarvisSpeaking(false);
          // If in continuous hands-free mode, resume listening after speaking
          if (handsFreeMode && !isRecording) {
            startRecording();
          }
        };

        audio.onerror = () => {
          setIsJarvisSpeaking(false);
        };

        await audio.play().catch(err => {
          console.warn('HTML5 audio play blocked, falling back to Web Speech synthesis:', err);
          if ('speechSynthesis' in window) {
            const utter = new SpeechSynthesisUtterance(text);
            utter.onend = () => setIsJarvisSpeaking(false);
            window.speechSynthesis.speak(utter);
          } else {
            setIsJarvisSpeaking(false);
          }
        });

        return res.data.audio_base64;
      } else if ('speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(text);
        utter.onend = () => setIsJarvisSpeaking(false);
        window.speechSynthesis.speak(utter);
      } else {
        setIsJarvisSpeaking(false);
      }
    } catch (err) {
      console.warn('Speech synthesis error:', err);
      if ('speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(text);
        utter.onend = () => setIsJarvisSpeaking(false);
        window.speechSynthesis.speak(utter);
      } else {
        setIsJarvisSpeaking(false);
      }
    }
    return undefined;
  }, [voiceOutputEnabled, selectedVoice, stopJarvisSpeech, handsFreeMode, isRecording, startRecording]);

  // Execute Jarvis command from speech
  const processUserSpeech = useCallback(async (spokenText: string) => {
    if (!spokenText.trim()) return;

    // Add user message to session
    const userMsgId = Math.random().toString(36).slice(2, 8);
    setTranscripts(prev => [
      ...prev,
      {
        id: userMsgId,
        speaker: 'USER',
        text: spokenText.trim(),
        time: new Date().toLocaleTimeString(),
      },
    ]);

    setIsJarvisThinking(true);

    try {
      const res = await api.post<any>('/api/chat', {
        message: spokenText.trim(),
        stream: false,
      });

      setIsJarvisThinking(false);

      if (!res.ok) {
        setBackendConnected(res.status !== 0);
        const errorReply = res.detail || 'Jarvis could not process the voice command.';
        setTranscripts(prev => [
          ...prev,
          {
            id: Math.random().toString(36).slice(2, 8),
            speaker: 'JARVIS',
            text: errorReply,
            time: new Date().toLocaleTimeString(),
          },
        ]);
        toast({ title: 'Command error', description: errorReply, variant: 'destructive' });
        return;
      }

      setBackendConnected(true);
      const reply = res.data?.content || 'Understood.';
      const jarvisMsgId = Math.random().toString(36).slice(2, 8);

      setTranscripts(prev => [
        ...prev,
        {
          id: jarvisMsgId,
          speaker: 'JARVIS',
          text: reply,
          time: new Date().toLocaleTimeString(),
        },
      ]);

      // Speak response aloud
      const audioB64 = await speakText(reply);
      if (audioB64) {
        setTranscripts(prev =>
          prev.map(t => (t.id === jarvisMsgId ? { ...t, audioBase64: audioB64 } : t))
        );
      }
    } catch (err: any) {
      setIsJarvisThinking(false);
      toast({ title: 'Error', description: err?.message || 'Failed to reach Jarvis assistant.' });
    }
  }, [speakText]);

  processUserSpeechRef.current = processUserSpeech;

  // Stop recording and process
  const handleStopAndProcess = useCallback(async () => {
    const finalSpoken = await stopRecording();
    if (finalSpoken && finalSpoken.trim()) {
      await submitVoiceSpeech(finalSpoken);
    }
  }, [stopRecording, submitVoiceSpeech]);

  // Toggle record button
  const handleToggleRecord = useCallback(() => {
    if (isRecording) {
      handleStopAndProcess();
    } else {
      isProcessingSpeechRef.current = false;
      stopJarvisSpeech();
      startRecording();
    }
  }, [isRecording, handleStopAndProcess, stopJarvisSpeech, startRecording]);

  // Handle manual TTS test
  const handleManualSpeak = async () => {
    if (!ttsText.trim()) return;
    setTtsLoading(true);
    await speakText(ttsText);
    setTranscripts(prev => [
      ...prev,
      {
        id: Math.random().toString(36).slice(2, 8),
        speaker: 'JARVIS',
        text: ttsText,
        time: new Date().toLocaleTimeString(),
      },
    ]);
    setTtsLoading(false);
  };

  // Clear transcripts
  const clearTranscript = () => {
    setTranscripts([]);
    toast({ title: 'Cleared', description: 'Transcript history cleared.' });
  };

  const wordCount = transcripts.reduce(
    (sum, t) => sum + t.text.split(/\s+/).filter(Boolean).length,
    0
  );

  return (
    <PageShell>
      <PageHeader
        title="Real-Time Voice Interface"
        description="Live speech-to-text transcription with continuous neural voice synthesis"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={toggleVoiceOutput}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                voiceOutputEnabled
                  ? 'bg-violet-500/10 border-violet-500/30 text-violet-300 hover:bg-violet-500/20'
                  : 'bg-zinc-800/60 border-zinc-700/50 text-zinc-400 hover:text-zinc-200'
              }`}
              title={voiceOutputEnabled ? 'Mute voice responses' : 'Enable voice responses'}
            >
              {voiceOutputEnabled ? <Volume2 size={14} className="text-violet-400" /> : <VolumeX size={14} />}
              <span>{voiceOutputEnabled ? 'Voice Out ON' : 'Voice Out Muted'}</span>
            </button>

            <button
              onClick={() => {
                const next = !handsFreeMode;
                setHandsFreeMode(next);
                toast({
                  title: next ? 'Hands-Free Mode Active' : 'Push-to-Talk Mode',
                  description: next
                    ? 'Jarvis auto-processes when you pause speaking.'
                    : 'Click microphone to start and stop recording.',
                });
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                handsFreeMode
                  ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
                  : 'bg-zinc-800/60 border-zinc-700/50 text-zinc-400'
              }`}
            >
              <Radio size={14} className={handsFreeMode ? 'text-cyan-400 animate-pulse' : ''} />
              <span>{handsFreeMode ? 'Hands-Free' : 'Push-to-Talk'}</span>
            </button>
          </div>
        }
      />

      {/* Backend offline warning banner */}
      {backendConnected === false && (
        <div className="mx-6 -mt-4 mb-3 flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
          <WifiOff size={16} />
          <span className="font-medium">Backend offline</span>
          <span className="text-red-400/70 text-xs">
            Start backend with <code className="bg-red-950/60 px-1 py-0.5 rounded">jarvis serve --reload</code> for neural STT & TTS.
          </span>
        </div>
      )}

      {/* Mic error banner */}
      {micError && (
        <div className="mx-6 -mt-2 mb-3 flex items-center gap-3 px-4 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300">
          <MicOff size={14} />
          <span>Microphone access warning: {micError}</span>
        </div>
      )}

      <div className="flex-1 flex flex-col xl:flex-row p-6 gap-6 max-w-6xl mx-auto w-full h-full">

        {/* Left Column: Voice Orb, Live Transcription, & Speech Output Controls */}
        <div className="w-full xl:w-[45%] flex flex-col gap-5">

          {/* Core Interactive Voice Console */}
          <div className="bg-[rgba(6,12,24,0.7)] backdrop-blur-md border border-[rgba(255,255,255,0.08)] rounded-2xl p-7 flex flex-col items-center justify-center relative overflow-hidden shadow-2xl">
            {/* Ambient status header */}
            <div className="w-full flex items-center justify-between text-[11px] uppercase tracking-widest font-mono text-zinc-400 mb-2">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${isRecording ? 'bg-red-500 animate-ping' : isJarvisSpeaking ? 'bg-cyan-400 animate-pulse' : 'bg-green-500'}`} />
                <span>
                  {isRecording
                    ? 'LISTENING (LIVE STT)'
                    : isJarvisThinking
                    ? 'JARVIS THINKING...'
                    : isJarvisSpeaking
                    ? 'JARVIS SPEAKING'
                    : 'CORE READY'}
                </span>
              </div>
              <span className="text-[10px] text-zinc-500">
                {handsFreeMode ? 'AUTO-DETECT SILENCE' : 'TAP TO RECORD'}
              </span>
            </div>

            {/* Central Glowing Reactor Orb */}
            <div className="my-8 relative flex items-center justify-center">
              {/* Outer pulsing ring responsive to audioLevel */}
              {isRecording && (
                <>
                  <motion.div
                    className="absolute rounded-full bg-red-500/20 blur-xl"
                    style={{
                      width: `${160 + audioLevel * 120}px`,
                      height: `${160 + audioLevel * 120}px`,
                    }}
                    transition={{ ease: 'easeOut', duration: 0.1 }}
                  />
                  <motion.div
                    className="absolute rounded-full border border-red-500/40"
                    style={{
                      width: `${140 + audioLevel * 80}px`,
                      height: `${140 + audioLevel * 80}px`,
                    }}
                  />
                </>
              )}

              {isJarvisSpeaking && (
                <motion.div
                  className="absolute rounded-full bg-cyan-500/20 blur-2xl"
                  animate={{ scale: [1, 1.25, 1], opacity: [0.3, 0.7, 0.3] }}
                  transition={{ repeat: Infinity, duration: 1.6 }}
                  style={{ width: '180px', height: '180px' }}
                />
              )}

              {/* Main Core Button */}
              <button
                onClick={handleToggleRecord}
                className={`w-32 h-32 rounded-full flex flex-col items-center justify-center relative z-10 transition-all duration-300 shadow-2xl cursor-pointer ${
                  isRecording
                    ? 'bg-red-500/20 border-2 border-red-500 text-red-400 shadow-[0_0_40px_rgba(239,68,68,0.4)] scale-105'
                    : isJarvisSpeaking
                    ? 'bg-cyan-500/20 border-2 border-cyan-400 text-cyan-300 shadow-[0_0_35px_rgba(6,182,212,0.4)]'
                    : 'bg-zinc-900/80 border border-zinc-700/50 text-zinc-300 hover:text-white hover:border-violet-500/50 hover:bg-violet-950/20 shadow-[0_0_20px_rgba(0,0,0,0.5)]'
                }`}
              >
                {isRecording ? (
                  <>
                    <Square size={36} className="text-red-400 fill-current" />
                    <span className="text-[10px] font-mono mt-1 tracking-wider text-red-300">STOP</span>
                  </>
                ) : isJarvisSpeaking ? (
                  <>
                    <Volume2 size={40} className="text-cyan-400 animate-pulse" />
                    <span className="text-[10px] font-mono mt-1 tracking-wider text-cyan-300">SPEAKING</span>
                  </>
                ) : isJarvisThinking ? (
                  <>
                    <Loader2 size={38} className="text-violet-400 animate-spin" />
                    <span className="text-[10px] font-mono mt-1 tracking-wider text-violet-300">THINKING</span>
                  </>
                ) : (
                  <>
                    <Mic size={42} className="text-zinc-300 group-hover:text-white" />
                    <span className="text-[10px] font-mono mt-1 tracking-wider text-zinc-400">SPEAK</span>
                  </>
                )}
              </button>
            </div>

            {/* Real-Time Live Speech Output Display */}
            <div className="w-full min-h-[56px] px-4 py-3 bg-[rgba(0,0,0,0.5)] border border-[rgba(255,255,255,0.06)] rounded-xl flex items-center justify-center text-center">
              {isRecording ? (
                <div className="text-sm font-medium text-white leading-relaxed">
                  {transcript && <span>{transcript} </span>}
                  {interimTranscript ? (
                    <span className="text-cyan-400 bg-cyan-950/30 px-1 rounded animate-pulse">
                      {interimTranscript}
                    </span>
                  ) : (
                    !transcript && <span className="text-zinc-500 italic">Listening... Speak now</span>
                  )}
                </div>
              ) : isJarvisSpeaking ? (
                <div className="flex items-center justify-between w-full px-2">
                  <div className="flex items-center gap-2 text-xs text-cyan-300">
                    <Activity size={14} className="animate-bounce" />
                    <span>Jarvis is speaking...</span>
                  </div>
                  <button
                    onClick={stopJarvisSpeech}
                    className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-[11px] font-medium transition-colors"
                  >
                    Interrupt
                  </button>
                </div>
              ) : isRecording ? (
                <div className="flex items-center justify-between text-xs text-amber-300">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                    <span>{fullTranscript ? `"${fullTranscript}"` : 'Listening... pause or stop talking to finish'}</span>
                  </div>
                </div>
              ) : fullTranscript ? (
                <div className="text-xs text-zinc-300">
                  <span className="text-zinc-500 mr-1.5 font-mono">Heard:</span>
                  "{fullTranscript}"
                </div>
              ) : (
                <span className="text-xs text-zinc-500">
                  Click the microphone or say a command to Jarvis
                </span>
              )}
            </div>

            {/* Dynamic frequency wave visualizer */}
            <div className="flex items-end justify-center gap-1.5 h-10 w-full mt-5">
              {Array.from({ length: 18 }).map((_, i) => {
                const heightPct = isRecording
                  ? Math.max(15, Math.min(100, Math.round(audioLevel * 100 * (1 + Math.sin(i * 0.5)))))
                  : isJarvisSpeaking
                  ? Math.max(20, Math.round(40 + 35 * Math.sin(i + Date.now() / 200)))
                  : 8;

                return (
                  <motion.div
                    key={i}
                    className={`w-1.5 rounded-full transition-all duration-75 ${
                      isRecording
                        ? 'bg-gradient-to-t from-red-500 to-amber-400'
                        : isJarvisSpeaking
                        ? 'bg-gradient-to-t from-cyan-500 to-violet-400'
                        : 'bg-zinc-800'
                    }`}
                    style={{ height: `${heightPct}%` }}
                  />
                );
              })}
            </div>
          </div>

          {/* Speech Synthesis (TTS) & Voice Settings Console */}
          <div className="bg-[rgba(6,12,24,0.7)] backdrop-blur-md border border-[rgba(255,255,255,0.08)] rounded-2xl p-5 flex flex-col shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs uppercase tracking-wider font-semibold text-zinc-300 flex items-center gap-2">
                <Volume2 size={15} className="text-violet-400" />
                <span>Text-to-Speech Output</span>
              </h3>
              <span className="text-[10px] text-zinc-500 font-mono">NEURAL TTS</span>
            </div>

            {/* Voice selector */}
            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-zinc-400 font-medium">Select Output Voice</label>
                <select
                  value={selectedVoice}
                  onChange={e => setSelectedVoice(e.target.value)}
                  className="bg-zinc-900/90 border border-zinc-700/60 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-violet-500 transition-colors"
                >
                  {voices.length > 0 ? (
                    voices.map(v => (
                      <option key={v.name} value={v.name}>
                        {v.name} ({v.gender})
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="en-US-GuyNeural">en-US-GuyNeural (Male - Jarvis Default)</option>
                      <option value="en-US-JennyNeural">en-US-JennyNeural (Female)</option>
                      <option value="en-US-AriaNeural">en-US-AriaNeural (Female)</option>
                      <option value="en-US-DavisNeural">en-US-DavisNeural (Male)</option>
                    </>
                  )}
                </select>
              </div>

              <button
                onClick={() => speakText("Voice synthesis test. All Jarvis audio channels are operating optimally.")}
                disabled={isJarvisSpeaking}
                className="mt-4 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs font-medium border border-zinc-700/40 flex items-center gap-1.5 transition-colors disabled:opacity-50"
                title="Preview selected voice"
              >
                <Play size={12} />
                <span>Preview</span>
              </button>
            </div>

            {/* Manual TTS Input */}
            <textarea
              value={ttsText}
              onChange={e => setTtsText(e.target.value)}
              placeholder="Type any message to synthesize through Jarvis's voice engine..."
              rows={2}
              className="w-full bg-zinc-950/60 border border-zinc-800 rounded-xl p-3 text-xs text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-violet-500 transition-colors mb-3"
            />

            <div className="flex items-center justify-between">
              <span className="text-[10px] text-zinc-500">{ttsText.length} characters</span>
              <button
                onClick={handleManualSpeak}
                disabled={ttsLoading || !ttsText.trim()}
                className="px-4 py-1.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-medium text-xs transition-colors shadow-lg shadow-violet-600/20 disabled:opacity-40 flex items-center gap-1.5"
              >
                {ttsLoading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                <span>Speak Now</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Live Conversation Session & Transcript History */}
        <div className="w-full xl:w-[55%] flex flex-col">
          <div className="flex-1 bg-[rgba(6,12,24,0.7)] backdrop-blur-md border border-[rgba(255,255,255,0.08)] rounded-2xl flex flex-col overflow-hidden shadow-2xl min-h-[480px]">

            {/* Transcript Header */}
            <div className="p-4 border-b border-[rgba(255,255,255,0.06)] flex items-center justify-between bg-[rgba(0,0,0,0.3)]">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-violet-400" />
                <h3 className="text-xs uppercase tracking-wider font-semibold text-white">Voice Session</h3>
                <span className="text-[10px] bg-zinc-800/80 text-zinc-400 px-2 py-0.5 rounded-full font-mono">
                  {transcripts.length} entries
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => {
                    const text = transcripts
                      .map(t => `[${t.time}] ${t.speaker}: ${t.text}`)
                      .join('\n\n');
                    if (text) {
                      navigator.clipboard.writeText(text).then(() =>
                        toast({ title: 'Exported', description: 'Transcript copied to clipboard.' })
                      );
                    } else {
                      toast({ title: 'Empty', description: 'No transcript entries yet.' });
                    }
                  }}
                  className="p-1.5 text-zinc-400 hover:text-white rounded-md hover:bg-zinc-800/60 transition-colors"
                  title="Copy session transcript"
                >
                  <Download size={15} />
                </button>
                <button
                  onClick={clearTranscript}
                  className="p-1.5 text-zinc-400 hover:text-red-400 rounded-md hover:bg-zinc-800/60 transition-colors"
                  title="Clear transcript"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>

            {/* Conversation Messages View */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {transcripts.length === 0 && !isRecording && !isJarvisThinking && (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500 py-16">
                  <div className="w-14 h-14 rounded-full bg-zinc-900/60 border border-zinc-800 flex items-center justify-center mb-3">
                    <Sparkles size={24} className="text-zinc-600" />
                  </div>
                  <span className="text-sm font-medium text-zinc-400">Voice Assistant Ready</span>
                  <span className="text-xs text-zinc-600 mt-1">
                    Click the microphone to start real-time transcription and conversation.
                  </span>
                </div>
              )}

              {transcripts.map(msg => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.speaker === 'USER' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`text-[11px] font-semibold mb-1 flex items-center gap-2 ${
                      msg.speaker === 'USER'
                        ? 'text-cyan-400 flex-row-reverse'
                        : 'text-violet-400'
                    }`}
                  >
                    <span>{msg.speaker}</span>
                    <span className="text-zinc-600 font-normal text-[10px]">{msg.time}</span>
                  </div>

                  <div
                    className={`max-w-[85%] p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      msg.speaker === 'USER'
                        ? 'bg-cyan-950/30 text-cyan-50 border border-cyan-500/20 rounded-tr-sm'
                        : 'bg-zinc-900/80 text-zinc-200 border border-zinc-700/40 rounded-tl-sm'
                    }`}
                  >
                    {msg.text}

                    {/* Voice Replay button for Jarvis messages */}
                    {msg.speaker === 'JARVIS' && (
                      <div className="mt-2 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[11px]">
                        <button
                          onClick={() => speakText(msg.text)}
                          className="flex items-center gap-1.5 text-zinc-400 hover:text-cyan-300 transition-colors"
                        >
                          <RotateCcw size={12} />
                          <span>Replay Audio</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Live interim user speech preview card */}
              {isRecording && (
                <div className="flex flex-col items-end">
                  <div className="text-[11px] font-semibold mb-1 flex items-center gap-2 text-red-400 flex-row-reverse">
                    <span>USER</span>
                    <span className="text-zinc-600 font-normal text-[10px]">Transcribing Live...</span>
                  </div>
                  <div className="max-w-[85%] p-3.5 rounded-2xl bg-red-950/20 border border-dashed border-red-500/30 rounded-tr-sm text-xs sm:text-sm text-zinc-300">
                    {fullTranscript ? (
                      <div>
                        <span>{transcript} </span>
                        <span className="text-cyan-300 font-medium animate-pulse">{interimTranscript}</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-zinc-500">
                        <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-ping" />
                        <span>Listening...</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Jarvis Thinking indicator */}
              {isJarvisThinking && (
                <div className="flex flex-col items-start">
                  <div className="text-[11px] font-semibold mb-1 text-violet-400 flex items-center gap-2">
                    <span>JARVIS</span>
                    <span className="text-zinc-600 font-normal text-[10px]">Processing...</span>
                  </div>
                  <div className="p-3.5 rounded-2xl bg-violet-950/20 border border-violet-500/20 rounded-tl-sm flex items-center gap-2 text-xs text-violet-300">
                    <Loader2 size={14} className="animate-spin text-violet-400" />
                    <span>Analyzing voice command and preparing response...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Session Stats Footer */}
            <div className="p-3.5 border-t border-[rgba(255,255,255,0.06)] bg-[rgba(0,0,0,0.3)] flex items-center justify-between text-[10px] font-mono text-zinc-500">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span>{backendConnected ? 'STT/TTS API CONNECTED' : 'OFFLINE MODE'}</span>
              </div>
              <div className="flex items-center gap-4">
                <span>WORDS: {wordCount}</span>
                <span>VOICE: {selectedVoice.split('-')[2] || 'Guy'}</span>
              </div>
            </div>

          </div>
        </div>

      </div>
    </PageShell>
  );
}
