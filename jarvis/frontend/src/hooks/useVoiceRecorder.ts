import { useState, useRef, useCallback } from 'react';
import { useJarvisStore } from '../store/jarvisStore';
import { getBaseUrl, getApiKey } from '../lib/api';

export interface UseVoiceRecorderOptions {
  onTranscription?: (text: string, isFinal?: boolean) => void;
  onInterim?: (text: string) => void;
  continuous?: boolean;
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

  const startRecording = useCallback(async () => {
    recognizedTextRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    setError(null);

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
        };

        recognition.onerror = (e: any) => {
          // If error is 'no-speech', do not crash
          if (e.error !== 'no-speech') {
            console.warn("SpeechRecognition error:", e.error || e);
          }
        };

        recognition.onend = () => {
          // If still recording in continuous mode, restart
          if (isRecording && recognitionRef.current) {
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
          if (!analyser) return;
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const average = sum / dataArray.length;
          const normalized = Math.min(1, average / 128);
          setAudioLevel(normalized);
          useJarvisStore.getState().setAudioAmplitude(normalized);
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
      setError(null);

    } catch (err: any) {
      console.error("Error accessing microphone:", err);
      setError(err?.message || "Microphone access denied or not available.");
      setIsRecording(false);
    }
  }, []);

  const stopRecording = useCallback((): Promise<string> => {
    return new Promise<string>((resolve) => {
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
  }, []);

  const cancelRecording = useCallback(() => {
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
  }, []);

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
