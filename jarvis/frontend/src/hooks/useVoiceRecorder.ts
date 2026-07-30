import { useState, useRef, useCallback } from 'react';

export function useVoiceRecorder(onTranscription: (text: string) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const chunks = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
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

      // Request data every 1 second to update the cumulative chunks
      mediaRecorder.current.start(1500);
      setIsRecording(true);
      setError(null);
      
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setError("Microphone access denied or not available.");
    }
  }, [onTranscription]);

  const stopRecording = useCallback(() => {
    return new Promise<void>((resolve) => {
      if (mediaRecorder.current && isRecording) {
        mediaRecorder.current.onstop = () => {
          mediaRecorder.current?.stream.getTracks().forEach(track => track.stop());
          
          // Wait a short bit to allow the final websocket message (the transcription of the last chunk) to arrive
          setTimeout(() => {
            if (ws.current) {
              ws.current.close();
              ws.current = null;
            }
            chunks.current = [];
            setIsRecording(false);
            resolve();
          }, 500); // 500ms should be enough for the final local STT result
        };
        mediaRecorder.current.stop();
      } else {
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
