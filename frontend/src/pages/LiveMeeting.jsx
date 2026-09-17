import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export function LiveMeeting() {
  const navigate = useNavigate();
  const [title, setTitle] = useState('Project Planning Meeting');
  const [session, setSession] = useState(null);
  const [sessionStatus, setSessionStatus] = useState('IDLE'); // IDLE, STARTING, RECORDING, PAUSED, STOPPING, COMPLETED, FAILED
  const [connectionStatus, setConnectionStatus] = useState('Disconnected'); // Disconnected, Connecting, Connected, Reconnecting
  const [timerSeconds, setTimerSeconds] = useState(0);

  const [transcript, setTranscript] = useState([]);
  const [partialText, setPartialText] = useState('');
  const [liveIntelligence, setLiveIntelligence] = useState({
    decisions: [],
    action_items: [],
    unresolved_questions: [],
    risks_blockers: [],
    topics: [],
    timeline_events: []
  });

  const [autoScroll, setAutoScroll] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const [isStarting, setIsStarting] = useState(false);

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const timerRef = useRef(null);
  const transcriptEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Auto scroll effect
  useEffect(() => {
    if (autoScroll && transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript, partialText, autoScroll]);

  // Timer effect
  useEffect(() => {
    if (sessionStatus === 'RECORDING') {
      timerRef.current = setInterval(() => {
        setTimerSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [sessionStatus]);

  const formatTimer = (secs) => {
    const hrs = Math.floor(secs / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (hrs > 0) {
      return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const startSession = async () => {
    try {
      setErrorMsg(null);
      setIsStarting(true);
      const res = await api.startLiveMeeting(title);
      setSession(res);
      setSessionStatus('RECORDING');
      setTimerSeconds(0);
      connectWebSocket(res.session_id);
      startMicrophoneCapture(res.session_id);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to start live session.');
    } finally {
      setIsStarting(false);
    }
  };

  const connectWebSocket = (sessionId) => {
    setConnectionStatus('Connecting');
    const token = localStorage.getItem('meeting_ai_token');
    const wsBase = import.meta.env.VITE_WS_BASE_URL || 
      (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + 
      (window.location.port === '5173' ? '127.0.0.1:8000/api/v1' : window.location.host + '/api/v1');
    const wsUrl = `${wsBase}/live-meetings/${sessionId}/stream?token=${encodeURIComponent(token || '')}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'connection_status') {
          setConnectionStatus('Connected');
        } else if (data.type === 'partial_transcript') {
          setPartialText(data.text);
        } else if (data.type === 'transcript') {
          setPartialText('');
          if (data.segment) {
            setTranscript((prev) => [...prev, data.segment]);
          }
          if (data.live_intelligence) {
            setLiveIntelligence({
              decisions: data.live_intelligence.decisions || [],
              action_items: data.live_intelligence.action_items || [],
              unresolved_questions: data.live_intelligence.unresolved_questions || [],
              risks_blockers: data.live_intelligence.risks_blockers || [],
              topics: data.live_intelligence.topics || [],
              timeline_events: data.live_intelligence.timeline_events || []
            });
          }
        } else if (data.type === 'session_status') {
          setSessionStatus(data.status);
        } else if (data.type === 'final_report') {
          setSessionStatus('COMPLETED');
          setConnectionStatus('Disconnected');
        } else if (data.type === 'error') {
          setErrorMsg(data.message);
        }
      } catch (e) {
        console.error('Error parsing WS message', e);
      }
    };

    ws.onerror = (err) => {
      console.error('WS error', err);
      setConnectionStatus('Reconnecting');
    };

    ws.onclose = () => {
      setConnectionStatus('Disconnected');
    };
  };

  const startMicrophoneCapture = async (sessionId) => {
    try {
      // 1. Web Speech API for real-time live text streaming
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
          let interim = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcriptChunk = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                  type: 'transcript',
                  text: transcriptChunk,
                  speaker: 'Speaker 1'
                }));
              }
            } else {
              interim += transcriptChunk;
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                  type: 'partial_transcript',
                  text: interim,
                  speaker: 'Speaker 1'
                }));
              }
            }
          }
        };

        recognition.onerror = (err) => {
          console.warn('Speech Recognition error:', err.error);
        };

        recognition.start();
        recognitionRef.current = recognition;
      }

      // 2. MediaRecorder for continuous audio chunk streaming
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(e.data);
          }
        };

        mediaRecorder.start(3000); // 3-second slices
      }
    } catch (err) {
      console.error('Microphone capture error:', err);
      setErrorMsg('Microphone permission is required to start a live meeting session.');
    }
  };

  const pauseMeeting = async () => {
    if (!session) return;
    try {
      await api.pauseLiveSession(session.session_id);
      setSessionStatus('PAUSED');
      if (recognitionRef.current) recognitionRef.current.stop();
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'pause' }));
      }
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  const resumeMeeting = async () => {
    if (!session) return;
    try {
      await api.resumeLiveSession(session.session_id);
      setSessionStatus('RECORDING');
      if (recognitionRef.current) recognitionRef.current.start();
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'resume' }));
      }
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  const stopMeeting = async () => {
    if (!session) return;
    try {
      setSessionStatus('STOPPING');
      if (recognitionRef.current) recognitionRef.current.stop();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      }

      await api.stopLiveSession(session.session_id);
      setSessionStatus('COMPLETED');
      navigate(`/meetings/${session.meeting_id}`);
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header & Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <span className={`w-3 h-3 rounded-full ${sessionStatus === 'RECORDING' ? 'bg-red-500 animate-ping' : 'bg-slate-500'}`} />
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {sessionStatus === 'IDLE' ? 'Start Live Meeting' : title}
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Real-time speech-to-text, live incremental intelligence, and decision extraction
          </p>
        </div>

        {sessionStatus === 'IDLE' ? (
          <div className="flex items-center space-x-3 w-full md:w-auto">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Meeting Title..."
              className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500 w-full md:w-64"
            />
            <button
              onClick={startSession}
              disabled={isStarting}
              className="px-5 py-2.5 bg-gradient-to-r from-red-600 to-indigo-600 hover:from-red-500 hover:to-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg shadow-red-900/20 transition-all flex items-center space-x-2 shrink-0"
            >
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="6" fill="currentColor" />
              </svg>
              <span>{isStarting ? 'Starting...' : 'Start Live Session'}</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            {/* Status & Timer Badges */}
            <div className="flex items-center space-x-2 bg-slate-950 px-3.5 py-2 rounded-lg border border-slate-800">
              <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                sessionStatus === 'RECORDING' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                sessionStatus === 'PAUSED' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
              }`}>
                {sessionStatus}
              </span>
              <span className="text-lg font-mono font-bold text-white tracking-wider">
                {formatTimer(timerSeconds)}
              </span>
            </div>

            {/* Connection Status Badge */}
            <div className="flex items-center space-x-1.5 bg-slate-950 px-3 py-2 rounded-lg border border-slate-800 text-xs font-medium">
              <span className={`w-2 h-2 rounded-full ${connectionStatus === 'Connected' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
              <span className="text-slate-300">{connectionStatus}</span>
            </div>

            {/* Session Action Controls */}
            {sessionStatus === 'RECORDING' && (
              <button
                onClick={pauseMeeting}
                className="px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 font-medium text-sm rounded-lg transition-colors"
              >
                Pause
              </button>
            )}

            {sessionStatus === 'PAUSED' && (
              <button
                onClick={resumeMeeting}
                className="px-4 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 font-medium text-sm rounded-lg transition-colors"
              >
                Resume
              </button>
            )}

            <button
              onClick={stopMeeting}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-medium text-sm rounded-lg shadow-md transition-colors"
            >
              Stop Meeting
            </button>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-sm flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-xs underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Main Grid: Transcript vs Live Intelligence */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live Transcript Stream (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col h-[640px]">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center space-x-2">
              <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
              </svg>
              <span>Live Transcript</span>
            </h2>
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
                autoScroll ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
            {transcript.length === 0 && !partialText ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                  </svg>
                </div>
                <p className="text-sm font-medium">Waiting for speech input...</p>
                <p className="text-xs text-slate-600 mt-1">Speak into your microphone to view live transcript segments.</p>
              </div>
            ) : (
              <>
                {transcript.map((seg, idx) => (
                  <div key={seg.id || idx} className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3.5 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-indigo-400">{seg.speaker_name || seg.speaker_label || 'Speaker 1'}</span>
                      <span className="text-slate-500 font-mono">
                        {seg.start_time !== undefined ? `${Math.floor(seg.start_time / 60)}:${String(Math.floor(seg.start_time % 60)).padStart(2, '0')}` : 'Live'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-200 leading-relaxed">{seg.text}</p>
                  </div>
                ))}

                {partialText && (
                  <div className="bg-slate-950/40 border border-indigo-500/20 rounded-lg p-3.5 space-y-1 animate-pulse">
                    <div className="text-xs font-semibold text-indigo-400">Speaker 1 (speaking...)</div>
                    <p className="text-sm text-slate-400 italic">{partialText}</p>
                  </div>
                )}
              </>
            )}
            <div ref={transcriptEndRef} />
          </div>
        </div>

        {/* Right Column: Live Intelligence Stream (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Live Decisions */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h3 className="text-md font-semibold text-white mb-3 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              <span>Confirmed Decisions ({liveIntelligence.decisions.length})</span>
            </h3>
            {liveIntelligence.decisions.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No decisions extracted yet.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {liveIntelligence.decisions.map((d, i) => (
                  <div key={i} className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-xs space-y-1">
                    <p className="font-medium text-emerald-300">{d.decision_text}</p>
                    <p className="text-slate-400 italic text-[11px]">"{d.context_quote}"</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Live Action Items */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h3 className="text-md font-semibold text-white mb-3 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
              <span>Action Items ({liveIntelligence.action_items.length})</span>
            </h3>
            {liveIntelligence.action_items.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No action items extracted yet.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {liveIntelligence.action_items.map((a, i) => (
                  <div key={i} className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-3 text-xs space-y-1">
                    <p className="font-medium text-indigo-200">{a.task_description}</p>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                      <span>Owner: <strong className="text-slate-300">{a.responsible_person || 'Not specified'}</strong></span>
                      <span>Due: <strong className="text-slate-300">{a.deadline || 'Not specified'}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Live Risks & Open Questions Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Risks */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
              <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400 mb-2">
                Risks ({liveIntelligence.risks_blockers.length})
              </h4>
              {liveIntelligence.risks_blockers.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic">None detected.</p>
              ) : (
                <div className="space-y-2 max-h-36 overflow-y-auto">
                  {liveIntelligence.risks_blockers.map((r, i) => (
                    <p key={i} className="text-xs text-slate-300 bg-rose-500/10 border border-rose-500/20 p-2 rounded">
                      {r.description}
                    </p>
                  ))}
                </div>
              )}
            </div>

            {/* Questions */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 mb-2">
                Open Questions ({liveIntelligence.unresolved_questions.length})
              </h4>
              {liveIntelligence.unresolved_questions.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic">None open.</p>
              ) : (
                <div className="space-y-2 max-h-36 overflow-y-auto">
                  {liveIntelligence.unresolved_questions.map((q, i) => (
                    <p key={i} className="text-xs text-slate-300 bg-amber-500/10 border border-amber-500/20 p-2 rounded">
                      {q.question}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveMeeting;
