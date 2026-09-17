import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { TranscriptViewer } from '../components/TranscriptViewer';
import { SpeakerList } from '../components/SpeakerList';
import { Loading } from '../components/Loading';

export function MeetingDetails() {
  const { meetingId } = useParams();
  const [meeting, setMeeting] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [speakers, setSpeakers] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('transcript');
  const [highlightedQuote, setHighlightedQuote] = useState(null);

  // Edit states for action item modal
  const [editingAction, setEditingAction] = useState(null);
  const [editTask, setEditTask] = useState('');
  const [editPerson, setEditPerson] = useState('');
  const [editDeadline, setEditDeadline] = useState('');
  const [editStatus, setEditStatus] = useState('pending');
  const [editNotes, setEditNotes] = useState('');

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [mRes, tRes, sRes, aRes] = await Promise.allSettled([
        api.getMeeting(meetingId),
        api.getTranscript(meetingId),
        api.getSpeakers(meetingId),
        api.getAnalysis(meetingId),
      ]);

      if (mRes.status === 'fulfilled') {
        setMeeting(mRes.value);
      } else {
        throw new Error(mRes.reason.message || 'Meeting not found.');
      }

      if (tRes.status === 'fulfilled') {
        setTranscript(tRes.value);
      }

      if (sRes.status === 'fulfilled') {
        setSpeakers(sRes.value.speakers || []);
      }

      if (aRes.status === 'fulfilled') {
        setAnalysis(aRes.value);
      }

      setLoading(false);
    } catch (err) {
      setError(err.message || 'Failed to load meeting details.');
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [meetingId]);

  const handleRunDiarization = async () => {
    setActionLoading(true);
    try {
      await api.diarizeMeeting(meetingId);
      await loadAllData();
      setActionLoading(false);
    } catch (err) {
      alert(`Diarization error: ${err.message}`);
      setActionLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    setActionLoading(true);
    try {
      await api.analyzeMeeting(meetingId);
      await loadAllData();
      setActiveTab('intelligence');
      setActionLoading(false);
    } catch (err) {
      alert(`Analysis error: ${err.message}`);
      setActionLoading(false);
    }
  };

  const navigateToEvidence = (quote) => {
    if (!quote) return;
    setHighlightedQuote(quote);
    setActiveTab('transcript');
  };

  const handleUpdateDecisionStatus = async (decisionId, newStatus) => {
    try {
      await api.updateDecision(meetingId, decisionId, { review_status: newStatus });
      await loadAllData();
    } catch (err) {
      alert(`Failed to update decision: ${err.message}`);
    }
  };

  const handleUpdateQuestionStatus = async (questionId, newStatus) => {
    try {
      await api.updateQuestion(meetingId, questionId, { status: newStatus });
      await loadAllData();
    } catch (err) {
      alert(`Failed to update question: ${err.message}`);
    }
  };

  const openEditActionModal = (ai) => {
    setEditingAction(ai);
    setEditTask(ai.task_description);
    setEditPerson(ai.responsible_person || '');
    setEditDeadline(ai.deadline || '');
    setEditStatus(ai.status || 'pending');
    setEditNotes(ai.notes || '');
  };

  const handleSaveActionItem = async () => {
    if (!editingAction) return;
    try {
      await api.updateActionItem(meetingId, editingAction.id, {
        task_description: editTask,
        responsible_person: editPerson,
        deadline: editDeadline,
        status: editStatus,
        notes: editNotes
      });
      setEditingAction(null);
      await loadAllData();
    } catch (err) {
      alert(`Failed to save action item: ${err.message}`);
    }
  };

  const handleExport = (fmt) => {
    api.exportMeeting(meetingId, fmt).catch(err => alert(`Export error: ${err.message}`));
  };

  if (loading) {
    return <Loading message="Loading meeting workspace..." />;
  }

  if (error || !meeting) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center space-y-4 max-w-lg mx-auto">
        <div className="text-2xl">⚠️</div>
        <h2 className="text-lg font-semibold text-slate-200">Meeting Error</h2>
        <p className="text-slate-400 text-sm">{error || 'Meeting not found.'}</p>
        <Link
          to="/"
          className="inline-block px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
        >
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const primaryFile = meeting.files && meeting.files.length > 0 ? meeting.files[0] : null;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <div className="flex items-center space-x-3 mb-1">
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{meeting.title}</h1>
              <StatusBadge status={meeting.status} />
            </div>
            <p className="text-xs text-slate-400">Meeting ID: <span className="font-mono text-slate-500">{meeting.id}</span></p>
          </div>

          {/* Action & Export buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handleExport('markdown')}
              className="px-3 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all flex items-center space-x-1"
              title="Export Markdown Report"
            >
              <span>📥 Export .MD</span>
            </button>
            <button
              onClick={() => handleExport('json')}
              className="px-3 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all flex items-center space-x-1"
              title="Export JSON Data"
            >
              <span>📥 Export .JSON</span>
            </button>
            <button
              onClick={handleRunAnalysis}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-600/20 transition-all flex items-center space-x-1.5"
            >
              <span>🧠 Run AI Intelligence</span>
            </button>
            <button
              onClick={handleRunDiarization}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 transition-all flex items-center space-x-1.5"
            >
              <span>🎙️ Diarize Speakers</span>
            </button>
          </div>
        </div>

        {/* Metadata Details */}
        {primaryFile && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-slate-950/60 p-3.5 rounded-xl border border-slate-850">
            <div>
              <span className="text-slate-500 block">Filename</span>
              <span className="font-medium text-slate-300 truncate block">{primaryFile.filename}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Category</span>
              <span className="font-medium text-slate-300 uppercase">{primaryFile.file_type} ({primaryFile.file_extension})</span>
            </div>
            <div>
              <span className="text-slate-500 block">File Size</span>
              <span className="font-medium text-slate-300">{(primaryFile.file_size_bytes / 1024).toFixed(1)} KB</span>
            </div>
            <div>
              <span className="text-slate-500 block">Uploaded</span>
              <span className="font-medium text-slate-300">{new Date(meeting.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-800 flex space-x-4">
        {['transcript', 'speakers', 'intelligence'].map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              if (tab !== 'transcript') setHighlightedQuote(null);
            }}
            className={`pb-3 px-1 text-sm font-semibold border-b-2 transition-all capitalize ${
              activeTab === tab
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab === 'intelligence' ? 'AI Intelligence Workspace' : tab}
          </button>
        ))}
      </div>

      {/* Tab 1: Transcript */}
      {activeTab === 'transcript' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">
              Transcript Segments ({transcript?.total_segments || 0})
            </h2>
            {highlightedQuote && (
              <button
                onClick={() => setHighlightedQuote(null)}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
              >
                <span>Clear Highlight</span>
              </button>
            )}
          </div>
          <TranscriptViewer segments={transcript?.segments || []} highlightedQuote={highlightedQuote} />
        </div>
      )}

      {/* Tab 2: Speakers */}
      {activeTab === 'speakers' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-300">Speaker Identification & Name Mapping</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Map system speaker labels (e.g. Speaker 1) to user-provided names (e.g. Harinath).
            </p>
          </div>
          <SpeakerList
            meetingId={meetingId}
            speakers={speakers}
            onSpeakerUpdated={loadAllData}
          />
        </div>
      )}

      {/* Tab 3: AI Intelligence Workspace */}
      {activeTab === 'intelligence' && (
        <div className="space-y-6">
          {!analysis || (!analysis.summary && analysis.decisions?.length === 0 && analysis.action_items?.length === 0) ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-10 text-center space-y-3">
              <div className="text-3xl">🧠</div>
              <h3 className="text-base font-semibold text-slate-200">No AI Analysis Generated Yet</h3>
              <p className="text-slate-400 text-xs max-w-md mx-auto">
                Click "Run AI Intelligence" above to extract grounded decisions, action items, topics, timeline events, risks, and follow-up plans.
              </p>
              <button
                onClick={handleRunAnalysis}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-all shadow-lg shadow-indigo-600/20"
              >
                Run AI Intelligence Analysis Now
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Executive Summary & Header Badges */}
              {analysis.summary && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider">Executive Summary</h3>
                    <div className="flex items-center space-x-2 text-xs">
                      <span className="bg-slate-800 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700">
                        Tone: <strong className="capitalize text-indigo-300">{analysis.summary.conversational_tone || 'neutral'}</strong>
                      </span>
                      <span className="bg-slate-800 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700">
                        Outcome: <strong className="capitalize text-emerald-300">{analysis.summary.meeting_outcome || 'not_determined'}</strong>
                      </span>
                    </div>
                  </div>

                  <p className="text-sm text-slate-200 leading-relaxed font-sans">
                    {analysis.summary.executive_summary || analysis.summary.overview}
                  </p>

                  {analysis.summary.tone_explanation && (
                    <p className="text-xs text-slate-400 italic bg-slate-950/60 p-2.5 rounded-lg border border-slate-850">
                      💬 Conversational Tone Analysis: {analysis.summary.tone_explanation}
                    </p>
                  )}
                </div>
              )}

              {/* Key Topics & Interactive Timeline Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Key Discussion Topics */}
                {analysis.topics && analysis.topics.length > 0 && (
                  <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <h3 className="text-base font-bold text-indigo-400 flex items-center space-x-2 border-b border-slate-800 pb-3">
                      <span>📌 Key Discussion Topics ({analysis.topics.length})</span>
                    </h3>
                    <div className="space-y-3">
                      {analysis.topics.map((t) => (
                        <div key={t.id} className="bg-slate-950/80 border border-slate-850 rounded-xl p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold text-slate-100">{t.title}</h4>
                            <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                              {t.importance} priority
                            </span>
                          </div>
                          <p className="text-xs text-slate-300">{t.description}</p>
                          <div
                            onClick={() => navigateToEvidence(t.context_quote)}
                            className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800 cursor-pointer hover:border-indigo-500/50 transition-colors flex justify-between items-center group"
                          >
                            <span className="truncate">"{t.context_quote}"</span>
                            <span className="text-[10px] text-indigo-400 font-semibold group-hover:underline ml-2">Jump &rarr;</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Chronological Timeline */}
                {analysis.timeline_events && analysis.timeline_events.length > 0 && (
                  <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <h3 className="text-base font-bold text-indigo-400 flex items-center space-x-2 border-b border-slate-800 pb-3">
                      <span>⏱️ Chronological Timeline ({analysis.timeline_events.length})</span>
                    </h3>
                    <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                      {analysis.timeline_events.map((te) => (
                        <div
                          key={te.id}
                          onClick={() => navigateToEvidence(te.context_quote)}
                          className="bg-slate-950/80 border border-slate-850 rounded-xl p-3 cursor-pointer hover:border-indigo-500/50 transition-all flex items-start space-x-3 group"
                        >
                          <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-1 rounded">
                            {te.event_time_str}
                          </span>
                          <div className="flex-1 space-y-0.5">
                            <h5 className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300">{te.event_title}</h5>
                            <p className="text-[11px] text-slate-400 line-clamp-1">"{te.context_quote}"</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Risks & Task Dependencies Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Risks & Blockers */}
                {analysis.risks_blockers && analysis.risks_blockers.length > 0 && (
                  <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <h3 className="text-base font-bold text-rose-400 flex items-center space-x-2 border-b border-slate-800 pb-3">
                      <span>⚠️ Risks & Blockers ({analysis.risks_blockers.length})</span>
                    </h3>
                    <div className="space-y-3">
                      {analysis.risks_blockers.map((r) => (
                        <div key={r.id} className="bg-slate-950/80 border border-rose-950/50 rounded-xl p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold text-slate-100">{r.title}</h4>
                            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              {r.item_type}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300">{r.description}</p>
                          <div
                            onClick={() => navigateToEvidence(r.context_quote)}
                            className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800 cursor-pointer hover:border-rose-500/50 transition-colors flex justify-between items-center group"
                          >
                            <span className="truncate">"{r.context_quote}"</span>
                            <span className="text-[10px] text-rose-400 font-semibold group-hover:underline ml-2">Jump &rarr;</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Task Dependencies */}
                {analysis.dependencies && analysis.dependencies.length > 0 && (
                  <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <h3 className="text-base font-bold text-amber-400 flex items-center space-x-2 border-b border-slate-800 pb-3">
                      <span>🔗 Task Dependencies ({analysis.dependencies.length})</span>
                    </h3>
                    <div className="space-y-3">
                      {analysis.dependencies.map((dp) => (
                        <div key={dp.id} className="bg-slate-950/80 border border-slate-850 rounded-xl p-4 space-y-2">
                          <div className="text-xs text-slate-200 font-semibold">
                            <span className="text-indigo-400 font-mono">{dp.task_b}</span> depends on <span className="text-amber-400 font-mono">{dp.task_a}</span>
                          </div>
                          <p className="text-xs text-slate-400">{dp.dependency_description}</p>
                          <div
                            onClick={() => navigateToEvidence(dp.context_quote)}
                            className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800 cursor-pointer hover:border-amber-500/50 transition-colors flex justify-between items-center group"
                          >
                            <span className="truncate">"{dp.context_quote}"</span>
                            <span className="text-[10px] text-amber-400 font-semibold group-hover:underline ml-2">Jump &rarr;</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* AI Follow-up Suggestions Panel */}
              {analysis.follow_up_suggestions && analysis.follow_up_suggestions.length > 0 && (
                <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-3">
                  <h3 className="text-sm font-bold text-violet-400 uppercase tracking-wider">
                    💡 AI Follow-Up Suggestions (Separated AI Recommendations)
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {analysis.follow_up_suggestions.map((s) => (
                      <div key={s.id} className="bg-slate-950/80 border border-violet-950/50 p-3.5 rounded-xl space-y-1">
                        <span className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider block">
                          AI Suggestion ({s.category})
                        </span>
                        <p className="text-xs text-slate-300">{s.suggestion_text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Key Decisions */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-base font-bold text-emerald-400 flex items-center space-x-2">
                      <span>💡 Key Decisions ({analysis.decisions?.length || 0})</span>
                    </h3>
                  </div>

                  {analysis.decisions?.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No decisions extracted from transcript.</p>
                  ) : (
                    <div className="space-y-3">
                      {analysis.decisions.map((d) => (
                        <div key={d.id} className="bg-slate-950/80 border border-slate-850 rounded-xl p-4 space-y-3">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-semibold text-slate-100">{d.decision_text}</p>
                            <select
                              value={d.review_status || 'confirmed'}
                              onChange={(e) => handleUpdateDecisionStatus(d.id, e.target.value)}
                              className="bg-slate-900 border border-slate-700 text-xs rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-indigo-500"
                            >
                              <option value="confirmed">Confirmed</option>
                              <option value="needs_review">Needs Review</option>
                              <option value="rejected">Rejected</option>
                            </select>
                          </div>

                          <div
                            onClick={() => navigateToEvidence(d.context_quote)}
                            className="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800 cursor-pointer hover:border-indigo-500/50 transition-colors group"
                            title="Click to jump to transcript evidence"
                          >
                            <div className="flex items-center justify-between text-indigo-400 font-semibold mb-0.5">
                              <span>Verbatim Evidence:</span>
                              <span className="text-[10px] group-hover:underline">Jump to Transcript &rarr;</span>
                            </div>
                            "{d.context_quote}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Action Items */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-base font-bold text-indigo-400 flex items-center space-x-2">
                      <span>⚡ Action Items & Tasks ({analysis.action_items?.length || 0})</span>
                    </h3>
                  </div>

                  {analysis.action_items?.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No action items extracted.</p>
                  ) : (
                    <div className="space-y-3">
                      {analysis.action_items.map((ai) => (
                        <div key={ai.id} className="bg-slate-950/80 border border-slate-850 rounded-xl p-4 space-y-3">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-semibold text-slate-100 flex-1">{ai.task_description}</p>
                            <button
                              onClick={() => openEditActionModal(ai)}
                              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium px-2 py-0.5 rounded bg-slate-900 border border-slate-800"
                            >
                              Edit ✏️
                            </button>
                          </div>

                          <div className="flex flex-wrap gap-2 text-[11px]">
                            <span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-md">
                              👤 Responsible: <strong>{ai.responsible_person || 'Not specified'}</strong>
                            </span>
                            <span className="bg-amber-500/10 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-md">
                              ⏰ Deadline: <strong>{ai.deadline || 'Not specified'}</strong>
                            </span>
                            <span className="bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded-md uppercase font-mono">
                              {ai.status}
                            </span>
                          </div>

                          {ai.notes && (
                            <p className="text-xs text-slate-400 italic bg-slate-900/40 p-2 rounded border border-slate-800/60">
                              📝 Notes: {ai.notes}
                            </p>
                          )}

                          <div
                            onClick={() => navigateToEvidence(ai.context_quote)}
                            className="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800 cursor-pointer hover:border-indigo-500/50 transition-colors group"
                            title="Click to jump to transcript evidence"
                          >
                            <div className="flex items-center justify-between text-indigo-400 font-semibold mb-0.5">
                              <span>Verbatim Evidence:</span>
                              <span className="text-[10px] group-hover:underline">Jump to Transcript &rarr;</span>
                            </div>
                            "{ai.context_quote}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Unresolved Questions */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4 md:col-span-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-base font-bold text-amber-400 flex items-center space-x-2">
                      <span>❓ Unresolved Questions ({analysis.unresolved_questions?.length || 0})</span>
                    </h3>
                  </div>

                  {analysis.unresolved_questions?.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No unresolved questions remaining.</p>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {analysis.unresolved_questions.map((q) => (
                        <div key={q.id} className="bg-slate-950/80 border border-slate-850 rounded-xl p-4 space-y-3">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-semibold text-slate-100 flex-1">{q.question}</p>
                            <select
                              value={q.status || 'open'}
                              onChange={(e) => handleUpdateQuestionStatus(q.id, e.target.value)}
                              className="bg-slate-900 border border-slate-700 text-xs rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-indigo-500"
                            >
                              <option value="open">Open</option>
                              <option value="resolved">Resolved</option>
                              <option value="not_applicable">Not Applicable</option>
                            </select>
                          </div>

                          <div
                            onClick={() => navigateToEvidence(q.context_quote)}
                            className="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800 cursor-pointer hover:border-indigo-500/50 transition-colors group"
                            title="Click to jump to transcript evidence"
                          >
                            <div className="flex items-center justify-between text-amber-400 font-semibold mb-0.5">
                              <span>Context Quote:</span>
                              <span className="text-[10px] group-hover:underline">Jump to Transcript &rarr;</span>
                            </div>
                            "{q.context_quote}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action Item Edit Modal */}
      {editingAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-100">Edit Action Item</h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Task Description</label>
                <input
                  type="text"
                  value={editTask}
                  onChange={(e) => setEditTask(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Responsible Person</label>
                <input
                  type="text"
                  value={editPerson}
                  onChange={(e) => setEditPerson(e.target.value)}
                  placeholder="e.g. Harinath or Not specified"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Deadline</label>
                <input
                  type="text"
                  value={editDeadline}
                  onChange={(e) => setEditDeadline(e.target.value)}
                  placeholder="e.g. by Friday or Not specified"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="pending">Pending</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Notes</label>
                <textarea
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Additional execution details..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 h-20"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setEditingAction(null)}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveActionItem}
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
