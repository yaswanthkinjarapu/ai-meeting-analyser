import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { MeetingCard } from '../components/MeetingCard';
import { Loading } from '../components/Loading';

export function Dashboard() {
  const [meetings, setMeetings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [meetingsData, statsData] = await Promise.all([
        searchQuery.trim() ? api.searchMeetings(searchQuery) : api.getMeetings(),
        api.getStats().catch(() => null)
      ]);
      setMeetings(meetingsData);
      setStats(statsData);
    } catch (err) {
      setError(err.message || 'Failed to load meeting data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const filteredMeetings = meetings.filter(m => {
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'COMPLETED') return ['TRANSCRIBED', 'DIARIZED', 'ANALYZED', 'COMPLETED'].includes(m.status);
    if (statusFilter === 'PROCESSING') return ['QUEUED', 'PROCESSING', 'TRANSCRIBING', 'DIARIZING', 'ANALYZING'].includes(m.status);
    if (statusFilter === 'FAILED') return m.status === 'FAILED';
    return true;
  });

  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 rounded-2xl border border-indigo-500/20 shadow-2xl">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Meeting Intelligence Dashboard
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Grounded AI extraction, evidence navigation, and task follow-up tracking
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center justify-center px-4 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          + Upload New Meeting
        </Link>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Total Meetings
          </span>
          <span className="text-2xl font-bold text-slate-100">{stats ? stats.total_meetings : meetings.length}</span>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <span className="text-xs font-semibold text-emerald-500/80 uppercase tracking-wider block mb-1">
            Decisions Reached
          </span>
          <span className="text-2xl font-bold text-emerald-400">{stats ? stats.total_decisions : 0}</span>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <span className="text-xs font-semibold text-amber-500/80 uppercase tracking-wider block mb-1">
            Open Action Items
          </span>
          <span className="text-2xl font-bold text-amber-400">{stats ? stats.open_action_items : 0}</span>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <span className="text-xs font-semibold text-indigo-400/80 uppercase tracking-wider block mb-1">
            Open Questions
          </span>
          <span className="text-2xl font-bold text-indigo-400">{stats ? stats.open_questions : 0}</span>
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800">
        <div className="w-full sm:w-80 relative">
          <input
            type="text"
            placeholder="Search title, transcript, decisions, actions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
          />
          <span className="absolute left-3 top-2.5 text-slate-500 text-sm">🔍</span>
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto overflow-x-auto">
          {['ALL', 'COMPLETED', 'PROCESSING', 'FAILED'].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === tab
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {tab}
            </button>
          ))}
          <button
            onClick={fetchData}
            className="text-xs text-indigo-400 hover:text-indigo-300 pl-2"
            title="Refresh Meetings"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Main Meetings Grid */}
      <div className="space-y-4">
        {loading && <Loading message="Loading meeting workspace..." />}

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-xl p-6 text-center space-y-3">
            <p className="text-sm font-medium">{error}</p>
            <button
              onClick={fetchData}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium"
            >
              Retry Connection
            </button>
          </div>
        )}

        {!loading && !error && filteredMeetings.length === 0 && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-slate-800 text-slate-400 mx-auto flex items-center justify-center text-2xl">
              📂
            </div>
            <h3 className="text-base font-semibold text-slate-300">No matching meetings found</h3>
            <p className="text-slate-500 text-sm max-w-sm mx-auto">
              {searchQuery ? `No results found for "${searchQuery}".` : 'Upload a meeting transcript or audio/video file to start.'}
            </p>
            <Link
              to="/upload"
              className="inline-block px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
            >
              Upload Meeting
            </Link>
          </div>
        )}

        {!loading && !error && filteredMeetings.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMeetings.map((m) => (
              <MeetingCard key={m.id} meeting={m} onDelete={fetchData} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
