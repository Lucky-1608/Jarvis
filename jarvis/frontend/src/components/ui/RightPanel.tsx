import { useState } from 'react';
import { motion } from 'framer-motion';
import { useJarvisStore } from '../../store/jarvisStore';
import { api } from '../../lib/api';
import { Cpu, Database, Network, Server, CheckCircle2, CircleDashed, Clock, ChevronRight, Search, FileText, Code2, Smartphone, WifiOff, Wifi, Send, RefreshCw, KeyRound } from 'lucide-react';

const ToolIcon = ({ name }: { name: string }) => {
  if (name.includes('Search')) return <Search size={14} className="text-blue-400" />;
  if (name.includes('File')) return <FileText size={14} className="text-yellow-400" />;
  if (name.includes('Code')) return <Code2 size={14} className="text-purple-400" />;
  return <ChevronRight size={14} className="text-zinc-400" />;
};

export function RightPanelContent({ className = '' }: { className?: string }) {
  const { currentTask, systemStats, whatsappStatus, whatsappQr, whatsappPairingCode, telegramStatus, backendConnected } = useJarvisStore();
  const [isResetting, setIsResetting] = useState(false);
  const [isPairingLoading, setIsPairingLoading] = useState(false);

  const handleResetWhatsApp = async () => {
    setIsResetting(true);
    try {
      await api.post('/api/whatsapp/reset');
    } catch (e) {
      console.error('Failed to reset WhatsApp session:', e);
    } finally {
      setTimeout(() => setIsResetting(false), 2000);
    }
  };

  const handleRequestPairingCode = async () => {
    setIsPairingLoading(true);
    try {
      const res = await api.post<{ status: string; pairing_code?: string }>('/api/whatsapp/pairing-code');
      if (res.ok && res.data?.pairing_code) {
        useJarvisStore.setState({ whatsappPairingCode: res.data.pairing_code });
      }
    } catch (e) {
      console.error('Failed to request pairing code:', e);
    } finally {
      setIsPairingLoading(false);
    }
  };

  return (
    <div className={`flex flex-col gap-8 ${className}`}>
      
      {/* Current Task */}
      {currentTask && (
        <section>
          <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-3">Current Task</h3>
          <div className="bg-[rgba(0,0,0,0.3)] rounded-lg p-3 border border-[rgba(255,255,255,0.05)] relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-zinc-800">
              <motion.div 
                className="h-full bg-[var(--accent-cyan)] shadow-[0_0_10px_rgba(0,212,255,0.5)]"
                initial={{ width: 0 }}
                animate={{ width: `${currentTask.progress}%` }}
                transition={{ type: "spring", stiffness: 50 }}
              />
            </div>
            <h4 className="text-sm font-medium text-[var(--text-primary)] mt-1 mb-3">{currentTask.title}</h4>
            <div className="flex flex-col gap-2">
              {currentTask.steps.map(step => (
                <div key={step.id} className="flex items-center gap-2 text-xs">
                  {step.status === 'completed' ? (
                    <CheckCircle2 size={14} className="text-green-500" />
                  ) : step.status === 'in-progress' ? (
                    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}>
                      <CircleDashed size={14} className="text-[var(--accent-cyan)]" />
                    </motion.div>
                  ) : (
                    <CircleDashed size={14} className="text-zinc-600" />
                  )}
                  <span className={step.status === 'pending' ? 'text-zinc-500' : 'text-zinc-300'}>{step.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}



      {/* System Logs */}
      <section>
        <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-3">System Logs</h3>
        <div className="flex flex-col gap-2 font-mono">
          {useJarvisStore().logs.slice().reverse().slice(0, 10).map(log => (
            <div key={log.id} className={`flex flex-col gap-1 text-xs py-1 ${log.type === 'error' ? 'text-red-400' : log.type === 'warning' ? 'text-yellow-400' : 'text-zinc-300'}`}>
              <div className="flex items-center gap-2">
                <span className="text-[10px] opacity-70 flex items-center gap-1"><Clock size={10} />{log.timestamp}</span>
                {log.type === 'error' && <CircleDashed size={12} className="text-red-500" />}
              </div>
              <div className="pl-1 border-l border-zinc-700/50 break-words">{log.message}</div>
            </div>
          ))}
        </div>
      </section>

      {/* System Health */}
      <section className="mt-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold">System Matrix</h3>
          <span className="text-[9px] text-[var(--accent-cyan)]/70 font-mono tracking-wider">LIVE TELEMETRY</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1" title="Brain Core — Host CPU & AI compute load">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Cpu size={12}/> Brain Core</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white min-w-[28px]">{systemStats.brainCore}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-700 ease-out ${systemStats.brainCore > 85 ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]' : systemStats.brainCore > 60 ? 'bg-amber-400' : 'bg-blue-500'}`} 
                  style={{ width: `${Math.min(100, Math.max(0, systemStats.brainCore))}%` }} 
                />
              </div>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1" title="Router — RAM utilization & task routing buffers">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Network size={12}/> Router</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white min-w-[28px]">{systemStats.router}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-700 ease-out ${systemStats.router > 85 ? 'bg-[var(--accent-violet)] shadow-[0_0_8px_rgba(124,58,237,0.6)]' : 'bg-[var(--accent-cyan)]'}`} 
                  style={{ width: `${Math.min(100, Math.max(0, systemStats.router))}%` }} 
                />
              </div>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1" title="Vision Engine — Camera & screen analysis status">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Search size={12}/> Vision Engine</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white min-w-[28px]">{systemStats.visionEngine}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[var(--accent-cyan)] transition-all duration-700 ease-out" 
                  style={{ width: `${Math.min(100, Math.max(0, systemStats.visionEngine))}%` }} 
                />
              </div>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1" title="Voice Engine — Speech synthesis & audio processing pipeline">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Server size={12}/> Voice Engine</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white min-w-[28px]">{systemStats.voiceEngine}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[var(--accent-violet)] transition-all duration-700 ease-out" 
                  style={{ width: `${Math.min(100, Math.max(0, systemStats.voiceEngine))}%` }} 
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Backend Connection Status */}
      <section>
        <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-3">Backend Connection</h3>
        <div className="bg-[rgba(0,0,0,0.2)] p-3 rounded-md border border-[rgba(255,255,255,0.03)] flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-medium">
            {backendConnected ? (
              <><Wifi size={14} className="text-green-400" /> <span className="text-green-400">Connected</span></>
            ) : (
              <><WifiOff size={14} className="text-red-400" /> <span className="text-red-400">Offline</span></>
            )}
          </div>
          <span className="text-[10px] text-zinc-500">
            API: {backendConnected ? '8000' : '—'}
          </span>
        </div>
      </section>

      {/* Integrations */}
      <section>
        <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-3">Integrations</h3>
        <div className="bg-[rgba(0,0,0,0.2)] p-3 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-white font-medium">
              <Smartphone size={14} className="text-zinc-400" /> WhatsApp Bridge
            </div>
            <div className="flex items-center gap-1.5 text-[10px]">
              {whatsappStatus === 'connected' ? (
                <><div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> Linked</>
              ) : whatsappStatus === 'waiting_qr' ? (
                <><div className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" /> Scan QR</>
              ) : (
                <><div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Offline</>
              )}
            </div>
          </div>
          
          {whatsappStatus === 'waiting_qr' && (
            <div className="flex flex-col items-center gap-2 mt-2 pb-2">
              {whatsappQr ? (
                <div className="bg-white p-2 rounded-lg inline-block shadow-lg">
                  <img src={whatsappQr} alt="WhatsApp QR Code" className="w-32 h-32 object-contain" />
                </div>
              ) : (
                <div className="w-32 h-32 rounded-lg border border-dashed border-zinc-700 flex flex-col items-center justify-center text-zinc-500 text-[10px] text-center p-2">
                  <CircleDashed size={20} className="animate-spin mb-1 text-[var(--accent-cyan)]" />
                  Generating QR...
                </div>
              )}

              {whatsappPairingCode ? (
                <div className="w-full bg-zinc-900/90 border border-[var(--accent-cyan)]/50 rounded-lg p-2.5 text-center mt-1">
                  <div className="text-[10px] text-zinc-300 font-medium mb-1">WhatsApp Pairing Code</div>
                  <div className="font-mono text-sm tracking-widest text-[var(--accent-cyan)] font-bold select-all bg-black/50 py-1 px-2 rounded border border-[var(--accent-cyan)]/30">
                    {whatsappPairingCode}
                  </div>
                  <div className="text-[9px] text-zinc-400 mt-1">
                    WhatsApp &gt; Linked Devices &gt; Link with phone number instead
                  </div>
                </div>
              ) : null}

              <div className="flex items-center gap-2 mt-1">
                <button
                  onClick={handleResetWhatsApp}
                  disabled={isResetting}
                  className="text-[10px] px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 flex items-center gap-1.5 transition-colors border border-zinc-700"
                  title="Clears stale session credentials on server and generates a fresh QR"
                >
                  <RefreshCw size={11} className={isResetting ? "animate-spin text-[var(--accent-cyan)]" : ""} />
                  {isResetting ? "Resetting..." : "Reset Session"}
                </button>

                <button
                  onClick={handleRequestPairingCode}
                  disabled={isPairingLoading}
                  className="text-[10px] px-2.5 py-1 rounded bg-[rgba(0,212,255,0.1)] hover:bg-[rgba(0,212,255,0.2)] text-[var(--accent-cyan)] flex items-center gap-1.5 transition-colors border border-[rgba(0,212,255,0.3)]"
                  title="Link device with phone number instead of scanning QR"
                >
                  <KeyRound size={11} className={isPairingLoading ? "animate-spin" : ""} />
                  {isPairingLoading ? "Generating..." : "Pairing Code"}
                </button>
              </div>

              <span className="text-[9px] text-zinc-400 text-center leading-tight mt-0.5">
                Scan QR or click <b>Pairing Code</b> to link by phone number.
              </span>
            </div>
          )}

          {/* Telegram Integration */}
          <div className="flex items-center justify-between border-t border-[rgba(255,255,255,0.05)] pt-3 mt-1">
            <div className="flex items-center gap-2 text-xs text-white font-medium">
              <Send size={14} className="text-blue-400" /> Telegram Bot
            </div>
            <div className="flex items-center gap-1.5 text-[10px]">
              {telegramStatus === 'connected' ? (
                <><div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> Linked</>
              ) : (
                <><div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Offline</>
              )}
            </div>
          </div>

        </div>
      </section>

    </div>
  );
}

export function RightPanel() {
  return (
    <motion.div 
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20, delay: 0.2 }}
      className="hidden lg:flex w-80 h-full border-l border-[var(--border-subtle)] bg-[var(--bg-panel)] backdrop-blur-xl flex-col z-10 shrink-0 overflow-y-auto"
    >
      <div className="p-5">
        <RightPanelContent />
      </div>
    </motion.div>
  );
}