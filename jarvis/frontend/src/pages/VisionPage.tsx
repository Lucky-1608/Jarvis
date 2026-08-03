import { useState } from 'react';
import { motion } from 'framer-motion';
import { PageShell } from '../components/ui/PageShell';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from '../hooks/use-toast';
import { Eye, Camera, Maximize, Target, Aperture, RefreshCw, ScanLine, BrainCircuit, BoxSelect, Cpu, Loader2, Scan, WifiOff } from 'lucide-react';
import { api } from '../lib/api';

export function VisionPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  const performVisionAction = async (endpoint: string, payload: any = {}) => {
    setLoading(true);
    const res = await api.post<any>(`/api/vision/${endpoint}`, Object.keys(payload).length > 0 ? payload : undefined);

    if (res.ok) {
      setResult(res.data);
      setBackendConnected(true);
    } else {
      setResult({ summary: 'Backend offline — cannot connect to vision system.', elements: [] });
      setBackendConnected(false);
    }
    setLoading(false);
  };

  return (
    <PageShell>
      <PageHeader 
        title="Vision Systems" 
        description="Real-time environmental perception and analysis"
        actions={
          <div className="flex gap-2">
            <button 
              onClick={() => performVisionAction('screenshot')}
              className="p-2 bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-white rounded-md hover:bg-[rgba(255,255,255,0.1)] transition-colors">
              <RefreshCw size={16} />
            </button>
            <button 
              onClick={() => performVisionAction('screenshot')}
              className="px-4 py-2 bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.3)] text-[var(--accent-cyan)] rounded-md text-sm font-medium hover:bg-[rgba(0,212,255,0.2)] transition-colors flex items-center gap-2">
              <Camera size={16} /> Start Feed
            </button>
          </div>
        }
      />
      
      <div className="flex-1 flex flex-col p-6 gap-6 max-w-7xl mx-auto w-full">
        
        {/* Top Half - Camera Feeds */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 h-[400px]">
          {/* Feed 1 (Active) */}
          <div className="relative bg-black rounded-xl border border-[rgba(255,255,255,0.1)] overflow-hidden flex items-center justify-center">
            {loading ? (
              <div className="text-[var(--accent-cyan)] flex flex-col items-center">
                <Loader2 size={32} className="mb-2 animate-spin" />
                <span className="text-xs font-mono">CAPTURING SCREEN...</span>
              </div>
            ) : (
              <div className="text-zinc-500 flex flex-col items-center">
                <Camera size={32} className="mb-2 opacity-20" />
                <span className="text-xs font-mono">SCREEN CAPTURE IDLE</span>
              </div>
            )}
          </div>
          
          {/* Feed 2 (Analyzing) */}
          <div className="relative bg-black rounded-xl border border-[rgba(255,255,255,0.1)] overflow-hidden flex items-center justify-center p-4">
             {result && result.elements && result.elements.length > 0 ? (
                <div className="w-full h-full text-xs font-mono text-zinc-300 overflow-y-auto">
                   <h4 className="text-[var(--accent-cyan)] mb-2">Detected Elements:</h4>
                   <ul className="list-disc pl-4">
                     {result.elements.map((el: any, i: number) => (
                       <li key={i} className="mb-1">
                         <span className="text-[var(--accent-violet)]">[{el.type}]</span> {el.content} 
                         <span className="text-zinc-500 ml-2">({el.location})</span>
                       </li>
                     ))}
                   </ul>
                </div>
             ) : (
                <div className="text-zinc-500 flex flex-col items-center">
                  <ScanLine size={32} className="mb-2 opacity-20" />
                  <span className="text-xs font-mono">ANALYSIS READY</span>
                </div>
             )}
          </div>
        </div>
        
        {/* Bottom Half - Analysis Panel */}
        <div className="flex-1 grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-4">
          
          {/* Detected Objects */}
          <div className="bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex flex-col">
            <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-4 flex items-center gap-2"><BoxSelect size={14} /> Detected Entities</h3>
            <div className="flex-1 overflow-y-auto pr-2 flex flex-col items-center justify-center text-zinc-500">
              {result && result.elements ? (
                <span className="text-xs text-[var(--accent-cyan)]">{result.elements.length} entities detected</span>
              ) : (
                <span className="text-xs">No entities detected</span>
              )}
            </div>
          </div>
          
          {/* Scene Understanding */}
          <div className="bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex flex-col">
            <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-4 flex items-center gap-2"><BrainCircuit size={14} /> Scene Understanding</h3>
            <div className="flex-1 bg-[rgba(0,0,0,0.4)] border border-[rgba(255,255,255,0.02)] rounded p-3 font-mono text-xs text-[var(--accent-cyan)] leading-relaxed shadow-[inset_0_0_20px_rgba(0,0,0,0.8)] overflow-y-auto">
              {loading ? (
                <span className="animate-pulse">Analyzing...</span>
              ) : result ? (
                <span>&gt; {result.summary}</span>
              ) : (
                <>
                  <span className="text-zinc-500">&gt; WAITING FOR FEED...</span><br/>
                  <span className="animate-pulse">_</span>
                </>
              )}
            </div>
          </div>
          
          {/* Actions & Metrics */}
          <div className="bg-[rgba(6,12,24,0.6)] border border-[rgba(255,255,255,0.05)] rounded-xl p-4 flex flex-col justify-between">
            <div>
              <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] font-semibold mb-4 flex items-center gap-2"><Cpu size={14} /> Vision Actions</h3>
              <div className="grid grid-cols-2 gap-2">
                <button 
                  onClick={() => performVisionAction('screenshot')}
                  disabled={loading}
                  className="p-3 bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)] rounded-lg text-xs font-medium text-white transition-colors border border-[rgba(255,255,255,0.05)] flex flex-col items-center gap-2 disabled:opacity-50"
                >
                  <Camera size={18} className="text-[var(--accent-cyan)]" />
                  Analyze Screen
                </button>
                <button 
                  onClick={() => performVisionAction('errors')}
                  disabled={loading}
                  className="p-3 bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)] rounded-lg text-xs font-medium text-white transition-colors border border-[rgba(255,255,255,0.05)] flex flex-col items-center gap-2 disabled:opacity-50"
                >
                  <ScanLine size={18} className="text-[var(--accent-violet)]" />
                  Check Errors
                </button>
                <button 
                  onClick={() => toast({ title: 'Not connected', description: 'Cannot track object without backend API.' })}
                  className="p-3 bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)] rounded-lg text-xs font-medium text-white transition-colors border border-[rgba(255,255,255,0.05)] flex flex-col items-center gap-2 opacity-50 cursor-not-allowed">
                  <Scan size={18} className="text-zinc-500" />
                  Track Object
                </button>
                <button 
                  onClick={() => toast({ title: 'Not connected', description: 'Cannot compare scenes without backend API.' })}
                  className="p-3 bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)] rounded-lg text-xs font-medium text-white transition-colors border border-[rgba(255,255,255,0.05)] flex flex-col items-center gap-2 opacity-50 cursor-not-allowed">
                  <BrainCircuit size={18} className="text-zinc-500" />
                  Compare Scenes
                </button>
              </div>
            </div>
            
            <div className="mt-6 pt-4 border-t border-[rgba(255,255,255,0.05)]">
               <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono mb-2">
                 <span>MODELS ACTIVE: LLaVA/Llama Vision</span>
                 <span>READY</span>
               </div>
               <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                 <span>CONFIDENCE</span>
                 <span className="text-green-400">{result ? Math.round(result.confidence * 100) : 0}%</span>
               </div>
            </div>
          </div>
          
        </div>
      </div>
    </PageShell>
  );
}