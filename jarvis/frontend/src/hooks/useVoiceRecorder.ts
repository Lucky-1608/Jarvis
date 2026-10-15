import { useState, useRef, useCallback, useEffect } from 'react';
import { useJarvisStore } from '../store/jarvisStore';
import { getBaseUrl, getApiKey } from '../lib/api';

export interface UseVoiceRecorderOptions {
  onTranscription?: (text: string, isFinal?: boolean) => void;
  onInterim?: (text: string) => void;
  onSilence?: (finalText: string) => void;
  continuous?: boolean;
  autoStopOnSilence?: boolean; // When true, considers any pause/stop after speech as the end of input (default: true)
  silenceDurationMs?: number; // Duration of silence/pause in ms to consider input ended (default: 1400ms)
  silenceThreshold?: number; // Audio level threshold (0 to 1) below which is considered silence (default: 0.035)
  initialSilenceTimeoutMs?: number; // Timeout in ms if no speech is detected at all (default: 10000ms)
}

export function useVoiceRecorder(
  callbackOrOptions?: ((text: string) => void) | UseVoiceRecorderOptions
) {
  const options: UseVoiceRecorderOptions = typeof callbackOrOptions === 'function'
    ? { onTranscription: callbackOrOptions }
    : (callbackOrOptions || {});

  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const isRecordingRef = useRef(false);
  const isStoppingRef = useRef(false);
  const stoppingPromiseRef = useRef<Promise<string> | null>(null);
  const hasSpokenRef = useRef(false);
  const lastSpeechTimeRef = useRef<number>(0);
  const silenceTimerRef = useRef<any>(null);
  const initialSilenceTimerRef = useRef<any>(null);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const recognitionRef = useRef<any>(null);
  const ws = useRef<WebSocket | null>(null);
  const chunks = useRef<Blob[]>([]);
  const recognizedTextRef = useRef('');
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Audio analysis refs
  const audioContext = useRef<AudioContext | null>(null);
  const animationFrameId = useRef<number | null>(null);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const clearSilenceTimers = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (initialSilenceTimerRef.current) {
      clearTimeout(initialSilenceTimerRef.current);
      initialSilenceTimerRef.current = null;
    }
  }, []);

  const cancelRecording = useCallback(() => {
    clearSilenceTimers();
    isStoppingRef.current = false;
    isRecordingRef.current = false;
    stoppingPromiseRef.current = null;

    if (animationFrameId.current) {
      cancelAnimationFrame(animationFrameId.current);
      animationFrameId.current = null;
    }
    if (audioContext.current) {
      audioContext.current.close().catch(console.error);
      audioContext.current = null;
    }
    setAudioLevel(0);
    useJarvisStore.getState().setAudioAmplitude(0);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }

    if (ws.current) {
      try {
        ws.current.close();
      } catch {}
      ws.current = null;
    }

    chunks.current = [];
    recognizedTextRef.current = '';
    setIsRecording(false);
    setInterimTranscript('');
  }, [clearSilenceTimers]);

  const stopRecording = useCallback((): Promise<string> => {
    clearSilenceTimers();

    if (stoppingPromiseRef.current) {
      return stoppingPromiseRef.current;
    }

    isStoppingRef.current = true;
    isRecordingRef.current = false;

    const stopPromise = new Promise<string>((resolve) => {
      // Clean up audio context and animation frame
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
        animationFrameId.current = null;
      }
      if (audioContext.current) {
        audioContext.current.close().catch(console.error);
        audioContext.current = null;
      }
      setAudioLevel(0);
      useJarvisStore.getState().setAudioAmplitude(0);

      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
        recognitionRef.current = null;
      }

      const finish = async () => {
        if (ws.current) {
          try {
            ws.current.close();
          } catch {}
          ws.current = null;
        }

        let finalText = recognizedTextRef.current.trim();

        // If local speech recognition produced nothing, run backend transcribe on audio
        if (!finalText && chunks.current.length > 0) {
          try {
            const audioBlob = new Blob(chunks.current, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');
            const base = await getBaseUrl();
            const res = await fetch(`${base}/api/voice/transcribe`, {
              method: 'POST',
              headers: { 'X-API-Key': getApiKey() },
              body: formData,
            });
            const data = await res.json();
            if (data?.text) {
              finalText = data.text.trim();
              recognizedTextRef.current = finalText;
            }
          } catch (err) {
            console.warn("Fallback STT error:", err);
          }
        }

        // Clean up tracks
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        chunks.current = [];
        setIsRecording(false);
        isRecordingRef.current = false;
        isStoppingRef.current = false;
        stoppingPromiseRef.current = null;
        setInterimTranscript('');
        setTranscript(finalText);

        if (optionsRef.current.onTranscription && finalText) {
          optionsRef.current.onTranscription(finalText, true);
        }

        resolve(finalText);
      };

      if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
        mediaRecorder.current.onstop = () => {
          finish();
        };
        try {
          mediaRecorder.current.stop();
        } catch {
          finish();
        }
      } else {
        finish();
      }
    });

    stoppingPromiseRef.current = stopPromise;
    return stopPromise;
  }, [clearSilenceTimers]);

  const triggerSilenceEnd = useCallback(async () => {
    clearSilenceTimers();
    if (!isRecordingRef.current || isStoppingRef.current) return;

    const currentText = recognizedTextRef.current.trim();
    if (!hasSpokenRef.current && !currentText) {
      cancelRecording();
      return;
    }

    try {
      const finalText = await stopRecording();
      if (optionsRef.current.onSilence) {
        optionsRef.current.onSilence(finalText);
      }
    } catch (err) {
      console.warn('[useVoiceRecorder] Error ending voice input on silence:', err);
    }
  }, [clearSilenceTimers, cancelRecording, stopRecording]);

  const notifySpeechActivity = useCallback((hasText: boolean = false) => {
    if (!isRecordingRef.current || isStoppingRef.current) return;

    lastSpeechTimeRef.current = Date.now();

    if (hasText || recognizedTextRef.current.trim().length > 0) {
      hasSpokenRef.current = true;
      if (initialSilenceTimerRef.current) {
        clearTimeout(initialSilenceTimerRef.current);
        initialSilenceTimerRef.current = null;
      }
    }

    // Reset silence timer on active speech
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    const autoStop = optionsRef.current.autoStopOnSilence !== false;
    if (hasSpokenRef.current && autoStop) {
      const silenceDuration = optionsRef.current.silenceDurationMs ?? 1400;
      silenceTimerRef.current = setTimeout(() => {
        triggerSilenceEnd();
      }, silenceDuration);
    }
  }, [triggerSilenceEnd]);

  const startRecording = useCallback(async () => {
    clearSilenceTimers();
    isStoppingRef.current = false;
    stoppingPromiseRef.current = null;
    hasSpokenRef.current = false;
    lastSpeechTimeRef.current = Date.now();
    isRecordingRef.current = true;

    recognizedTextRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    setError(null);

    // Initial timeout if user opens mic and never speaks
    const initialTimeout = optionsRef.current.initialSilenceTimeoutMs ?? 10000;
    initialSilenceTimerRef.current = setTimeout(() => {
      if (isRecordingRef.current && !hasSpokenRef.current && !recognizedTextRef.current.trim()) {
        console.debug("[useVoiceRecorder] Initial timeout without speech.");
        cancelRecording();
      }
    }, initialTimeout);

    // 1. Native Web Speech API for 0-ms latency local real-time transcription
    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    let webSpeechActive = false;

    if (SpeechRecognitionClass) {
      try {
        const recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event: any) => {
          let interim = '';
          let final = '';

          for (let i = 0; i < event.results.length; ++i) {
            const res = event.results[i];
            if (res.isFinal) {
              final += res[0].transcript;
            } else {
              interim += res[0].transcript;
            }
          }

          const combined = (final + (interim ? ' ' + interim : '')).trim();
          recognizedTextRef.current = combined;
          setInterimTranscript(interim.trim());
          if (final.trim()) {
            setTranscript(final.trim());
          }

          if (optionsRef.current.onInterim) {
            optionsRef.current.onInterim(interim.trim());
          }

          if (optionsRef.current.onTranscription && combined) {
            optionsRef.current.onTranscription(combined, !interim);
          }

          if (combined) {
            notifySpeechActivity(true);
          }
        };

        recognition.onerror = (e: any) => {
          // If error is 'no-speech', do not crash
          if (e.error !== 'no-speech') {
            console.warn("SpeechRecognition error:", e.error || e);
          }
        };

        recognition.onend = () => {
          // If still recording in continuous mode, restart
          if (isRecordingRef.current && !isStoppingRef.current && recognitionRef.current) {
            try {
              recognition.start();
            } catch {}
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
        webSpeechActive = true;
      } catch (err) {
        console.warn("SpeechRecognition init failed, falling back to server STT:", err);
      }
    }

    // 2. MediaRecorder for live audio visualizer & backend STT fallback
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      mediaStreamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4');

      mediaRecorder.current = new MediaRecorder(stream, { mimeType });
      chunks.current = [];

      // Audio analysis for real-time waveform visualizer
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        audioContext.current = new AudioContextClass();
        const analyser = audioContext.current.createAnalyser();
        const source = audioContext.current.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        const updateAmplitude = () => {
          if (!analyser || !isRecordingRef.current) return;
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const average = sum / dataArray.length;
          const normalized = Math.min(1, average / 128);
          setAudioLevel(normalized);
          useJarvisStore.getState().setAudioAmplitude(normalized);

          const threshold = optionsRef.current.silenceThreshold ?? 0.035;

          // Sound detected
          if (normalized > threshold) {
            if (normalized > 0.06 || recognizedTextRef.current.trim().length > 0) {
              notifySpeechActivity(false);
            }
          }

          animationFrameId.current = requestAnimationFrame(updateAmplitude);
        };

        updateAmplitude();
      } catch (err) {
        console.warn("Could not set up audio context for visualization:", err);
      }

      // 3. Connect to backend streaming STT WebSocket
      try {
        const base = await getBaseUrl();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = base ? base.replace(/^http/, 'ws') : `${protocol}//${window.location.host}`;
        const token = getApiKey() || localStorage.getItem('JARVIS_API_KEY') || 'JARVIS_DEV_KEY';

        const socket = new WebSocket(`${host}/api/voice/stream?token=${token}`);
        ws.current = socket;

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.text) {
              const text = data.text.trim();
              // Only override if WebSpeech didn't already produce text
              if (!webSpeechActive || !recognizedTextRef.current) {
                recognizedTextRef.current = text;
                setInterimTranscript(text);
                if (optionsRef.current.onTranscription) {
                  optionsRef.current.onTranscription(text, false);
                }
                if (text) {
                  notifySpeechActivity(true);
                }
              }
            }
          } catch (e) {
            console.error("Failed to parse STT websocket message", e);
          }
        };

        socket.onerror = () => {
          console.debug("STT WebSocket stream unavailable, using native speech engine.");
        };
      } catch {}

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.current.push(e.data);
          if (ws.current?.readyState === WebSocket.OPEN) {
            const blob = new Blob(chunks.current, { type: mimeType });
            ws.current.send(blob);
          }
        }
      };

      mediaRecorder.current.start(800); // 800ms chunks for live streaming
      setIsRecording(true);
      isRecordingRef.current = true;
      setError(null);

    } catch (err: any) {
      console.error("Error accessing microphone:", err);
      setError(err?.message || "Microphone access denied or not available.");
      setIsRecording(false);
      isRecordingRef.current = false;
      clearSilenceTimers();
    }
  }, [clearSilenceTimers, cancelRecording, notifySpeechActivity]);

  useEffect(() => {
    return () => {
      clearSilenceTimers();
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
      if (audioContext.current) {
        audioContext.current.close().catch(() => {});
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }
      if (ws.current) {
        try { ws.current.close(); } catch {}
      }
    };
  }, [clearSilenceTimers]);

  return {
    isRecording,
    transcript,
    interimTranscript,
    fullTranscript: (transcript + ' ' + interimTranscript).trim(),
    audioLevel,
    startRecording,
    stopRecording,
    cancelRecording,
    error,
  };
}
