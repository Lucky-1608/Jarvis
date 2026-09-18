import { useState, useRef, useCallback } from 'react';
import { useJarvisStore } from '../store/jarvisStore';

export function useVoiceRecorder(onTranscription: (text: string) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const chunks = useRef<Blob[]>([]);
  
  // Audio analysis refs
  const audioContext = useRef<AudioContext | null>(null);
  const animationFrameId = useRef<number | null>(null);

  const startRecording = useCallback(async () => {
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
          // Normalize (roughly) 0-255 to 0-1
          useJarvisStore.getState().setAudioAmplitude(Math.min(1, average / 128));
          animationFrameId.current = requestAnimationFrame(updateAmplitude);
        };
        
        updateAmplitude();
      } catch (err) {
        console.warn("Could not set up audio context for visualization:", err);
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = import.meta.env.VITE_API_BASE_URL 
        ? import.meta.env.VITE_API_BASE_URL.replace(/^http/, 'ws')
        : `${protocol}//${window.location.host}`;
        
      ws.current = new WebSocket(`${host}/api/voice/stream`);

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.text) {
            onTranscription(data.text);
          }
          if (data.error) {
            setError(data.error);
          }
        } catch (e) {
          console.error("Failed to parse STT websocket message", e);
        }
      };

      ws.current.onerror = () => {
        setError("WebSocket connection failed.");
      };

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.current.push(e.data);
          // Send cumulative audio to the server
          if (ws.current?.readyState === WebSocket.OPEN) {
            const blob = new Blob(chunks.current, { type: 'audio/webm' });
            ws.current.send(blob);
          }
        }
      };

      // Only fire ondataavailable when the recording is explicitly stopped
      // This prevents spamming the backend/ElevenLabs with full cumulative audio every 250ms
      mediaRecorder.current.start();
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

      if (mediaRecorder.current && isRecording) {
        if (mediaRecorder.current.state === 'inactive') {
          setIsRecording(false);
          resolve();
          return;
        }
        
        let resolved = false;
        const completeStop = () => {
          if (resolved) return;
          resolved = true;
          
          if (ws.current) {
            ws.current.close();
            ws.current = null;
          }
          chunks.current = [];
          setIsRecording(false);
          resolve();
        };
        
        mediaRecorder.current.onstop = () => {
          mediaRecorder.current?.stream.getTracks().forEach(track => track.stop());
          // Wait a short bit to allow the final websocket message to arrive
          setTimeout(completeStop, 250); 
        };
        
        try {
          mediaRecorder.current.stop();
          // Safety fallback: if onstop doesn't fire, force complete stop after 1s
          setTimeout(completeStop, 1000);
        } catch (e) {
          completeStop();
        }
      } else {
        setIsRecording(false);
        resolve();
      }
    });
  }, [isRecording]);

  return {
    isRecording,
    startRecording,
    stopRecording,
    error
  };
}
