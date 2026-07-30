import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Search, Brain, Book, Code, Settings, Pin, Trash2, Tag, Calendar, ChevronRight, Activity, Plus, Edit3 } from 'lucide-react';
import { api } from '../lib/api';


const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100 } }
};

const TypeIcon = ({ type }: { type: string }) => {
  if (type === 'episodic') return <Brain size={16} className="text-[var(--accent-cyan)]" />;
  if (type === 'semantic') return <Book size={16} className="text-[var(--accent-violet)]" />;
  if (type === 'procedural') return <Code size={16} className="text-[var(--accent-gold)]" />;
  return <Settings size={16} />;
};

export function MemoryPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState('All');
  const [memories, setMemories] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [memoryStats, setMemoryStats] = useState<any>(null);

  const loadRecentMemories = () => {
    api.get('/api/memory/recent?limit=20')
      .then(res => {
        if (res.ok && res.data.results) {
          const data = res.data;
          setMemories(data.results.map((r: any) => ({
            id: r.id,
            title: r.content.substring(0, 60) + (r.content.length > 60 ? '...' : ''),
            content: r.content,
            type: r.memory_type === 'conversations' ? 'episodic' : r.memory_type === 'knowledge' ? 'semantic' : 'procedural',
            timestamp: new Date(r.timestamp * 1000).toLocaleDateString(),
            relevance: Math.round(r.score * 100),
            importance: r.importance,
            tags: [],
            connections: [],
          })));
        }
      })
      .catch(console.error);
  };

  useEffect(() => {
    api.get('/api/memory/stats')
      .then(res => res.ok && setMemoryStats(res.data))
      .catch(console.error);
      
    loadRecentMemories();
  }, []);

  const searchMemories = (query: string) => {
    if (!query.trim()) { 
      loadRecentMemories();
      return; 
    }
    api.get(`/api/memory/search?query=${encodeURIComponent(query)}&limit=20`)
      .then(res => {
        if (res.ok && res.data.results) {
          const data = res.data;
          setMemories(data.results.map((r: any) => ({
            id: r.id,
            title: r.content.substring(0, 60) + (r.content.length > 60 ? '...' : ''),
            content: r.content,
            type: r.memory_type === 'conversations' ? 'episodic' : r.memory_type === 'knowledge' ? 'semantic' : 'procedural',
            timestamp: new Date(r.timestamp * 1000).toLocaleDateString(),
            relevance: Math.round(r.score * 100),
            importance: r.importance,
            tags: [],
            connections: [],
          })));
        }
      })
      .catch(console.error);
  };
  
  const selectedMemory = memories.find(m => m.id === selectedId) || null;

  const filteredMemories = memories.filter(m => filter === 'All' || m.type === filter.toLowerCase());

  return (
    <PageShell>
      <PageHeader 
        title="Memory Core" 
        description="Neural knowledge graph and long-term storage"
        actions={
          <button 
            onClick={() => {
              api.post('/api/memory', { content: 'New memory created via UI', memory_type: 'knowledge' })
                .then(res => {
                  if (res.ok) toast({ title: 'Memory Added', description: 'Memory successfully saved.' });
                })
                .catch(console.error);
            }}
            className="px-4 py-2 bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.3)] text-[var(--accent-cyan)] rounded-md text-sm font-medium hover:bg-[rgba(0,212,255,0.2)] transition-colors shadow-[0_0_15px_rgba(0,212,255,0.1)] flex items-center gap-2">
            <Plus size={16} /> Add Memory
          </button>
        }
      />
      
      <div className="flex-1 flex flex-col md:flex-row p-6 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column */}
        <div className="w-full md:w-[60%] flex flex-col gap-6">
          
          {/* Memory Graph */}
          <div className="w-full h-[280px] bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] rounded-xl relative overflow-hidden flex items-center justify-center">
            <div className="absolute top-4 left-4 text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold z-10">Neural Map</div>
            
            {/* Simulated Nodes with static relative positions for stability but pulsing animations */}
            <div className="relative w-[80%] h-[80%]">
              {/* Lines */}
              <svg className="absolute inset-0 w-full h-full overflow-visible pointer-events-none">
                <motion.line x1="50%" y1="50%" x2="20%" y2="30%" stroke="rgba(0,212,255,0.2)" strokeWidth="1" animate={{ opacity: [0.2, 0.5, 0.2] }} transition={{ repeat: Infinity, duration: 3 }} />
                <motion.line x1="50%" y1="50%" x2="80%" y2="25%" stroke="rgba(124,58,237,0.2)" strokeWidth="2" animate={{ opacity: [0.2, 0.6, 0.2] }} transition={{ repeat: Infinity, duration: 4, delay: 1 }} />
                <motion.line x1="50%" y1="50%" x2="70%" y2="80%" stroke="rgba(245,158,11,0.2)" strokeWidth="1" />
                <motion.line x1="20%" y1="30%" x2="15%" y2="60%" stroke="rgba(0,212,255,0.1)" strokeWidth="1" />
                <motion.line x1="80%" y1="25%" x2="90%" y2="60%" stroke="rgba(124,58,237,0.1)" strokeWidth="1" />
              </svg>
              
              {/* Nodes */}
              <motion.div 
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-[rgba(0,212,255,0.2)] border-2 border-[var(--accent-cyan)] shadow-[0_0_20px_rgba(0,212,255,0.4)] flex items-center justify-center cursor-pointer z-10"
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ repeat: Infinity, duration: 4 }}
              >
                <div className="w-2 h-2 rounded-full bg-white" />
              </motion.div>
              
              <motion.div className="absolute top-[30%] left-[20%] -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-[rgba(0,212,255,0.1)] border border-[var(--accent-cyan)] cursor-pointer z-10" whileHover={{ scale: 1.2 }} />
              <motion.div className="absolute top-[25%] left-[80%] -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-[rgba(124,58,237,0.2)] border-2 border-[var(--accent-violet)] shadow-[0_0_15px_rgba(124,58,237,0.3)] cursor-pointer z-10" whileHover={{ scale: 1.2 }} />
              <motion.div className="absolute top-[80%] left-[70%] -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-[rgba(245,158,11,0.1)] border border-[var(--accent-gold)] cursor-pointer z-10" whileHover={{ scale: 1.2 }} />
              <motion.div className="absolute top-[60%] left-[15%] -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-[rgba(0,212,255,0.2)] border border-[var(--accent-cyan)] cursor-pointer z-10" whileHover={{ scale: 1.2 }} />
              <motion.div className="absolute top-[60%] left-[90%] -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-[rgba(124,58,237,0.1)] border border-[var(--accent-violet)] cursor-pointer z-10" whileHover={{ scale: 1.2 }} />
            </div>
          </div>
          
          {/* List Area */}
          <div className="flex flex-col gap-4 flex-1">
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input 
                  type="text" 
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && searchMemories(searchQuery)}
                  placeholder="Search memory graph..." 
                  className="w-full bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.1)] rounded-md py-2 pl-9 pr-4 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[var(--accent-cyan)] focus:ring-1 focus:ring-[var(--accent-cyan)] transition-all"
                />
              </div>
            </div>
            
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
              {['All', 'Episodic', 'Semantic', 'Procedural', 'Pinned'].map(f => (
                <button 
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors border ${filter === f ? 'bg-[rgba(255,255,255,0.1)] border-[rgba(255,255,255,0.2)] text-white' : 'bg-transparent border-transparent text-zinc-400 hover:text-white hover:bg-[rgba(255,255,255,0.05)]'}`}
                >
                  {f}
                </button>
              ))}
            </div>
            
            <motion.div 
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="flex flex-col gap-2 overflow-y-auto max-h-[500px] pr-2"
            >
              {filteredMemories.map(memory => (
                <motion.div 
                  key={memory.id}
                  variants={itemVariants}
                  onClick={() => setSelectedId(memory.id)}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${selectedId === memory.id ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] shadow-lg' : 'bg-[rgba(255,255,255,0.02)] border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.04)] hover:border-[rgba(255,255,255,0.06)]'}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <TypeIcon type={memory.type} />
                      <h4 className="text-sm font-medium text-white">{memory.title}</h4>
                    </div>
                    <span className="text-[10px] text-zinc-500">{memory.timestamp}</span>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] line-clamp-1 mb-3">{memory.content}</p>
                  <div className="flex items-center justify-between">
                    <div className="flex gap-1.5">
                      {memory.tags?.map((tag: any) => (
                        <span key={tag} className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[rgba(0,0,0,0.5)] border border-[rgba(255,255,255,0.05)] text-zinc-400">{tag}</span>
                      ))}
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1 bg-zinc-800 rounded-full overflow-hidden">
                        <div className="h-full bg-[var(--accent-cyan)] opacity-70" style={{ width: `${memory.relevance}%` }} />
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
        
        {/* Right Column - Inspector */}
        <div className="w-full md:w-[40%]">
          <div className="sticky top-6 bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.05)] rounded-xl p-6 h-fit min-h-[400px]">
            <div className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-6 flex justify-between items-center">
              <span>Memory Inspector</span>
              <span className="text-zinc-500 font-mono">ID: {selectedMemory ? selectedMemory.id.toUpperCase() : 'NONE'}</span>
            </div>
            
            {selectedMemory ? (
              <>
            
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[rgba(255,255,255,0.05)] flex items-center justify-center">
                <TypeIcon type={selectedMemory.type} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white leading-tight">{selectedMemory.title}</h3>
                <span className="text-xs text-[var(--text-muted)] capitalize tracking-widest">{selectedMemory.type} Memory</span>
              </div>
            </div>
            
            <div className="bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-lg p-4 mb-6">
              <p className="text-sm text-zinc-300 leading-relaxed">{selectedMemory.content}</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.03)] rounded-lg p-3">
                <div className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-1 flex items-center gap-1"><Calendar size={10} /> Discovered</div>
                <div className="text-sm text-white">{selectedMemory.timestamp}</div>
              </div>
              <div className="bg-[rgba(0,0,0,0.2)] border border-[rgba(255,255,255,0.03)] rounded-lg p-3">
                <div className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-1 flex items-center gap-1"><Activity size={10} /> Relevance</div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white font-mono">{selectedMemory.relevance}%</span>
                  <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                    <div className="h-full bg-[var(--accent-cyan)]" style={{ width: `${selectedMemory.relevance}%` }} />
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mb-6">
              <div className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-2 flex items-center gap-1"><Tag size={12} /> Tags</div>
              <div className="flex flex-wrap gap-2">
                {selectedMemory.tags?.map((tag: any) => (
                  <span key={tag} className="text-xs px-2 py-1 rounded bg-[rgba(255,255,255,0.05)] text-zinc-300 border border-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.1)] cursor-pointer transition-colors">{tag}</span>
                ))}
                <button 
                  onClick={() => toast({ title: 'Not connected', description: 'Editing tags is not yet supported.' })}
                  className="text-xs px-2 py-1 rounded border border-dashed border-[rgba(255,255,255,0.2)] text-zinc-500 hover:text-zinc-300 transition-colors">+</button>
              </div>
            </div>
            
            {selectedMemory.connections.length > 0 && (
              <div className="mb-8">
                <div className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-2">Connected Memories</div>
                <div className="flex flex-col gap-1">
                  {selectedMemory.connections?.map((connId: any) => {
                    const conn = memories.find(m => m.id === connId);
                    if (!conn) return null;
                    return (
                      <div key={connId} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-[rgba(255,255,255,0.05)] cursor-pointer group transition-colors" onClick={() => setSelectedId(connId)}>
                        <div className="flex items-center gap-2">
                          <ChevronRight size={14} className="text-zinc-600 group-hover:text-white transition-colors" />
                          <span className="text-xs text-zinc-400 group-hover:text-zinc-200 truncate max-w-[200px]">{conn.title}</span>
                        </div>
                        <button 
                          onClick={(e) => { e.stopPropagation(); toast({ title: 'Not connected', description: 'Cannot delete memory without backend API.' }); }}
                          className="p-1 opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all">
                          <Trash2 size={12} />
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
            
            <div className="p-4 border-t border-[rgba(255,255,255,0.05)]">
              <div className="flex gap-3">
                <button 
                  onClick={() => toast({ title: 'Not connected', description: 'Cannot sync changes without backend API.' })}
                  className="flex-1 py-2 bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-white text-xs font-medium rounded transition-colors flex items-center justify-center gap-2">
                  <Edit3 size={14} /> Sync
                </button>
                <button 
                  onClick={() => toast({ title: 'Not connected', description: 'Cannot revert without backend API.' })}
                  className="flex-1 py-2 bg-[rgba(239,68,68,0.1)] hover:bg-[rgba(239,68,68,0.2)] text-red-400 text-xs font-medium rounded border border-[rgba(239,68,68,0.2)] transition-colors flex items-center justify-center gap-2">
                  <Trash2 size={14} /> Revert
                </button>
              </div>
            </div>
            </>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
                <Brain size={48} className="mb-4 opacity-20" />
                <p className="text-sm">Select a memory node to inspect</p>
              </div>
            )}
            
          </div>
        </div>
      </div>
    </PageShell>
  );
}