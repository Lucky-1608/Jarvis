import { useState, useRef, useCallback } from 'react';
import { useJarvisStore } from '../store/jarvisStore';
import { getBaseUrl, getApiKey } from '../lib/api';

export function useVoiceRecorder(onTranscription: (text: string) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const recognitionRef = useRef<any>(null);
  const ws = useRef<WebSocket | null>(null);
  const chunks = useRef<Blob[]>([]);
  const recognizedTextRef = useRef('');
  
  // Audio analysis refs
  const audioContext = useRef<AudioContext | null>(null);
  const animationFrameId = useRef<number | null>(null);

  const startRecording = useCallback(async () => {
    recognizedTextRef.current = '';
    setError(null);

    // 1. Native Web Speech API for instant local real-time transcription
    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognitionClass) {
      try {
        const recognition = new SpeechRecognitionClass();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event: any) => {
          let interimTranscript = '';
          let finalTranscript = '';

          for (let i = 0; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }

          const currentText = (finalTranscript + ' ' + interimTranscript).trim();
          if (currentText) {
            recognizedTextRef.current = currentText;
            onTranscription(currentText);
          }
        };

        recognition.onerror = (e: any) => {
          console.warn("SpeechRecognition error:", e);
        };

        recognition.start();
        recognitionRef.current = recognition;
      } catch (err) {
        console.warn("SpeechRecognition init failed, falling back to audio recording:", err);
      }
    }

    // 2. MediaRecorder for live audio visualization and backend STT fallback
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
      // Set up audio analysis for the UI bubble
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        audioContext.current = new AudioContextClass();
        const analyser = audioContext.current.createAnalyser();
        const source = audioContext.current.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        const updateAmplitude = () => {
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const average = sum / dataArray.length;
          useJarvisStore.getState().setAudioAmplitude(Math.min(1, average / 128));
          animationFrameId.current = requestAnimationFrame(updateAmplitude);
        };
        
        updateAmplitude();
      } catch (err) {
        console.warn("Could not set up audio context for visualization:", err);
      }

      // Connect to backend streaming STT if available
      try {
        const base = await getBaseUrl();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = base ? base.replace(/^http/, 'ws') : `${protocol}//${window.location.host}`;
        const token = getApiKey() || localStorage.getItem('JARVIS_API_KEY') || 'JARVIS_DEV_KEY';

        ws.current = new WebSocket(`${host}/api/voice/stream?token=${token}`);

        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.text && !recognizedTextRef.current) {
              onTranscription(data.text);
            }
          } catch (e) {
            console.error("Failed to parse STT websocket message", e);
          }
        };

        ws.current.onerror = () => {
          // If WS fails, native SpeechRecognition or fallback transcribe handles it
          console.warn("STT WebSocket stream unavailable, using native speech engine.");
        };
      } catch {}

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.current.push(e.data);
          if (ws.current?.readyState === WebSocket.OPEN) {
            const blob = new Blob(chunks.current, { type: 'audio/webm' });
            ws.current.send(blob);
          }
        }
      };

      mediaRecorder.current.start(1000);
      setIsRecording(true);
      setError(null);
      
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setError("Microphone access denied or not available.");
    }
  }, [onTranscription]);

  const stopRecording = useCallback(() => {
    return new Promise<void>((resolve) => {
      // Clean up audio context and animation frame
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
        animationFrameId.current = null;
      }
      if (audioContext.current) {
        audioContext.current.close().catch(console.error);
        audioContext.current = null;
      }
      useJarvisStore.getState().setAudioAmplitude(0);

      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
        recognitionRef.current = null;
      }

      if (mediaRecorder.current && isRecording) {
        if (mediaRecorder.current.state === 'inactive') {
          setIsRecording(false);
          resolve();
          return;
        }
        
        let resolved = false;
        const completeStop = async () => {
          if (resolved) return;
          resolved = true;
          
          if (ws.current) {
            ws.current.close();
            ws.current = null;
          }

          if (recognizedTextRef.current) {
            onTranscription(recognizedTextRef.current);
          } else if (chunks.current.length > 0) {
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
                onTranscription(data.text);
              }
            } catch (err) {
              console.warn("Fallback STT error:", err);
            }
          }

          chunks.current = [];
          setIsRecording(false);
          resolve();
        };
        
        mediaRecorder.current.onstop = () => {
          mediaRecorder.current?.stream.getTracks().forEach(track => track.stop());
          completeStop();
        };
        
        try {
          mediaRecorder.current.stop();
          setTimeout(completeStop, 1500);
        } catch (e) {
          completeStop();
        }
      } else {
        if (recognizedTextRef.current) {
          onTranscription(recognizedTextRef.current);
        }
        setIsRecording(false);
        resolve();
      }
    });
  }, [isRecording, onTranscription]);

  return {
    isRecording,
    startRecording,
    stopRecording,
    error
  };
}
