import React from 'react';

function formatTime(seconds) {
  if (seconds === null || seconds === undefined) return null;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function TranscriptViewer({ segments, highlightedQuote }) {
  if (!segments || segments.length === 0) {
    return (
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
        No transcript segments available for this meeting yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {segments.map((seg, idx) => {
        const speakerDisplayName = seg.speaker_name
          ? `${seg.speaker_name} (${seg.speaker_label || 'Speaker'})`
          : (seg.speaker_label || 'Unknown Speaker');

        const startTimeStr = formatTime(seg.start_time);
        const endTimeStr = formatTime(seg.end_time);
        const timeDisplay = (startTimeStr && endTimeStr)
          ? `${startTimeStr} – ${endTimeStr}`
          : (startTimeStr ? startTimeStr : null);

        const isHighlighted = highlightedQuote && seg.text.toLowerCase().includes(highlightedQuote.toLowerCase());

        return (
          <div
            key={seg.id || idx}
            id={`segment-${seg.id}`}
            className={`border rounded-xl p-4 transition-all ${
              isHighlighted
                ? 'bg-indigo-950/60 border-indigo-500/80 shadow-lg shadow-indigo-500/10'
                : 'bg-slate-900/70 border-slate-800/80 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className={`w-2 h-2 rounded-full ${isHighlighted ? 'bg-indigo-400 animate-ping' : 'bg-indigo-500'}`}></span>
                <span className="text-xs font-semibold text-indigo-300">
                  {speakerDisplayName}
                </span>
              </div>
              {timeDisplay && (
                <span className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-850">
                  ⏱️ {timeDisplay}
                </span>
              )}
            </div>
            <p className={`text-sm leading-relaxed pl-4 border-l-2 ${isHighlighted ? 'text-white border-indigo-500 font-medium' : 'text-slate-200 border-slate-800'}`}>
              {seg.text}
            </p>
          </div>
        );
      })}
    </div>
  );
}
