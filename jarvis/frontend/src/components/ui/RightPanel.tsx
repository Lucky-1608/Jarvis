import { motion } from 'framer-motion';
import { useJarvisStore } from '../../store/jarvisStore';
import { Cpu, Database, Network, Server, CheckCircle2, CircleDashed, Clock, ChevronRight, Search, FileText, Code2, Smartphone, WifiOff, Wifi, Send } from 'lucide-react';

const ToolIcon = ({ name }: { name: string }) => {
  if (name.includes('Search')) return <Search size={14} className="text-blue-400" />;
  if (name.includes('File')) return <FileText size={14} className="text-yellow-400" />;
  if (name.includes('Code')) return <Code2 size={14} className="text-purple-400" />;
  return <ChevronRight size={14} className="text-zinc-400" />;
};

export function RightPanelContent({ className = '' }: { className?: string }) {
  const { currentTask, systemStats, whatsappStatus, whatsappQr, telegramStatus, backendConnected } = useJarvisStore();

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
        <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-3">System Matrix</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Cpu size={12}/> Brain Core</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white">{systemStats.brainCore}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500" style={{ width: `${systemStats.brainCore}%` }} />
              </div>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Network size={12}/> Router</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white">{systemStats.router}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div className={`h-full ${systemStats.router > 80 ? 'bg-[var(--accent-violet)]' : 'bg-[var(--accent-cyan)]'}`} style={{ width: `${systemStats.router}%` }} />
              </div>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Search size={12}/> Vision Engine</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white">{systemStats.visionEngine}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-[var(--accent-cyan)]" style={{ width: `${systemStats.visionEngine}%` }} />
              </div>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] p-2 rounded-md border border-[rgba(255,255,255,0.03)] flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-[10px] text-zinc-400"><Server size={12}/> Voice Engine</div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-white">{systemStats.voiceEngine}%</span>
              <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-[var(--accent-violet)]" style={{ width: `${systemStats.voiceEngine}%` }} />
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
          
          {whatsappStatus === 'waiting_qr' && whatsappQr && (
            <div className="flex flex-col items-center gap-2 mt-2 pb-2">
              <div className="bg-white p-2 rounded-lg inline-block shadow-lg">
                <img src={whatsappQr} alt="WhatsApp QR Code" className="w-32 h-32 object-contain" />
              </div>
              <span className="text-[10px] text-zinc-400 text-center">Open WhatsApp on your phone<br/>and go to Linked Devices</span>
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