import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Search, Wrench, ShieldAlert, Zap, Box, TerminalSquare, AlertTriangle, ArrowRight } from 'lucide-react';
import { BASE } from '../lib/api';
interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
}

interface Tool {
  name: string;
  description: string;
  category: string;
  dangerous: boolean;
  parameters: ToolParameter[];
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100 } }
};

export function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [filter, setFilter] = useState('All');
  
  useEffect(() => {
    fetch(`${BASE}/api/tools`, {
      headers: {
        'X-API-Key': 'JARVIS_DEV_KEY'
      }
    })
      .then(res => res.json())
      .then(data => {
        if (data && data.tools) {
          setTools(data.tools);
        }
      })
      .catch(err => console.error('Failed to fetch tools:', err))
      .finally(() => setLoading(false));
  }, []);

  const activeTool = tools.find(t => t.name === selectedTool) || null;
  
  const categories = ['All', ...Array.from(new Set(tools.map(t => t.category)))];
  const filteredTools = tools.filter(t => filter === 'All' || t.category === filter);

  return (
    <PageShell>
      <PageHeader 
        title="Tools & Capabilities" 
        description="Manage and monitor available AI capabilities and registered tools"
        actions={
          <button 
            onClick={() => toast({ title: 'Not connected', description: 'Cannot install tools without backend API.' })}
            className="px-4 py-2 bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.3)] text-[var(--accent-cyan)] rounded-md text-sm font-medium hover:bg-[rgba(0,212,255,0.2)] transition-colors shadow-[0_0_15px_rgba(0,212,255,0.1)] flex items-center gap-2">
            <Box size={16} /> Registry
          </button>
        }
      />
      
      <div className="flex-1 flex flex-col md:flex-row p-6 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column */}
        <div className="w-full md:w-[60%] flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input 
                type="text" 
                placeholder="Search registered tools..." 
                className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded-md py-2 pl-9 pr-4 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[var(--accent-cyan)] focus:ring-1 focus:ring-[var(--accent-cyan)] transition-all"
              />
            </div>
          </div>
          
          <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
            {categories.map(c => (
              <button 
                key={c}
                onClick={() => setFilter(c)}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors border capitalize ${filter === c ? 'bg-[rgba(255,255,255,0.1)] border-[rgba(255,255,255,0.2)] text-white' : 'bg-transparent border-transparent text-zinc-400 hover:text-white hover:bg-[rgba(255,255,255,0.05)]'}`}
              >
                {c}
              </button>
            ))}
          </div>
          
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto max-h-[600px] pr-2 pb-4"
          >
            {filteredTools.map(tool => (
              <motion.div 
                key={tool.name}
                variants={itemVariants}
                onClick={() => setSelectedTool(tool.name)}
                className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col h-full ${selectedTool === tool.name ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] shadow-lg' : 'bg-[rgba(255,255,255,0.02)] border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.04)] hover:border-[rgba(255,255,255,0.06)]'}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.05)] flex items-center justify-center">
                    {tool.dangerous ? <ShieldAlert size={18} className="text-red-400" /> : <Wrench size={18} className="text-[var(--accent-cyan)]" />}
                  </div>
                  <span className="text-[10px] uppercase tracking-widest px-2 py-1 rounded bg-[rgba(0,0,0,0.4)] text-zinc-400 font-mono">
                    {tool.category}
                  </span>
                </div>
                
                <h3 className="text-sm font-semibold text-white mb-1">{tool.name}</h3>
                <p className="text-xs text-zinc-400 line-clamp-2 mb-4 flex-1">{tool.description}</p>
                
                <div className="flex items-center justify-between pt-3 border-t border-[rgba(255,255,255,0.05)]">
                  <span className="text-xs text-zinc-500 font-mono flex items-center gap-1"><TerminalSquare size={12}/> {tool.parameters.length} params</span>
                  {tool.dangerous && <span className="text-[10px] text-red-400 flex items-center gap-1 font-semibold uppercase tracking-wider"><AlertTriangle size={10}/> restricted</span>}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
        
        {/* Right Column - Inspector */}
        <div className="w-full md:w-[40%]">
          <div className="sticky top-6 bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] rounded-xl p-6 h-fit min-h-[400px]">
            <div className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-6 flex justify-between items-center">
              <span>Tool Inspector</span>
              <span className="text-zinc-500 font-mono">ID: {activeTool ? activeTool.name : 'NONE'}</span>
            </div>
            
            {activeTool ? (
              <>
                <div className="flex items-center gap-3 mb-6">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${activeTool.dangerous ? 'bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)]' : 'bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.2)]'}`}>
                    {activeTool.dangerous ? <ShieldAlert size={20} className="text-red-400" /> : <Wrench size={20} className="text-[var(--accent-cyan)]" />}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white tracking-wide">{activeTool.name}</h3>
                    <span className="text-xs text-zinc-400 uppercase tracking-widest font-mono">{activeTool.category} module</span>
                  </div>
                </div>
                
                <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 mb-6">
                  <p className="text-sm text-zinc-300 leading-relaxed">{activeTool.description}</p>
                </div>
                
                {activeTool.dangerous && (
                  <div className="mb-6 bg-[rgba(239,68,68,0.1)] border border-red-500/20 rounded-lg p-3 flex items-start gap-3">
                    <AlertTriangle size={16} className="text-red-400 mt-0.5 shrink-0" />
                    <div>
                      <h4 className="text-sm font-semibold text-red-400 mb-1">Restricted Tool</h4>
                      <p className="text-xs text-red-400/80">This tool has full system access and can perform destructive actions. Explicit authorization required.</p>
                    </div>
                  </div>
                )}
                
                <div className="mb-8">
                  <h4 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-3">Parameters Payload</h4>
                  <div className="bg-[#0a0a0a] border border-zinc-800 rounded-lg overflow-hidden">
                    {activeTool.parameters.length > 0 ? (
                      <table className="w-full text-left text-sm">
                        <thead className="bg-[rgba(255,255,255,0.02)] border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                          <tr>
                            <th className="p-3 font-medium">Name</th>
                            <th className="p-3 font-medium">Type</th>
                            <th className="p-3 font-medium">Req</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                          {activeTool.parameters.map((p, i) => (
                            <tr key={i} className="hover:bg-[rgba(255,255,255,0.01)] transition-colors">
                              <td className="p-3 font-mono text-zinc-300">{p.name}</td>
                              <td className="p-3 font-mono text-[var(--accent-violet)]">{p.type}</td>
                              <td className="p-3">
                                {p.required ? <span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> : <span className="w-2 h-2 rounded-full bg-zinc-600 inline-block" />}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="p-4 text-center text-xs font-mono text-zinc-500">
                        {'{ }'} NO_PARAMETERS_REQUIRED
                      </div>
                    )}
                  </div>
                </div>
                
                <button 
                  onClick={() => {
                    fetch(`${BASE}/api/tools/execute`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'JARVIS_DEV_KEY' },
                      body: JSON.stringify({ tool_name: activeTool.name, params: {} })
                    })
                      .then(r => r.json())
                      .then(data => {
                        toast({ title: data.success !== false ? 'Tool Executed' : 'Execution Failed', description: JSON.stringify(data).substring(0, 200) });
                      })
                      .catch(err => toast({ title: 'Error', description: err.message }));
                  }}
                  className={`w-full py-3 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 ${activeTool.dangerous ? 'bg-red-500 hover:bg-red-600 text-white shadow-[0_0_15px_rgba(239,68,68,0.3)]' : 'bg-[var(--accent-cyan)] hover:bg-[rgba(0,212,255,0.8)] text-black shadow-[0_0_15px_rgba(0,212,255,0.3)]'}`}>
                  <Zap size={16} /> Execute Test Payload <ArrowRight size={14} />
                </button>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
                <Wrench size={48} className="mb-4 opacity-20" />
                <p className="text-sm text-center">Select a tool from the registry<br/>to inspect its capabilities</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
