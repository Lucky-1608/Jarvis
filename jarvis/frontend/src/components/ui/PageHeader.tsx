import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="w-full px-8 py-8 border-b border-[var(--border-subtle)] bg-[rgba(6,12,24,0.4)] backdrop-blur-xl sticky top-0 z-20 shrink-0">
      <div className="max-w-7xl mx-auto flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-wider text-[var(--text-primary)] mb-1 drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
            {title}
          </h1>
          <p className="text-sm text-[var(--text-muted)] tracking-wide">{description}</p>
        </div>
        {actions && (
          <div className="flex items-center gap-3">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}