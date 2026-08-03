import { Menu, Activity } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger } from './sheet';
import { LeftPanelContent } from './LeftPanel';
import { RightPanelContent } from './RightPanel';
import { useState } from 'react';

export function MobileHeader() {
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);

  return (
    <div className="lg:hidden flex items-center justify-between px-4 h-14 shrink-0 bg-[rgba(2,4,8,0.8)] backdrop-blur-md border-b border-[var(--border-subtle)] z-50 relative">
      
      {/* Left Menu (Navigation) */}
      <Sheet open={leftOpen} onOpenChange={setLeftOpen}>
        <SheetTrigger asChild>
          <button className="p-2 text-[var(--text-primary)] hover:text-[var(--accent-cyan)] transition-colors">
            <Menu size={20} />
          </button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[280px] p-0 border-r border-[var(--border-subtle)] bg-[var(--bg-panel)] overflow-hidden">
          <LeftPanelContent onNavigate={() => setLeftOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Center Logo */}
      <div className="flex flex-col items-center">
        <h2 className="text-[12px] font-bold tracking-[0.4em] text-center">J.A.R.V.I.S.</h2>
        <p className="text-[8px] tracking-widest text-[var(--accent-cyan)] text-center mt-0.5">OS</p>
      </div>

      {/* Right Menu (System) */}
      <Sheet open={rightOpen} onOpenChange={setRightOpen}>
        <SheetTrigger asChild>
          <button className="p-2 text-[var(--text-primary)] hover:text-[var(--accent-cyan)] transition-colors">
            <Activity size={20} />
          </button>
        </SheetTrigger>
        <SheetContent side="right" className="w-[300px] p-0 border-l border-[var(--border-subtle)] bg-[var(--bg-panel)] overflow-y-auto">
          <div className="p-5 pb-10">
            <RightPanelContent />
          </div>
        </SheetContent>
      </Sheet>
      
    </div>
  );
}
