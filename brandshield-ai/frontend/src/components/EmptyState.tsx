import React from 'react';
import { Clock, ShieldAlert, Sparkles } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  features: string[];
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  features,
}) => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center backdrop-blur-sm">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
        <Clock className="h-7 w-7" />
      </div>
      <div className="inline-flex items-center gap-2 rounded-full bg-indigo-950/80 px-3 py-1 text-xs font-medium text-indigo-300 border border-indigo-800/60 mb-3">
        <Sparkles className="h-3 w-3" />
        Upcoming Feature
      </div>
      <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
      <p className="mx-auto max-w-lg text-sm text-slate-400 mb-6">{description}</p>

      <div className="mx-auto max-w-md rounded-lg border border-slate-800/80 bg-slate-950/50 p-4 text-left">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
          <ShieldAlert className="h-3.5 w-3.5 text-indigo-400" />
          Planned Architecture Scope
        </div>
        <ul className="space-y-1.5 text-xs text-slate-300">
          {features.map((feature, idx) => (
            <li key={idx} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
              {feature}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 text-xs text-slate-500">
        This section is scheduled for subsequent enterprise release.
      </div>
    </div>
  );
};
