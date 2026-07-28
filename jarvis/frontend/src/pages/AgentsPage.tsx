import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Users, Bot, Activity, Brain, Server, ShieldCheck, Power, Play, Square, WifiOff } from 'lucide-react';
import { api } from '../lib/api';

type ApiActionError = {
  status: number;
  detail: string;
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100 } }
};

export function AgentsPage() {
  const [selectedType, setSelectedType] = useState<string>('All');
  const [agents, setAgents] = useState<any[]>([]);
  const [stats, setStats] = useState({ total: 0, running: 0, completed: 0, idle: 0 });
  const [loading, setLoading] = useState(true);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  const showActionError = (action: 'spawn' | 'wake' | 'terminate', error: ApiActionError) => {
    if (error.status === 0) {
      setBackendConnected(false);
      toast({
        title: 'Backend not connected',
        description: `Cannot ${action} agent - backend is unreachable.`,
      });
      return;
    }

    setBackendConnected(true);
    toast({
      title: `Cannot ${action} agent`,
      description: error.detail || `Backend rejected the ${action} request.`,
    });
  };

  const fetchAgents = async () => {
    setLoading(true);

    const [agentsRes, statsRes] = await Promise.all([
      api.get<any>('/api/agents'),
      api.get<any>('/api/agents/stats'),
    ]);

    if (!agentsRes.ok) {
      setBackendConnected(agentsRes.status !== 0);
    } else if (agentsRes.data.agents) {
      setAgents(agentsRes.data.agents);
      setBackendConnected(true);
    }

    if (statsRes.ok) {
      setStats(statsRes.data);
    }

    setLoading(false);
  };

  useEffect(() => { fetchAgents(); }, []);

  const handleSpawn = async () => {
    const res = await api.post<any>('/api/agents/spawn', {
      name: 'DelegatedExpert',
      persona: 'You are a specialized AI assistant.',
      task: '',
    });
    if (res.ok && res.data.success) {
      toast({ title: 'Agent spawned', description: `${res.data.agent.name} created successfully.` });
      fetchAgents();
    } else if (!res.ok) {
      showActionError('spawn', res);
    }
  };

  const handleWake = async (agentId: string) => {
    const res = await api.post<any>(`/api/agents/${agentId}/wake`);
    if (res.ok && res.data.success) {
      toast({ title: 'Agent woken', description: 'Agent is now active.' });
      fetchAgents();
    } else if (!res.ok) {
      showActionError('wake', res);
    }
  };

  const handleTerminate = async (agentId: string) => {
    const res = await api.post<any>(`/api/agents/${agentId}/terminate`);
    if (res.ok && res.data.success) {
      toast({ title: 'Agent terminated', description: 'Agent has been stopped.' });
      fetchAgents();
    } else if (!res.ok) {
      showActionError('terminate', res);
    }
  };

  const types = ['All', 'SystemAgent', 'SubAgent', 'BackgroundAgent'];
  const filteredAgents = agents.filter(a => selectedType === 'All' || a.type === selectedType);

  const formatRelativeTime = (ts: number | null) => {
    if (!ts) return 'Always On';
    const diff = Math.floor((Date.now() / 1000) - ts);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-green-400 bg-green-400/10 border-green-400/20';
      case 'idle': return 'text-[var(--accent-cyan)] bg-[var(--accent-cyan)]/10 border-[var(--accent-cyan)]/20';
      case 'completed': return 'text-[var(--accent-violet)] bg-[var(--accent-violet)]/10 border-[var(--accent-violet)]/20';
      case 'sleeping': return 'text-zinc-400 bg-zinc-400/10 border-zinc-400/20';
      default: return 'text-zinc-400 bg-zinc-400/10 border-zinc-400/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <Activity size={12} className="animate-pulse" />;
      case 'idle': return <ShieldCheck size={12} />;
      case 'sleeping': return <Power size={12} />;
      default: return null;
    }
  };

  return (
    <PageShell>
      <PageHeader 
        title="Agent Swarm" 
        description="Monitor and manage autonomous background agents and specialized sub-agents."
        actions={
          <button 
            onClick={handleSpawn}
            className="px-4 py-2 bg-[var(--accent-cyan)] text-black rounded-md text-sm font-bold hover:bg-[rgba(0,212,255,0.8)] transition-colors shadow-[0_0_15px_rgba(0,212,255,0.3)] flex items-center gap-2">
            <Users size={16} /> Spawn Agent
          </button>
        }
      />
      
      <div className="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col gap-6">
        
        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.2)] flex items-center justify-center text-[var(--accent-cyan)]">
              <Users size={20} />
            </div>
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Total Agents</p>
              <h3 className="text-2xl font-bold text-white">{stats.total}</h3>
            </div>
          </div>
          
          <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400">
              <Activity size={20} />
            </div>
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Active Tasks</p>
              <h3 className="text-2xl font-bold text-white">{stats.running}</h3>
            </div>
          </div>
          
          <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-[var(--accent-violet)]/10 border border-[var(--accent-violet)]/20 flex items-center justify-center text-[var(--accent-violet)]">
              <Server size={20} />
            </div>
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Idle Agents</p>
              <h3 className="text-2xl font-bold text-white">{stats.idle}</h3>
            </div>
          </div>
          
          <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <Brain size={20} />
            </div>
            <div>
              <p className="text-xs text-zinc-400 uppercase tracking-widest font-mono">Completed</p>
              <h3 className="text-2xl font-bold text-white">{stats.completed}</h3>
            </div>
          </div>
        </div>
        
        {/* Backend Offline Banner */}
      {backendConnected === false && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
          <WifiOff size={16} />
          <span className="font-medium">Backend offline</span>
          <span className="text-red-400/70 text-xs">API calls are not reaching the server. Start the backend with <code className="px-1.5 py-0.5 bg-black/30 rounded font-mono">python -m jarvis serve</code></span>
        </div>
      )}

      {/* Filters */}
        <div className="flex gap-2 border-b border-[rgba(255,255,255,0.05)] pb-4">
          {types.map(t => (
            <button 
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selectedType === t ? 'bg-[rgba(255,255,255,0.1)] text-white' : 'text-zinc-500 hover:text-zinc-300 hover:bg-[rgba(255,255,255,0.05)]'}`}
            >
              {t === 'All' ? 'All Agents' : t + 's'}
            </button>
          ))}
        </div>
        
        {/* Agents Grid */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          {filteredAgents.map(agent => (
            <motion.div 
              key={agent.id}
              variants={itemVariants}
              className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-xl p-5 hover:border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.03)] transition-colors flex flex-col"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${agent.type === 'SubAgent' ? 'bg-[var(--accent-violet)]/10 border-[var(--accent-violet)]/20 text-[var(--accent-violet)]' : agent.type === 'SystemAgent' ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-[var(--accent-cyan)]/10 border-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]'}`}>
                    {agent.type === 'SystemAgent' ? <Server size={20} /> : <Bot size={20} />}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{agent.name}</h3>
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-mono">{agent.type}</p>
                  </div>
                </div>
                
                <div className={`px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 ${getStatusColor(agent.status)}`}>
                  {getStatusIcon(agent.status)}
                  {agent.status}
                </div>
              </div>
              
              <p className="text-xs text-zinc-400 mb-2 flex-1 leading-relaxed">
                {agent.persona}
              </p>
              {agent.task && (
                <p className="text-[10px] text-zinc-500 mb-4 font-mono bg-[rgba(0,0,0,0.3)] px-2 py-1 rounded">
                  ▸ {agent.task}
                </p>
              )}
              
              <div className="flex items-center justify-between py-3 border-t border-[rgba(255,255,255,0.05)] mt-auto">
                <div className="flex flex-col">
                  <span className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono mb-0.5">Uptime</span>
                  <span className="text-xs text-zinc-300">
                    {agent.completed_at ? 'Completed' : agent.status === 'running' ? 'Active' : 'Idle'}
                  </span>
                </div>
                <div className="flex flex-col text-right">
                  <span className="text-[10px] text-zinc-600 uppercase tracking-widest font-mono mb-0.5">Last Active</span>
                  <span className="text-xs text-zinc-300">
                    {formatRelativeTime(agent.created_at)}
                  </span>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-2 mt-4">
                <button 
                  onClick={() => handleWake(agent.id)}
                  className="flex items-center justify-center gap-2 py-2 rounded bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-xs font-medium text-white transition-colors">
                  <Play size={12} /> Wake
                </button>
                <button 
                  onClick={() => handleTerminate(agent.id)}
                  className="flex items-center justify-center gap-2 py-2 rounded bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-xs font-medium text-red-400 transition-colors">
                  <Square size={12} /> Terminate
                </button>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </PageShell>
  );
}
