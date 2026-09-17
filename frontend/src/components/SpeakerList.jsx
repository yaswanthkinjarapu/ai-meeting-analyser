import React, { useState } from 'react';
import { api } from '../services/api';

export function SpeakerList({ meetingId, speakers, onSpeakerUpdated }) {
  const [editingId, setEditingId] = useState(null);
  const [nameInput, setNameInput] = useState('');
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState(null);

  const handleStartEdit = (speaker) => {
    setEditingId(speaker.id);
    setNameInput(speaker.speaker_name || '');
    setError(null);
  };

  const handleSave = async (speakerId) => {
    setSavingId(speakerId);
    setError(null);
    try {
      await api.updateSpeakerName(meetingId, speakerId, nameInput);
      setEditingId(null);
      setSavingId(null);
      if (onSpeakerUpdated) {
        onSpeakerUpdated();
      }
    } catch (err) {
      setError(err.message || 'Failed to update speaker name.');
      setSavingId(null);
    }
  };

  if (!speakers || speakers.length === 0) {
    return (
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 text-center text-slate-500 text-sm">
        No detected speakers yet. Run speaker diarization or process transcript to identify speakers.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs rounded-lg p-2.5">
          ⚠️ {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {speakers.map((spk) => {
          const isEditing = editingId === spk.id;
          const isSaving = savingId === spk.id;

          return (
            <div
              key={spk.id}
              className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex items-center justify-between"
            >
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  {spk.speaker_label}
                </span>
                <span className="text-sm font-medium text-slate-100">
                  {spk.speaker_name ? (
                    <span className="text-emerald-400 font-semibold">{spk.speaker_name}</span>
                  ) : (
                    <span className="text-slate-500 italic">Not identified (Unmapped)</span>
                  )}
                </span>
              </div>

              <div>
                {isEditing ? (
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                      placeholder="Enter real name"
                      className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                    <button
                      onClick={() => handleSave(spk.id)}
                      disabled={isSaving}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-2.5 py-1 rounded font-medium transition-all"
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="text-slate-500 hover:text-slate-300 text-xs px-1.5"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => handleStartEdit(spk)}
                    className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700 transition-all"
                  >
                    {spk.speaker_name ? 'Edit Name' : '+ Map Name'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
