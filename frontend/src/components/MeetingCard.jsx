import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge } from './StatusBadge';
import { api } from '../services/api';

export function MeetingCard({ meeting, onDelete }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const primaryFile = meeting.files && meeting.files.length > 0 ? meeting.files[0] : null;
  const createdDate = new Date(meeting.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.deleteMeeting(meeting.id);
      if (onDelete) onDelete();
    } catch (err) {
      alert(err.message || 'Failed to delete meeting.');
      setDeleting(false);
      setShowConfirm(false);
    }
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all hover:shadow-xl hover:shadow-indigo-500/5 group flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between mb-3 gap-2">
          <h3 className="font-semibold text-slate-100 group-hover:text-indigo-400 transition-colors line-clamp-1 flex-1">
            {meeting.title}
          </h3>
          <StatusBadge status={meeting.status} />
        </div>

        <div className="space-y-2 text-xs text-slate-400 mb-4">
          {primaryFile && (
            <div className="flex items-center justify-between">
              <span className="truncate max-w-[180px]" title={primaryFile.filename}>
                📄 {primaryFile.filename}
              </span>
              <span className="uppercase text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                {primaryFile.file_extension}
              </span>
            </div>
          )}

          {/* Counts metadata */}
          <div className="flex items-center space-x-3 text-[11px] text-slate-400 pt-1 border-t border-slate-800/60">
            <span>💡 Decisions: <b className="text-slate-200">{meeting.decisions_count || 0}</b></span>
            <span>⚡ Actions: <b className="text-slate-200">{meeting.action_items_count || 0}</b></span>
            <span>❓ Questions: <b className="text-slate-200">{meeting.unresolved_questions_count || 0}</b></span>
          </div>

          <div className="flex items-center justify-between text-slate-500 pt-1 text-[11px]">
            <span>Uploaded {createdDate}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2 pt-2">
        <Link
          to={`/meetings/${meeting.id}`}
          className="flex-1 text-center py-2 px-3 rounded-lg text-xs font-medium bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white border border-slate-700 hover:border-indigo-500 transition-all"
        >
          View Details &rarr;
        </Link>
        <button
          onClick={() => setShowConfirm(true)}
          className="p-2 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
          title="Delete Meeting"
        >
          🗑️
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h4 className="text-base font-bold text-slate-100">Delete Meeting?</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Are you sure you want to delete <b className="text-slate-200">"{meeting.title}"</b>? This action cannot be undone and will delete all files and intelligence data.
            </p>
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-3 py-1.5 text-xs text-white bg-rose-600 hover:bg-rose-500 rounded-lg font-semibold disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete Meeting'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
