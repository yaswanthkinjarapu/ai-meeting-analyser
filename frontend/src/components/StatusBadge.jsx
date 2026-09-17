import React from 'react';

export function StatusBadge({ status }) {
  const normalized = (status || 'UNKNOWN').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  if (normalized === 'COMPLETED' || normalized === 'TRANSCRIBED' || normalized === 'DIARIZED' || normalized === 'ANALYZED') {
    colorClasses = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  } else if (['QUEUED', 'PROCESSING', 'TRANSCRIBING', 'DIARIZING', 'ANALYZING', 'EXTRACTING_AUDIO'].includes(normalized)) {
    colorClasses = 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse';
  } else if (normalized === 'FAILED') {
    colorClasses = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
  } else if (normalized === 'UPLOADED') {
    colorClasses = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClasses}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5"></span>
      {normalized}
    </span>
  );
}
