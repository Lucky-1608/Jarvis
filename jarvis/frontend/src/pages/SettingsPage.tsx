import { useState } from 'react';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Settings, Cpu, Mic, Monitor, Brain, Shield, Puzzle, Code, Info } from 'lucide-react';
import { motion } from 'framer-motion';

const tabs = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'models', label: 'AI Models', icon: Cpu },
  { id: 'voice', label: 'Voice', icon: Mic },
  { id: 'appearance', label: 'Appearance', icon: Monitor },
  { id: 'memory', label: 'Memory', icon: Brain },
  { id: 'privacy', label: 'Privacy', icon: Shield },
  { id: 'integrations', label: 'Integrations', icon: Puzzle },
  { id: 'advanced', label: 'Advanced', icon: Code },
  { id: 'about', label: 'About', icon: Info },
];

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <PageShell>
      <PageHeader 
        title="System Preferences" 
        description="Core configuration and model tuning"
      />
      
      <div className="flex-1 flex max-w-6xl mx-auto w-full h-[calc(100vh-140px)] py-6 px-4 md:px-8 gap-8">
        
        {/* Sidebar Navigation */}
        <div className="w-64 shrink-0 flex flex-col gap-1">
          {tabs.map(tab => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all relative ${
                  isActive ? 'bg-[rgba(255,255,255,0.05)] text-white' : 'text-zinc-400 hover:text-white hover:bg-[rgba(255,255,255,0.02)]'
                }`}
              >
                {isActive && (
                  <motion.div 
                    layoutId="activeSetting"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[var(--accent-cyan)] rounded-r-full shadow-[0_0_10px_rgba(0,212,255,0.5)]"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <tab.icon size={18} className={isActive ? 'text-[var(--accent-cyan)]' : ''} />
                {tab.label}
              </button>
            )
          })}
        </div>
        
        {/* Main Content Area */}
        <div className="flex-1 bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-2xl p-8 overflow-y-auto">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            
            {activeTab === 'general' && (
              <div className="space-y-8">
                <section>
                  <h2 className="text-xl font-semibold text-white mb-6">Profile Settings</h2>
                  <div className="flex flex-col items-center justify-center p-4">
                    <div className="w-20 h-20 rounded-full bg-[rgba(0,212,255,0.1)] border-2 border-[var(--accent-cyan)] flex items-center justify-center mb-4">
                      <Monitor size={32} className="text-[var(--accent-cyan)]" />
                    </div>
                    <button 
                      onClick={() => toast({ title: 'Not connected', description: 'Cannot change avatar without backend connection.' })}
                      className="px-4 py-2 bg-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.15)] text-white rounded text-sm transition-colors mb-2">Change Avatar</button>
                    <span className="text-xs text-zinc-500">Max size 2MB</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label className="text-xs text-zinc-400 font-medium">Display Name</label>
                      <input type="text" defaultValue="Admin User" className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded p-2.5 text-sm text-white focus:outline-none focus:border-[var(--accent-cyan)]" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs text-zinc-400 font-medium">Email Address</label>
                      <input type="email" defaultValue="admin@nexus.dev" className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded p-2.5 text-sm text-white focus:outline-none focus:border-[var(--accent-cyan)]" />
                    </div>
                  </div>
                </section>
                
                <hr className="border-[rgba(255,255,255,0.05)]" />
                
                <section>
                  <h2 className="text-xl font-semibold text-white mb-6">Preferences</h2>
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-white mb-1">Desktop Notifications</div>
                        <div className="text-xs text-zinc-500">Receive alerts when Jarvis completes a long-running task.</div>
                      </div>
                      <div className="w-10 h-5 bg-[var(--accent-cyan)] rounded-full p-0.5 cursor-pointer">
                        <div className="w-4 h-4 bg-white rounded-full translate-x-5 shadow-sm" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-white mb-1">Sound Effects</div>
                        <div className="text-xs text-zinc-500">Play subtle UI sounds on interactions.</div>
                      </div>
                      <div className="w-10 h-5 bg-[var(--accent-cyan)] rounded-full p-0.5 cursor-pointer">
                        <div className="w-4 h-4 bg-white rounded-full translate-x-5 shadow-sm" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-white mb-1">Session Timeout</div>
                        <div className="text-xs text-zinc-500">Require authentication after inactivity.</div>
                      </div>
                      <select className="bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded p-2 text-sm text-white focus:outline-none">
                        <option>15 minutes</option>
                        <option>1 hour</option>
                        <option>4 hours</option>
                        <option>Never</option>
                      </select>
                    </div>
                  </div>
                </section>
                
                <div className="flex justify-end pt-6 border-t border-[rgba(255,255,255,0.05)]">
                  <button 
                    onClick={() => toast({ title: 'Not connected', description: 'Cannot save settings without backend connection.' })}
                    className="px-6 py-2 bg-[var(--accent-cyan)] text-black font-semibold rounded hover:bg-cyan-400 transition-colors shadow-[0_0_15px_rgba(0,212,255,0.3)]">Save Changes</button>
                </div>
              </div>
            )}
            
            {activeTab === 'models' && (
              <div className="space-y-8">
                <section>
                  <h2 className="text-xl font-semibold text-white mb-2">Connected Models</h2>
                  <p className="text-sm text-zinc-400 mb-6">Manage API connections and model routing preferences.</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-5 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-1 h-full bg-green-500" />
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-base font-semibold text-white">GPT-4o</h3>
                          <span className="text-xs text-zinc-500">OpenAI</span>
                        </div>
                        <div className="w-10 h-5 bg-green-500 rounded-full p-0.5">
                          <div className="w-4 h-4 bg-white rounded-full translate-x-5 shadow-sm" />
                        </div>
                      </div>
                      <div className="flex justify-between items-center text-xs mt-6">
                        <span className="text-green-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400" /> Active</span>
                        <span className="text-zinc-500">Latency: 240ms</span>
                      </div>
                    </div>
                    
                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-5 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-1 h-full bg-[var(--accent-blue)]" />
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-base font-semibold text-white">Claude 3.5 Sonnet</h3>
                          <span className="text-xs text-zinc-500">Anthropic</span>
                        </div>
                        <div className="w-10 h-5 bg-[var(--accent-blue)] rounded-full p-0.5">
                          <div className="w-4 h-4 bg-white rounded-full translate-x-5 shadow-sm" />
                        </div>
                      </div>
                      <div className="flex justify-between items-center text-xs mt-6">
                        <span className="text-[var(--accent-blue)] flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)]" /> Active</span>
                        <span className="text-zinc-500">Latency: 180ms</span>
                      </div>
                    </div>
                    
                    <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-5 relative overflow-hidden">
                      <div className="absolute top-0 right-0 w-1 h-full bg-zinc-600" />
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-base font-semibold text-white">Llama 3 (8B)</h3>
                          <span className="text-xs text-zinc-500">Local (Ollama)</span>
                        </div>
                        <div className="w-10 h-5 bg-zinc-700 rounded-full p-0.5">
                          <div className="w-4 h-4 bg-zinc-400 rounded-full shadow-sm" />
                        </div>
                      </div>
                      <div className="flex justify-between items-center text-xs mt-6">
                        <span className="text-zinc-500 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-zinc-500" /> Offline</span>
                        <span className="text-zinc-500">Connect to start</span>
                      </div>
                    </div>
                  </div>
                </section>
                
                <hr className="border-[rgba(255,255,255,0.05)]" />
                
                <section>
                   <h2 className="text-xl font-semibold text-white mb-6">Model Parameters</h2>
                   <div className="space-y-6 max-w-lg">
                     <div>
                       <div className="flex justify-between mb-2">
                         <label className="text-sm font-medium text-white">Temperature</label>
                         <span className="text-xs text-zinc-400 font-mono">0.7</span>
                       </div>
                       <input type="range" min="0" max="2" step="0.1" defaultValue="0.7" className="w-full accent-[var(--accent-cyan)]" />
                       <div className="flex justify-between text-xs text-zinc-500 mt-1">
                         <span>Precise</span>
                         <span>Creative</span>
                       </div>
                     </div>
                     <div>
                       <label className="text-sm font-medium text-white mb-2 block">Default Routing</label>
                       <select className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded p-2.5 text-sm text-white focus:outline-none focus:border-[var(--accent-cyan)]">
                         <option>Smart Routing (Auto)</option>
                         <option>GPT-4o (Primary)</option>
                         <option>Claude 3.5 Sonnet (Primary)</option>
                       </select>
                     </div>
                   </div>
                </section>
              </div>
            )}
            
            {activeTab === 'appearance' && (
              <div className="space-y-8">
                <section>
                  <h2 className="text-xl font-semibold text-white mb-6">Theme</h2>
                  <div className="flex gap-4">
                    <div className="w-32 h-24 rounded border-2 border-[var(--accent-cyan)] bg-[#020408] p-2 flex flex-col gap-2 cursor-pointer relative">
                       <div className="w-full h-2 bg-zinc-800 rounded" />
                       <div className="w-2/3 h-2 bg-zinc-800 rounded" />
                       <div className="absolute bottom-2 right-2 w-4 h-4 rounded-full bg-[var(--accent-cyan)] flex items-center justify-center"><div className="w-2 h-2 bg-black rounded-full"/></div>
                    </div>
                    <div className="w-32 h-24 rounded border-2 border-[rgba(255,255,255,0.1)] bg-[#ffffff] p-2 flex flex-col gap-2 cursor-not-allowed opacity-50 relative group">
                       <div className="w-full h-2 bg-gray-200 rounded" />
                       <div className="w-2/3 h-2 bg-gray-200 rounded" />
                       <div className="absolute inset-0 bg-black/50 flex items-center justify-center text-[10px] font-bold opacity-0 group-hover:opacity-100 transition-opacity">DARK ONLY</div>
                    </div>
                  </div>
                </section>
                
                <section>
                  <h2 className="text-xl font-semibold text-white mb-4">Accent Color</h2>
                  <div className="flex gap-4">
                    <button className="w-8 h-8 rounded-full bg-[#00d4ff] ring-2 ring-offset-2 ring-offset-[#060a14] ring-[#00d4ff]" />
                    <button className="w-8 h-8 rounded-full bg-[#0080ff] opacity-50 hover:opacity-100 transition-opacity" />
                    <button className="w-8 h-8 rounded-full bg-[#7c3aed] opacity-50 hover:opacity-100 transition-opacity" />
                    <button className="w-8 h-8 rounded-full bg-[#f59e0b] opacity-50 hover:opacity-100 transition-opacity" />
                    <button className="w-8 h-8 rounded-full bg-[#10b981] opacity-50 hover:opacity-100 transition-opacity" />
                    <button className="w-8 h-8 rounded-full bg-[#ef4444] opacity-50 hover:opacity-100 transition-opacity" />
                  </div>
                </section>
                
                <section className="max-w-lg">
                  <h2 className="text-xl font-semibold text-white mb-6">Visual Effects</h2>
                  <div className="space-y-6">
                    <div>
                      <div className="flex justify-between mb-2">
                        <label className="text-sm font-medium text-white">Panel Opacity</label>
                        <span className="text-xs text-zinc-400 font-mono">70%</span>
                      </div>
                      <input type="range" min="0" max="100" defaultValue="70" className="w-full accent-[var(--accent-cyan)]" />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-white mb-2 block">Animation Intensity</label>
                      <select className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded p-2.5 text-sm text-white focus:outline-none focus:border-[var(--accent-cyan)]">
                         <option>Full (Cinematic)</option>
                         <option>Subtle</option>
                         <option>Reduced Motion</option>
                       </select>
                    </div>
                  </div>
                </section>
              </div>
            )}
            
            {/* Placeholder for other tabs */}
            {!['general', 'models', 'appearance'].includes(activeTab) && (
              <div className="h-64 flex flex-col items-center justify-center text-zinc-500">
                 <Settings size={48} className="mb-4 opacity-20" />
                 <p>Settings panel for {activeTab} is under construction.</p>
              </div>
            )}
            
          </motion.div>
        </div>
        
      </div>
    </PageShell>
  );
}