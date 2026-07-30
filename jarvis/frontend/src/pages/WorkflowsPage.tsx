import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Network, CheckCircle2, Circle, Clock, Play, AlertTriangle, ArrowRight, Waypoints, Brain } from 'lucide-react';
import { BASE } from '../lib/api';


const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0, transition: { type: 'spring' as const, stiffness: 100 } }
};

export function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'execution' | 'n8n'>('execution');

  useEffect(() => {
    fetch(`${BASE}/api/workflows`, { headers: { 'X-API-Key': 'JARVIS_DEV_KEY' } })
      .then(r => r.json())
      .then(data => { if (data.workflows) setWorkflows(data.workflows); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  
  const activePlan = workflows.find(w => w.id === selectedWorkflow) || null;

  const formatRelativeTime = (ts: number) => {
    const diff = Math.floor((Date.now() / 1000) - ts);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={16} className="text-green-400" />;
      case 'running': return <Play size={16} className="text-[var(--accent-cyan)] fill-[var(--accent-cyan)]/20 animate-pulse" />;
      case 'blocked': return <AlertTriangle size={16} className="text-yellow-400" />;
      case 'pending': return <Circle size={16} className="text-zinc-600" />;
      default: return <Circle size={16} className="text-zinc-600" />;
    }
  };

  const getBadgeClass = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-400/10 text-green-400 border-green-400/20';
      case 'running': return 'bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)] border-[var(--accent-cyan)]/20';
      case 'blocked': return 'bg-yellow-400/10 text-yellow-400 border-yellow-400/20';
      default: return 'bg-zinc-800 text-zinc-400 border-zinc-700';
    }
  };

  return (
    <PageShell>
      <PageHeader 
        title="Execution Workflows" 
        description="Visualize how the AI Planner decomposes complex tasks into ordered tool operations, or build custom workflows with n8n."
        actions={
          <div className="flex items-center gap-2 bg-[rgba(255,255,255,0.05)] p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('execution')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'execution' ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] shadow-sm' : 'text-zinc-400 hover:text-white'}`}
            >
              <Network size={16} /> Execution Plans
            </button>
            <button
              onClick={() => setActiveTab('n8n')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'n8n' ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] shadow-sm' : 'text-zinc-400 hover:text-white'}`}
            >
              <Waypoints size={16} /> Custom Workflows
            </button>
          </div>
        }
      />
      
      {activeTab === 'execution' ? (
      <div className="flex-1 flex flex-col lg:flex-row p-6 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column - Workflow List */}
        <div className="w-full lg:w-1/3 flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-180px)] pr-2 scrollbar-thin">
          <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2">Recent Execution Plans</div>
          
          {workflows.length === 0 ? (
            <div className="text-zinc-500 text-sm text-center p-4">No workflows yet. Send a message to Jarvis to generate execution plans.</div>
          ) : (
            workflows.map(workflow => (
            <div 
              key={workflow.id}
              onClick={() => setSelectedWorkflow(workflow.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedWorkflow === workflow.id ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] shadow-lg' : 'bg-[rgba(255,255,255,0.02)] border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.04)] hover:border-[rgba(255,255,255,0.06)]'}`}
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-[10px] font-mono text-zinc-500 bg-[rgba(0,0,0,0.4)] px-2 py-0.5 rounded">{workflow.id}</span>
                <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                  <Clock size={10} /> {typeof workflow.timestamp === 'number' ? formatRelativeTime(workflow.timestamp) : workflow.timestamp}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-white mb-3 line-clamp-2 leading-relaxed">{workflow.goal}</h3>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${getBadgeClass(workflow.status)}`}>
                  {workflow.status}
                </span>
                <span className="text-xs text-zinc-500 font-mono">
                  {workflow.steps.length} {workflow.steps.length === 1 ? 'step' : 'steps'}
                </span>
              </div>
            </div>
          )))}
        </div>
        
        {/* Right Column - Plan Inspector */}
        <div className="w-full lg:w-2/3">
          {activePlan ? (
            <div className="bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] rounded-xl h-full p-6 flex flex-col">
              
              <div className="flex items-start gap-4 mb-6 pb-6 border-b border-[rgba(255,255,255,0.05)]">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${activePlan.status === 'completed' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : activePlan.status === 'running' ? 'bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)] border border-[var(--accent-cyan)]/20' : activePlan.status === 'blocked' ? 'bg-yellow-400/10 text-yellow-400 border border-yellow-400/20' : 'bg-zinc-800 text-zinc-400 border border-zinc-700'}`}>
                  {activePlan.status === 'completed' ? <CheckCircle2 size={24} /> : activePlan.status === 'running' ? <Play size={24} className="ml-1" /> : activePlan.status === 'blocked' ? <AlertTriangle size={24} /> : <Waypoints size={24} />}
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500">{activePlan.id}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getBadgeClass(activePlan.status)}`}>{activePlan.status}</span>
                  </div>
                  <h2 className="text-lg font-bold text-white leading-snug">{activePlan.goal}</h2>
                </div>
              </div>
              
              <div className="mb-8">
                <h4 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-3 flex items-center gap-2"><Brain size={12}/> Planner Reasoning</h4>
                <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 text-sm text-zinc-300 italic border-l-2 border-l-[var(--accent-violet)]">
                  "{activePlan.reasoning}"
                </div>
              </div>
              
              {activePlan.requires_confirmation && activePlan.status === 'blocked' && (
                <div className="mb-8 bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-4 flex items-start gap-3">
                  <AlertTriangle size={18} className="text-yellow-400 mt-0.5 shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-yellow-400 mb-1">Confirmation Required</h4>
                    <p className="text-xs text-yellow-400/80 mb-3">This plan involves dangerous tools that require user authorization.</p>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => toast({ title: 'Not connected', description: 'Authorization requires a live backend connection.' })}
                        className="px-4 py-2 bg-yellow-400 text-black text-xs font-bold rounded hover:bg-yellow-500 transition-colors">Authorize Plan</button>
                      <button 
                        onClick={() => toast({ title: 'Cancelled', description: 'Plan execution cancelled.' })}
                        className="px-4 py-2 bg-[rgba(255,255,255,0.1)] text-white text-xs font-medium rounded hover:bg-[rgba(255,255,255,0.15)] transition-colors">Cancel</button>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="flex-1">
                <h4 className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-4 flex items-center gap-2"><Network size={12}/> Execution Steps</h4>
                
                {activePlan.steps.length === 0 ? (
                  <div className="text-center p-8 bg-[rgba(255,255,255,0.01)] rounded-lg border border-[rgba(255,255,255,0.02)] text-zinc-500 text-sm flex flex-col items-center">
                    <CheckCircle2 size={32} className="mb-3 opacity-20" />
                    This task was simple enough to answer directly.<br/>No tool execution steps were generated.
                  </div>
                ) : (
                  <motion.div variants={containerVariants} initial="hidden" animate="show" className="relative pl-6 border-l-2 border-zinc-800/50 space-y-8">
                    {activePlan.steps.map((step: any, index: number) => (
                      <motion.div key={step.id} variants={itemVariants} className="relative">
                        <div className={`absolute -left-[35px] bg-[#020408] rounded-full border-2 ${step.status === 'completed' ? 'border-[#020408]' : 'border-[#020408]'}`}>
                          {getStatusIcon(step.status)}
                        </div>
                        
                        <div className={`p-4 rounded-lg border ${step.status === 'running' ? 'bg-[rgba(0,212,255,0.03)] border-[rgba(0,212,255,0.2)] shadow-[0_0_15px_rgba(0,212,255,0.05)]' : 'bg-[rgba(255,255,255,0.02)] border-[rgba(255,255,255,0.05)]'}`}>
                          <div className="flex justify-between items-start mb-2">
                            <h5 className={`text-sm font-bold ${step.status === 'completed' ? 'text-zinc-300' : step.status === 'running' ? 'text-white' : 'text-zinc-500'}`}>
                              Step {index + 1}: {step.description}
                            </h5>
                          </div>
                          
                          {step.tool && (
                            <div className="mt-3 flex items-center gap-2">
                              <span className="text-[10px] uppercase tracking-widest font-mono text-zinc-500 bg-[rgba(0,0,0,0.5)] px-2 py-1 rounded">Tool Call</span>
                              <span className={`text-xs font-mono px-2 py-1 rounded border ${step.status === 'running' ? 'bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)] border-[var(--accent-cyan)]/20' : 'bg-[rgba(255,255,255,0.05)] text-zinc-400 border-[rgba(255,255,255,0.1)]'}`}>
                                {step.tool}()
                              </span>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </div>
              
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-zinc-500 bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] rounded-xl">
              <Network size={48} className="mb-4 opacity-20" />
              <p className="text-sm text-center">Select an execution plan to<br/>inspect its steps and reasoning</p>
            </div>
          )}
        </div>
      </div>
      ) : (
        <div className="flex-1 flex flex-col p-6 max-w-[1600px] mx-auto w-full h-[calc(100vh-140px)]">
          <div className="bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] rounded-xl overflow-hidden h-full flex flex-col relative">
            <div className="absolute top-0 left-0 w-full p-3 bg-[#0a0a0a] border-b border-[rgba(255,255,255,0.05)] flex justify-between items-center z-10 text-xs text-zinc-400 font-medium shadow-sm">
              <span className="flex items-center gap-2"><Waypoints size={14} className="text-[var(--accent-cyan)]"/> Embedded n8n Instance (localhost:5678)</span>
              <a href="http://localhost:5678" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--accent-cyan)] flex items-center gap-1 transition-colors">Open in New Tab <ArrowRight size={12}/></a>
            </div>
            <iframe 
              src="http://localhost:5678" 
              title="n8n Custom Workflows"
              className="w-full h-full flex-1 pt-[44px] border-0"
              allow="clipboard-read; clipboard-write"
            />
          </div>
        </div>
      )}
    </PageShell>
  );
}
