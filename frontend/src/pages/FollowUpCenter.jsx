import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Loading } from '../components/Loading';

export function FollowUpCenter() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // all, overdue, due_soon, questions, suggestions, calendar, email

  // Modal States
  const [scheduleModal, setScheduleModal] = useState(null); // { item, title, start_time, end_time, description, evidence_quote }
  const [emailModal, setEmailModal] = useState(null); // { item, recipient, subject, body }
  const [actionSuccess, setActionSuccess] = useState(null);

  const loadFollowupData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getFollowUpCenter();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load follow-up center');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFollowupData();
  }, []);

  const handleOpenScheduleModal = (item) => {
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 1);
    const startStr = defaultDate.toISOString().slice(0, 16);
    const endDate = new Date(defaultDate.getTime() + 30 * 60000);
    const endStr = endDate.toISOString().slice(0, 16);

    setScheduleModal({
      action_item_id: item.id || null,
      meeting_id: item.meeting_id || null,
      title: item.task_description || item.question || 'Follow-up Meeting',
      start_time: startStr,
      end_time: endStr,
      description: `Follow-up for task: ${item.task_description || item.question || ''}`,
      evidence_quote: item.context_quote || item.evidence || '',
      provider: 'google'
    });
  };

  const handleConfirmSchedule = async () => {
    if (!scheduleModal) return;
    try {
      setActionSuccess(null);
      await api.createCalendarEvent({
        meeting_id: scheduleModal.meeting_id,
        action_item_id: scheduleModal.action_item_id,
        title: scheduleModal.title,
        description: scheduleModal.description,
        start_time: scheduleModal.start_time,
        end_time: scheduleModal.end_time,
        provider: scheduleModal.provider,
        evidence_quote: scheduleModal.evidence_quote
      });
      setScheduleModal(null);
      setActionSuccess('Calendar event scheduled successfully!');
      loadFollowupData();
    } catch (err) {
      alert(err.message || 'Failed to schedule calendar event');
    }
  };

  const handleOpenEmailModal = (item) => {
    setEmailModal({
      action_item_id: item.id || null,
      meeting_id: item.meeting_id || null,
      recipient: item.responsible_person ? `${item.responsible_person.toLowerCase()}@example.com` : 'Not specified',
      subject: `Follow-up: ${item.task_description || item.question || 'Meeting Follow-up'}`,
      body: `Hi,\n\nFollowing up on the action item from our meeting:\n\nTask: ${item.task_description || item.question}\nDue: ${item.deadline || 'Not specified'}\n\nEvidence quote: "${item.context_quote || ''}"\n\nThanks!`
    });
  };

  const handleConfirmSaveDraft = async () => {
    if (!emailModal) return;
    try {
      setActionSuccess(null);
      await api.createEmailDraft({
        meeting_id: emailModal.meeting_id,
        action_item_id: emailModal.action_item_id,
        recipient: emailModal.recipient,
        subject: emailModal.subject,
        body: emailModal.body
      });
      setEmailModal(null);
      setActionSuccess('Email draft created successfully!');
      loadFollowupData();
    } catch (err) {
      alert(err.message || 'Failed to create email draft');
    }
  };

  const handleSendEmail = async (draftId) => {
    try {
      setActionSuccess(null);
      await api.sendEmail(draftId);
      setActionSuccess('Email sent successfully!');
      loadFollowupData();
    } catch (err) {
      alert(err.message || 'Failed to send email');
    }
  };

  const handleDeleteEvent = async (eventId) => {
    if (!window.confirm('Are you sure you want to cancel this calendar event?')) return;
    try {
      setActionSuccess(null);
      await api.deleteCalendarEvent(eventId);
      setActionSuccess('Calendar event cancelled.');
      loadFollowupData();
    } catch (err) {
      alert(err.message || 'Failed to cancel event');
    }
  };

  if (loading) return <Loading message="Loading Follow-Up Center..." />;

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-6 rounded-xl">
        <h3 className="font-bold text-lg mb-2">Error Loading Follow-Up Center</h3>
        <p className="text-sm">{error}</p>
        <button onClick={loadFollowupData} className="mt-4 px-4 py-2 bg-slate-800 text-white text-xs font-medium rounded-lg">Retry</button>
      </div>
    );
  }

  const overdue = data?.overdue_actions || [];
  const dueSoon = data?.due_soon_actions || [];
  const questions = data?.open_questions || [];
  const suggestions = data?.suggestions || [];
  const calendarEvents = data?.calendar_events || [];
  const emailDrafts = data?.email_drafts || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-indigo-500" />
            <span>Follow-Up Center</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Turn meeting decisions, deadlines, and questions into actionable calendar events and follow-ups.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-xs text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            Timezone: <strong className="text-indigo-400">{data?.settings?.timezone || 'Asia/Kolkata'}</strong>
          </span>
        </div>
      </div>

      {actionSuccess && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-xl text-sm flex items-center justify-between">
          <span>{actionSuccess}</span>
          <button onClick={() => setActionSuccess(null)} className="text-xs underline">Dismiss</button>
        </div>
      )}

      {/* Tabs / Filters */}
      <div className="flex space-x-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {[
          { id: 'all', label: 'All Items' },
          { id: 'overdue', label: `Overdue (${overdue.length})` },
          { id: 'due_soon', label: `Due Soon (${dueSoon.length})` },
          { id: 'questions', label: `Open Questions (${questions.length})` },
          { id: 'suggestions', label: `AI Suggestions (${suggestions.length})` },
          { id: 'calendar', label: `Scheduled Calendar (${calendarEvents.length})` },
          { id: 'email', label: `Email Drafts (${emailDrafts.length})` }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Section: Overdue Action Items */}
      {(activeTab === 'all' || activeTab === 'overdue') && overdue.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-md font-bold text-rose-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
            <span>Overdue Action Items ({overdue.length})</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {overdue.map((act) => (
              <div key={act.id} className="bg-slate-900 border border-rose-500/30 rounded-xl p-5 shadow-lg space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="text-sm font-semibold text-white">{act.task_description}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">Overdue</span>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <p>Responsible: <strong className="text-slate-200">{act.responsible_person || 'Not specified'}</strong></p>
                  <p>Deadline: <strong className="text-rose-400">{act.deadline}</strong></p>
                  <p className="italic text-slate-500 mt-1">"{act.context_quote}"</p>
                </div>
                <div className="flex items-center space-x-2 pt-2 border-t border-slate-800">
                  <button onClick={() => handleOpenScheduleModal(act)} className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-medium">
                    Schedule Follow-up
                  </button>
                  <button onClick={() => handleOpenEmailModal(act)} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium">
                    Create Email Draft
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section: Due Soon Action Items */}
      {(activeTab === 'all' || activeTab === 'due_soon') && dueSoon.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-md font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span>Upcoming / Due Soon ({dueSoon.length})</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {dueSoon.map((act) => (
              <div key={act.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="text-sm font-semibold text-white">{act.task_description}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Due Soon</span>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <p>Responsible: <strong className="text-slate-200">{act.responsible_person || 'Not specified'}</strong></p>
                  <p>Deadline: <strong className="text-amber-300">{act.deadline}</strong></p>
                  <p className="italic text-slate-500 mt-1">"{act.context_quote}"</p>
                </div>
                <div className="flex items-center space-x-2 pt-2 border-t border-slate-800">
                  <button onClick={() => handleOpenScheduleModal(act)} className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-medium">
                    Schedule Follow-up
                  </button>
                  <button onClick={() => handleOpenEmailModal(act)} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium">
                    Create Email Draft
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section: Open Questions */}
      {(activeTab === 'all' || activeTab === 'questions') && questions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-md font-bold text-indigo-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
            <span>Open Questions ({questions.length})</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {questions.map((q) => (
              <div key={q.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
                <h3 className="text-sm font-semibold text-white">{q.question}</h3>
                <p className="text-xs text-slate-500 italic">"{q.context_quote}"</p>
                <div className="pt-2 border-t border-slate-800">
                  <button onClick={() => handleOpenScheduleModal(q)} className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-medium">
                    Schedule Discussion
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section: AI Follow-up Suggestions */}
      {(activeTab === 'all' || activeTab === 'suggestions') && suggestions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-md font-bold text-violet-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-400" />
            <span>AI Follow-Up Suggestions ({suggestions.length})</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suggestions.map((s) => (
              <div key={s.id} className="bg-slate-900 border border-violet-500/20 rounded-xl p-5 shadow-lg space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 bg-violet-500/20 text-violet-300 border border-violet-500/30 rounded text-[10px] font-bold uppercase">{s.category}</span>
                  <span className="text-[10px] text-slate-500">AI Recommendation</span>
                </div>
                <p className="text-sm text-slate-200">{s.suggestion_text}</p>
                <div className="pt-2 border-t border-slate-800">
                  <button onClick={() => handleOpenScheduleModal(s)} className="px-3 py-1.5 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-lg text-xs font-medium">
                    Schedule Follow-up Meeting
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section: Scheduled Calendar Events */}
      {(activeTab === 'all' || activeTab === 'calendar') && calendarEvents.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-md font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span>Scheduled Calendar Events ({calendarEvents.length})</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {calendarEvents.map((evt) => (
              <div key={evt.id} className="bg-slate-900 border border-emerald-500/30 rounded-xl p-5 shadow-lg space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="text-sm font-semibold text-white">{evt.title}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">{evt.status}</span>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <p>Start: <strong className="text-slate-200">{new Date(evt.start_time).toLocaleString()}</strong></p>
                  <p>End: <strong className="text-slate-200">{new Date(evt.end_time).toLocaleString()}</strong></p>
                  {evt.evidence_quote && <p className="italic text-slate-500 mt-1">"{evt.evidence_quote}"</p>}
                </div>
                <div className="pt-2 border-t border-slate-800 flex justify-end">
                  <button onClick={() => handleDeleteEvent(evt.id)} className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 rounded-lg text-xs font-medium">
                    Cancel Event
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section: Email Drafts */}
      {(activeTab === 'all' || activeTab === 'email') && emailDrafts.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-md font-bold text-indigo-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
            <span>Email Follow-Up Drafts ({emailDrafts.length})</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {emailDrafts.map((draft) => (
              <div key={draft.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="text-sm font-semibold text-white">{draft.subject}</h3>
                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                    draft.status === 'SENT' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-300 border border-slate-700'
                  }`}>{draft.status}</span>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <p>To: <strong className="text-slate-200">{draft.recipient}</strong></p>
                  <p className="bg-slate-950 p-2 rounded text-slate-300 whitespace-pre-wrap mt-2">{draft.body}</p>
                </div>
                {draft.status === 'DRAFT' && (
                  <div className="pt-2 border-t border-slate-800 flex justify-end">
                    <button onClick={() => handleSendEmail(draft.id)} className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium">
                      Send Email
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Schedule Calendar Event Modal */}
      {scheduleModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Schedule Calendar Event Proposal</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Event Title</label>
                <input
                  type="text"
                  value={scheduleModal.title}
                  onChange={(e) => setScheduleModal({ ...scheduleModal, title: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Start Date & Time</label>
                  <input
                    type="datetime-local"
                    value={scheduleModal.start_time}
                    onChange={(e) => setScheduleModal({ ...scheduleModal, start_time: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">End Date & Time</label>
                  <input
                    type="datetime-local"
                    value={scheduleModal.end_time}
                    onChange={(e) => setScheduleModal({ ...scheduleModal, end_time: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Evidence Quote</label>
                <p className="bg-slate-950 p-2.5 rounded text-slate-300 italic">"{scheduleModal.evidence_quote}"</p>
              </div>
            </div>
            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
              <button onClick={() => setScheduleModal(null)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded text-xs">Cancel</button>
              <button onClick={handleConfirmSchedule} className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-bold">
                Create Event
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Email Draft Modal */}
      {emailModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Create Email Draft Proposal</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Recipient Email</label>
                <input
                  type="text"
                  value={emailModal.recipient}
                  onChange={(e) => setEmailModal({ ...emailModal, recipient: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Subject</label>
                <input
                  type="text"
                  value={emailModal.subject}
                  onChange={(e) => setEmailModal({ ...emailModal, subject: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Body</label>
                <textarea
                  rows="5"
                  value={emailModal.body}
                  onChange={(e) => setEmailModal({ ...emailModal, body: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
              <button onClick={() => setEmailModal(null)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded text-xs">Cancel</button>
              <button onClick={handleConfirmSaveDraft} className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-bold">
                Save Draft
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FollowUpCenter;
