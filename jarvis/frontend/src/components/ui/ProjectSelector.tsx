import { useJarvisStore } from '../../store/jarvisStore';
import { Folder } from 'lucide-react';

const mockProjects = [
  { id: 'proj_1', name: 'Jarvis OS' },
  { id: 'proj_2', name: 'LifeOS' },
  { id: 'proj_3', name: 'AI Recruiter' }
];

export function ProjectSelector() {
  const activeProjectId = useJarvisStore(s => s.activeProjectId);
  const setActiveProjectId = useJarvisStore(s => s.setActiveProjectId);

  return (
    <div className="flex items-center w-full px-3 py-2 mt-4 bg-[rgba(255,255,255,0.03)] rounded-md border border-[var(--border-subtle)] hover:bg-[rgba(255,255,255,0.06)] transition-colors">
      <Folder size={14} className="text-[var(--accent-cyan)] mr-2 shrink-0" />
      <select 
        value={activeProjectId || mockProjects[0].id}
        onChange={(e) => setActiveProjectId(e.target.value)}
        className="bg-transparent border-none outline-none text-xs font-medium text-[var(--text-primary)] w-full appearance-none cursor-pointer"
      >
        {mockProjects.map(proj => (
          <option key={proj.id} value={proj.id} className="bg-[#0B0F19] text-[var(--text-primary)]">
            {proj.name}
          </option>
        ))}
      </select>
    </div>
  );
}
