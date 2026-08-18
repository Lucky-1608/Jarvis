import { create } from 'zustand';
import { getBaseUrl } from '../lib/api';

export type AIState = 'idle' | 'listening' | 'thinking' | 'executing' | 'speaking' | 'error' | 'success';

interface TaskStep {
  id: string;
  label: string;
  status: 'pending' | 'in-progress' | 'completed' | 'error';
}

interface CurrentTask {
  title: string;
  progress: number;
  steps: TaskStep[];
}

interface Agent {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'idle' | 'thinking';
  description: string;
}

interface ToolCall {
  id: string;
  tool: string;
  timestamp: string;
  status: 'success' | 'running' | 'error';
}

interface MemoryFragment {
  id: string;
  content: string;
  relevance: number;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'jarvis';
  text: string;
  timestamp: string;
}

interface SystemStats {
  brainCore: number;
  router: number;
  visionEngine: number;
  voiceEngine: number;
}

export interface LogEntry {
  id: string;
  message: string;
  timestamp: string;
  type?: 'info' | 'warning' | 'error';
}

interface JarvisStore {
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;

  aiState: AIState;
  setAIState: (state: AIState) => void;
  
  currentTask: CurrentTask | null;
  setCurrentTask: (task: CurrentTask | null) => void;
  
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  
  recentTools: ToolCall[];
  addToolCall: (call: ToolCall) => void;
  
  memories: MemoryFragment[];
  
  messages: ChatMessage[];
  addMessage: (text: string, isUser: boolean) => void;

  systemStats: SystemStats;
  updateVisionStatus: (val: number) => void;
  
  audioAmplitude: number;
  setAudioAmplitude: (amp: number) => void;

  logs: LogEntry[];
  addLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void;
  
  alertActive: boolean;
  alertMessage: string | null;
  
  whatsappStatus: 'disconnected' | 'waiting_qr' | 'connected';
  whatsappQr: string | null;
  telegramStatus: 'disconnected' | 'connected';

  backendConnected: boolean;
  setBackendConnected: (connected: boolean) => void;

  connectWebSocket: () => void;
}

// Initial mock data removed

let wsInstance: WebSocket | null = null;

export const useJarvisStore = create<JarvisStore>((set, get) => ({
  activeProjectId: null,
  setActiveProjectId: (id) => set({ activeProjectId: id }),

  aiState: 'idle',
  setAIState: (state) => set({ aiState: state }),
  
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),
  
  agents: [],
  setAgents: (agents) => set({ agents }),
  
  recentTools: [],
  addToolCall: (call) => set((state) => ({ recentTools: [call, ...state.recentTools].slice(0, 10) })),
  
  memories: [],
  
  messages: [],
  addMessage: (text, isUser) => set((state) => {
    const newMessage: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      role: isUser ? 'user' : 'jarvis',
      text,
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false })
    };
    return { messages: [...state.messages, newMessage] };
  }),
  
  systemStats: {
    brainCore: 100,
    router: 100,
    visionEngine: 100,
    voiceEngine: 100
  },
  updateVisionStatus: (val) => set((state) => ({ systemStats: { ...state.systemStats, visionEngine: val } })),
  
  audioAmplitude: 0,
  setAudioAmplitude: (amp) => set({ audioAmplitude: amp }),

  logs: [],
  addLog: (log) => set((state) => {
    const newLog: LogEntry = {
      ...log,
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false })
    };
    return { logs: [...state.logs, newLog].slice(-50) };
  }),

  alertActive: false,
  alertMessage: null,

  whatsappStatus: 'disconnected',
  whatsappQr: null,
  telegramStatus: 'disconnected',

  backendConnected: false as boolean,
  setBackendConnected: (connected: boolean) => set({ backendConnected: connected }),

  connectWebSocket: async () => {
    if (wsInstance) return;

    get().addLog({ message: 'Establishing WebSocket connection to Core...' });
    
    const base = await getBaseUrl();
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = base ? base.replace(/^http/, 'ws') : `${wsProtocol}//${window.location.host}`;
    
    // Use the actual API key from local storage
    const token = localStorage.getItem('JARVIS_API_KEY') || 'JARVIS_DEV_KEY';
    wsInstance = new WebSocket(`${host}/api/hud/ws?token=${token}`);
    
    wsInstance.onopen = () => {
      set({ backendConnected: true });
      get().addLog({ message: 'WebSocket connected. Listening for telemetry...' });
    };

    wsInstance.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'system.ready') {
          get().addLog({ message: `Core system ready. Tools loaded: ${msg.data?.tools_registered || 0}` });
        } else if (msg.type === 'vision.started') {
          set((state) => ({ systemStats: { ...state.systemStats, visionEngine: 80 } }));
        } else if (msg.type === 'vision.completed') {
          set((state) => ({ systemStats: { ...state.systemStats, visionEngine: 100 } }));
        } else if (msg.type === 'whatsapp.qr') {
          set({ whatsappStatus: 'waiting_qr', whatsappQr: msg.data.payload });
        } else if (msg.type === 'whatsapp.status') {
          set({ whatsappStatus: msg.data.payload });
        } else if (msg.type === 'telegram.status') {
          set({ telegramStatus: msg.data.payload });
        } else if (msg.type === 'hud.notification') {
          const { title, message, level } = msg.data;
          get().addLog({ 
            message: `[${level.toUpperCase()}] ${title}: ${message}`,
            type: level === 'error' || level === 'warning' ? 'error' : 'info'
          });
          
          if (level === 'warning' || level === 'error') {
            set({ alertActive: true, alertMessage: title });
            setTimeout(() => {
              set({ alertActive: false, alertMessage: null });
            }, 5000);
          }
        }
      } catch (err) {
        console.error("Error parsing WS message:", err);
      }
    };

    wsInstance.onclose = () => {
      set({ backendConnected: false });
      get().addLog({ message: 'WebSocket disconnected.', type: 'warning' });
      wsInstance = null;
    };
  }
}));