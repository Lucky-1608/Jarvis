import { useState, useRef, useCallback, useEffect } from 'react';
import { useJarvisStore } from '../store/jarvisStore';
import { getBaseUrl, getApiKey } from '../lib/api';

export interface UseVoiceRecorderOptions {
  onTranscription?: (text: string, isFinal?: boolean) => void;
  onInterim?: (text: string) => void;
  onSilence?: (finalText: string) => void;
  continuous?: boolean;
  autoStopOnSilence?: boolean; // When true, considers any pause/stop after speech as the end of input (default: true)
  silenceDurationMs?: number; // Duration of silence/pause in ms to consider input ended (default: 2200ms)
  silenceThreshold?: number; // Audio level threshold (0 to 1) below which is considered silence (default: 0.025)
  initialSilenceTimeoutMs?: number; // Timeout in ms if no speech is detected at all (default: 10000ms)
}

const HALLUCINATION_PHRASES = new Set([
  'thank you',
  'thank you very much',
  'thanks',
  'thanks for watching',
  'thank you for watching',
  'thanks for listening',
  'thank you for listening',
  'please subscribe',
  'like and subscribe',
  'subtitles by the amara org community',
  'subtitles by',
  'transcribed by',
  'you',
  'bye',
  'bye bye',
  'mbc',
]);

function cleanTranscriptionText(raw: string): string {
  if (!raw) return '';
  const trimmed = raw.trim();
  const normalized = trimmed.toLowerCase().replace(/[^\w\s]/g, '').trim();
  if (!normalized || HALLUCINATION_PHRASES.has(normalized)) {
    return '';
  }
  // Catch repeated Whisper silence hallucinations like "Thank you. Thank you."
  if (/^(?:(?:thank you(?:\s+(?:very|so)\s+much)?|thanks(?:\s+for\s+(?:watching|listening))?|you|bye)[.,!?\s]*)+$/i.test(trimmed)) {
    return '';
  }
  // Strip leading "Thank you." if Whisper hallucinated it on initial silence before actual speech
  return trimmed
    .replace(/^(?:(?:thank you(?:\s+(?:very|so)\s+much)?|thanks(?:\s+for\s+(?:watching|listening))?)[.,!?\s]+)+(?=\w)/i, '')
    .trim();
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
  const hasAudioSpeechRef = useRef(false);
  const webSpeechWorkingRef = useRef(false);
  const wsBusyRef = useRef(false);
  const mimeTypeRef = useRef<string>('audio/webm');
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
    hasSpokenRef.current = false;
    hasAudioSpeechRef.current = false;
    webSpeechWorkingRef.current = false;
    wsBusyRef.current = false;

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
      const rec = recognitionRef.current;
      recognitionRef.current = null;
      try {
        rec.stop();
      } catch {}
    }

    if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
      try {
        mediaRecorder.current.onstop = null;
        mediaRecorder.current.stop();
      } catch {}
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
        const rec = recognitionRef.current;
        recognitionRef.current = null;
        try {
          rec.stop();
        } catch {}
      }

      const finish = async () => {
        if (ws.current) {
          try {
            ws.current.close();
          } catch {}
          ws.current = null;
        }

        let finalText = cleanTranscriptionText(recognizedTextRef.current);

        // When using backend STT (e.g. Companion App / Tauri / Mobile where WebSpeech doesn't produce full text),
        // always transcribe the complete recorded audio blob so no words at the end or middle are lost.
        const shouldTranscribeFullAudio =
          chunks.current.length > 0 && (!webSpeechWorkingRef.current || !finalText);

        if (shouldTranscribeFullAudio) {
          try {
            const activeMime = mimeTypeRef.current || 'audio/webm';
            const ext = activeMime.includes('mp4') ? 'mp4' : 'webm';
            const audioBlob = new Blob(chunks.current, { type: activeMime });
            if (audioBlob.size > 500) {
              const formData = new FormData();
              formData.append('file', audioBlob, `recording.${ext}`);
              const base = await getBaseUrl();
              const res = await fetch(`${base}/api/voice/transcribe`, {
                method: 'POST',
                headers: { 'X-API-Key': getApiKey() },
                body: formData,
              });
              if (res.ok) {
                const data = await res.json();
                const cleaned = cleanTranscriptionText(data?.text || '');
                if (cleaned) {
                  finalText = cleaned;
                  recognizedTextRef.current = finalText;
                }
              }
            }
          } catch (err) {
            console.warn('Full audio STT error:', err);
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
        wsBusyRef.current = false;
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

    const currentText = cleanTranscriptionText(recognizedTextRef.current);
    if (!hasSpokenRef.current && !hasAudioSpeechRef.current && !currentText) {
      cancelRecording();
      return;
    }

    try {
      const finalText = await stopRecording();
      if (finalText && optionsRef.current.onSilence) {
        optionsRef.current.onSilence(finalText);
      }
    } catch (err) {
      console.warn('[useVoiceRecorder] Error ending voice input on silence:', err);
    }
  }, [clearSilenceTimers, cancelRecording, stopRecording]);

  const notifySpeechActivity = useCallback((isConfirmedSpeech: boolean = false) => {
    if (!isRecordingRef.current || isStoppingRef.current) return;

    lastSpeechTimeRef.current = Date.now();

    if (isConfirmedSpeech || recognizedTextRef.current.trim().length > 0) {
      hasSpokenRef.current = true;
      if (initialSilenceTimerRef.current) {
        clearTimeout(initialSilenceTimerRef.current);
        initialSilenceTimerRef.current = null;
      }
    }

    // Reset silence timer on active speech so we never cut off mid-sentence
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }

    const autoStop = optionsRef.current.autoStopOnSilence !== false;
    if (hasSpokenRef.current && autoStop) {
      const silenceDuration = optionsRef.current.silenceDurationMs ?? 2200;
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
    hasAudioSpeechRef.current = false;
    webSpeechWorkingRef.current = false;
    wsBusyRef.current = false;
    lastSpeechTimeRef.current = Date.now();
    isRecordingRef.current = true;

    recognizedTextRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    setError(null);

    // Initial timeout if user opens mic and never speaks
    const initialTimeout = optionsRef.current.initialSilenceTimeoutMs ?? 10000;
    initialSilenceTimerRef.current = setTimeout(() => {
      if (
        isRecordingRef.current &&
        !hasSpokenRef.current &&
        !hasAudioSpeechRef.current &&
        !recognizedTextRef.current.trim()
      ) {
        console.debug('[useVoiceRecorder] Initial timeout without speech.');
        cancelRecording();
      }
    }, initialTimeout);

    // 1. Native Web Speech API for 0-ms latency local real-time transcription (when supported & working)
    const isTauriEnv =
      typeof window !== 'undefined' &&
      ('__TAURI_INTERNALS__' in window || '__TAURI__' in window);
    const SpeechRecognitionClass =
      !isTauriEnv &&
      ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

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

          const combined = cleanTranscriptionText(
            (final + (interim ? ' ' + interim : '')).trim()
          );
          if (!combined) return;

          webSpeechWorkingRef.current = true;
          hasAudioSpeechRef.current = true;
          recognizedTextRef.current = combined;
          setInterimTranscript(interim.trim());
          if (final.trim()) {
            setTranscript(cleanTranscriptionText(final));
          }

          if (optionsRef.current.onInterim) {
            optionsRef.current.onInterim(interim.trim());
          }

          if (optionsRef.current.onTranscription) {
            optionsRef.current.onTranscription(combined, !interim);
          }

          notifySpeechActivity(true);
        };

        recognition.onerror = (e: any) => {
          const errCode = e?.error || '';
          if (
            errCode === 'network' ||
            errCode === 'not-allowed' ||
            errCode === 'service-not-allowed' ||
            errCode === 'audio-capture'
          ) {
            // Disable broken WebSpeech so backend STT handles everything cleanly
            webSpeechWorkingRef.current = false;
            recognitionRef.current = null;
            try {
              recognition.stop();
            } catch {}
          } else if (errCode !== 'no-speech' && errCode !== 'aborted') {
            console.warn('SpeechRecognition error:', errCode || e);
          }
        };

        recognition.onend = () => {
          if (isRecordingRef.current && !isStoppingRef.current && recognitionRef.current) {
            try {
              recognition.start();
            } catch {}
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
      } catch (err) {
        console.warn('SpeechRecognition init failed, falling back to server STT:', err);
      }
    }

    // 2. MediaRecorder for live audio visualizer & backend neural STT
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';
      mimeTypeRef.current = mimeType;

      mediaRecorder.current = new MediaRecorder(stream, { mimeType });
      chunks.current = [];

      // Audio analysis for real-time waveform visualizer & accurate RMS voice detection
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        audioContext.current = new AudioContextClass();
        if (audioContext.current.state === 'suspended') {
          audioContext.current.resume().catch(() => {});
        }
        const analyser = audioContext.current.createAnalyser();
        const source = audioContext.current.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        const freqData = new Uint8Array(analyser.frequencyBinCount);
        const timeData = new Uint8Array(analyser.fftSize);
        let activeSpeechFrames = 0;

        const updateAmplitude = () => {
          if (!analyser || !isRecordingRef.current) return;

          analyser.getByteFrequencyData(freqData);
          let freqSum = 0;
          for (let i = 0; i < freqData.length; i++) {
            freqSum += freqData[i];
          }
          const freqNorm = Math.min(1, freqSum / freqData.length / 128);

          analyser.getByteTimeDomainData(timeData);
          let sumSquares = 0;
          for (let i = 0; i < timeData.length; i++) {
            const sample = (timeData[i] - 128) / 128;
            sumSquares += sample * sample;
          }
          const rms = Math.sqrt(sumSquares / timeData.length);
          const visualLevel = Math.min(1, Math.max(freqNorm, rms * 3.2));

          setAudioLevel(visualLevel);
          useJarvisStore.getState().setAudioAmplitude(visualLevel);

          const threshold = optionsRef.current.silenceThreshold ?? 0.018;

          if (rms > threshold || freqNorm > threshold * 1.4) {
            activeSpeechFrames += 1;
            if (activeSpeechFrames >= 3) {
              hasAudioSpeechRef.current = true;
            }
            // Sustained speech (~200ms) arms hasSpoken; once armed, any voice activity keeps resetting silence timer
            if (activeSpeechFrames >= 12 || (hasSpokenRef.current && activeSpeechFrames >= 2)) {
              notifySpeechActivity(true);
            }
          } else {
            activeSpeechFrames = 0;
          }

          animationFrameId.current = requestAnimationFrame(updateAmplitude);
        };

        updateAmplitude();
      } catch (err) {
        console.warn('Could not set up audio context for visualization:', err);
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
          wsBusyRef.current = false;
          try {
            const data = JSON.parse(event.data);
            if (data.text !== undefined) {
              const text = cleanTranscriptionText(data.text);
              if (!text) return;

              // Update whenever local WebSpeech isn't actively driving transcription
              if (!webSpeechWorkingRef.current) {
                recognizedTextRef.current = text;
                setTranscript(text);
                setInterimTranscript('');
                if (optionsRef.current.onTranscription) {
                  optionsRef.current.onTranscription(text, false);
                }
                notifySpeechActivity(true);
              }
            }
          } catch (e) {
            console.error('Failed to parse STT websocket message', e);
          }
        };

        socket.onerror = () => {
          wsBusyRef.current = false;
          console.debug('STT WebSocket stream unavailable, will transcribe on stop.');
        };

        socket.onclose = () => {
          wsBusyRef.current = false;
        };
      } catch {}

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.current.push(e.data);
          // Only stream to backend STT after speech energy has been detected, and don't overlap requests
          if (
            hasAudioSpeechRef.current &&
            !isStoppingRef.current &&
            !webSpeechWorkingRef.current &&
            !wsBusyRef.current &&
            ws.current?.readyState === WebSocket.OPEN
          ) {
            const blob = new Blob(chunks.current, { type: mimeType });
            if (blob.size > 1000) {
              wsBusyRef.current = true;
              ws.current.send(blob);
            }
          }
        }
      };

      mediaRecorder.current.start(900); // 900ms chunks for live streaming
      setIsRecording(true);
      isRecordingRef.current = true;
      setError(null);
    } catch (err: any) {
      console.error('Error accessing microphone:', err);
      setError(err?.message || 'Microphone access denied or not available.');
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
        try {
          recognitionRef.current.stop();
        } catch {}
      }
      if (ws.current) {
        try {
          ws.current.close();
        } catch {}
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
