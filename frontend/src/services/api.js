const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

function getAuthHeaders(headers = {}) {
  const token = localStorage.getItem('meeting_ai_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const err = await response.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch (e) {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  // Authentication Endpoints
  async register(data) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async login(data) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 1. List all meetings
  async getMeetings() {
    const res = await fetch(`${API_BASE}/meetings`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 2. Get meeting stats
  async getStats() {
    const res = await fetch(`${API_BASE}/meetings/stats`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 3. Search meetings
  async searchMeetings(query) {
    const res = await fetch(`${API_BASE}/meetings/search?q=${encodeURIComponent(query)}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 4. Get single meeting by ID
  async getMeeting(id) {
    const res = await fetch(`${API_BASE}/meetings/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 5. Upload meeting file
  async uploadMeeting(formData) {
    const res = await fetch(`${API_BASE}/meetings/upload`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return handleResponse(res);
  },

  // 6. Delete meeting
  async deleteMeeting(id) {
    const res = await fetch(`${API_BASE}/meetings/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 7. Retrieve transcript segments
  async getTranscript(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/transcript`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 8. Trigger transcript processing for TXT
  async processTranscript(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/process-transcript`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 9. Trigger audio speech-to-text transcription
  async transcribeAudio(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/transcribe`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 10. Trigger video FFmpeg extraction & transcription
  async processVideo(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/process-video`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 11. Trigger speaker diarization
  async diarizeMeeting(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/diarize`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 12. Get meeting speaker list
  async getSpeakers(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/speakers`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 13. Map speaker label to user-provided name
  async updateSpeakerName(meetingId, speakerId, speakerName) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/speakers/${speakerId}`, {
      method: 'PUT',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ speaker_name: speakerName }),
    });
    return handleResponse(res);
  },

  // 14. Trigger AI Intelligence Analysis
  async analyzeMeeting(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/analyze`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 15. Get stored AI Intelligence Analysis
  async getAnalysis(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/analysis`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // 16. Update Action Item
  async updateActionItem(meetingId, actionItemId, data) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/action-items/${actionItemId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  // 17. Update Decision
  async updateDecision(meetingId, decisionId, data) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/decisions/${decisionId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  // 18. Update Unresolved Question
  async updateQuestion(meetingId, questionId, data) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/questions/${questionId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  // 19. Export Meeting Report
  async exportMeeting(meetingId, format = 'markdown') {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/export?format=${format}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      throw new Error('Failed to export meeting report');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `meeting_report_${meetingId}.${format === 'json' ? 'json' : 'md'}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  },

  // Phase 10 API Methods
  async getIntelligence(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/intelligence`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getTopics(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/topics`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getTimeline(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/timeline`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getRisks(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/risks`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getDependencies(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/dependencies`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getFollowUp(meetingId) {
    const res = await fetch(`${API_BASE}/meetings/${meetingId}/follow-up`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // Phase 11 Live Meeting API Methods
  async startLiveMeeting(title = 'Live Meeting') {
    const res = await fetch(`${API_BASE}/live-meetings`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ title }),
    });
    return handleResponse(res);
  },

  async getLiveSession(sessionId) {
    const res = await fetch(`${API_BASE}/live-meetings/${sessionId}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async pauseLiveSession(sessionId) {
    const res = await fetch(`${API_BASE}/live-meetings/${sessionId}/pause`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async resumeLiveSession(sessionId) {
    const res = await fetch(`${API_BASE}/live-meetings/${sessionId}/resume`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async stopLiveSession(sessionId) {
    const res = await fetch(`${API_BASE}/live-meetings/${sessionId}/stop`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // Phase 12 Follow-Up & Calendar API Methods
  async getFollowUpCenter() {
    const res = await fetch(`${API_BASE}/follow-ups`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async prepareScheduleFollowup(actionItemId) {
    const res = await fetch(`${API_BASE}/follow-ups/${actionItemId}/schedule`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getCalendarStatus() {
    const res = await fetch(`${API_BASE}/calendar/status`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async connectCalendar() {
    const res = await fetch(`${API_BASE}/calendar/connect`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async disconnectCalendar() {
    const res = await fetch(`${API_BASE}/calendar/disconnect`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getCalendarEvents() {
    const res = await fetch(`${API_BASE}/calendar/events`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async createCalendarEvent(data) {
    const res = await fetch(`${API_BASE}/calendar/events`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async deleteCalendarEvent(eventId) {
    const res = await fetch(`${API_BASE}/calendar/events/${eventId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getEmailDrafts() {
    const res = await fetch(`${API_BASE}/email/drafts`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async createEmailDraft(data) {
    const res = await fetch(`${API_BASE}/email/drafts`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async sendEmail(draftId) {
    const res = await fetch(`${API_BASE}/email/send?draft_id=${encodeURIComponent(draftId)}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getUserSettings() {
    const res = await fetch(`${API_BASE}/settings`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async updateUserSettings(data) {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  }
};
