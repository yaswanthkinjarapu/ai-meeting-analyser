import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export function Settings() {
  const [settings, setSettings] = useState({
    timezone: 'UTC',
    reminder_lead_minutes: 15,
    email_notifications_enabled: true,
    in_app_notifications_enabled: true,
    calendar_provider: 'mock',
    email_provider: 'mock',
  });
  const [calendarStatus, setCalendarStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [userSet, calStat] = await Promise.all([
        api.getUserSettings(),
        api.getCalendarStatus().catch(() => null),
      ]);
      if (userSet) setSettings(userSet);
      if (calStat) setCalendarStatus(calStat);
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to load settings.' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateUserSettings(settings);
      setSettings(updated);
      setMessage({ type: 'success', text: 'Settings updated successfully!' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to save settings.' });
    } finally {
      setSaving(false);
    }
  };

  const toggleCalendarConnection = async () => {
    try {
      if (calendarStatus?.connected) {
        const res = await api.disconnectCalendar();
        setCalendarStatus(res);
        setMessage({ type: 'info', text: 'Calendar disconnected.' });
      } else {
        const res = await api.connectCalendar();
        setCalendarStatus(res);
        setMessage({ type: 'success', text: 'Calendar connected successfully!' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to update calendar integration.' });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mr-3"></div>
        Loading preferences...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">User Settings & Integration Hub</h1>
        <p className="text-slate-400 text-sm mt-1">
          Configure default timezones, reminder notifications, and external provider connections.
        </p>
      </div>

      {message && (
        <div
          className={`p-4 rounded-xl border text-sm ${
            message.type === 'error'
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              : message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
          }`}
        >
          {message.text}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Timezone & Regional Settings */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-200 border-b border-slate-800 pb-3 flex items-center gap-2">
            <span>🌐</span> Timezone & Regional Setup
          </h2>
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Default System Timezone
            </label>
            <select
              value={settings.timezone}
              onChange={(e) => handleChange('timezone', e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="UTC">UTC (Universal Coordinated Time)</option>
              <option value="America/New_York">America/New_York (EST/EDT)</option>
              <option value="America/Chicago">America/Chicago (CST/CDT)</option>
              <option value="America/Denver">America/Denver (MST/MDT)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
              <option value="Europe/London">Europe/London (GMT/BST)</option>
              <option value="Europe/Paris">Europe/Paris (CET/CEST)</option>
              <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
              <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
              <option value="Australia/Sydney">Australia/Sydney (AEST/AEDT)</option>
            </select>
            <p className="text-xs text-slate-500 mt-1">
              All relative deadlines (e.g., "by 5 PM tomorrow") are resolved using this timezone.
            </p>
          </div>
        </div>

        {/* Reminder & Notification Preferences */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-200 border-b border-slate-800 pb-3 flex items-center gap-2">
            <span>🔔</span> Follow-up Reminders & Alerts
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">
                Default Reminder Lead Time (Minutes)
              </label>
              <input
                type="number"
                min="5"
                max="1440"
                value={settings.reminder_lead_minutes}
                onChange={(e) => handleChange('reminder_lead_minutes', parseInt(e.target.value) || 15)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex flex-col justify-end space-y-3">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.email_notifications_enabled}
                  onChange={(e) => handleChange('email_notifications_enabled', e.target.checked)}
                  className="rounded border-slate-800 text-indigo-600 focus:ring-indigo-500 bg-slate-950 h-4 w-4"
                />
                <span className="text-sm text-slate-300">Enable Email Alerts</span>
              </label>
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.in_app_notifications_enabled}
                  onChange={(e) => handleChange('in_app_notifications_enabled', e.target.checked)}
                  className="rounded border-slate-800 text-indigo-600 focus:ring-indigo-500 bg-slate-950 h-4 w-4"
                />
                <span className="text-sm text-slate-300">Enable In-App Banners</span>
              </label>
            </div>
          </div>
        </div>

        {/* Integration Integrations */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-200 border-b border-slate-800 pb-3 flex items-center gap-2">
            <span>📅</span> Calendar & Communication Integrations
          </h2>

          <div className="flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-xl">
            <div>
              <h3 className="font-semibold text-slate-200 text-sm">Google Calendar Provider</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Sync action item follow-ups directly to your Google Calendar.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`inline-block w-2.5 h-2.5 rounded-full ${
                    calendarStatus?.connected ? 'bg-emerald-400' : 'bg-slate-600'
                  }`}
                />
                <span className="text-xs text-slate-300 font-mono">
                  {calendarStatus?.connected ? `Connected (${calendarStatus.provider})` : 'Disconnected'}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={toggleCalendarConnection}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                calendarStatus?.connected
                  ? 'bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/30'
                  : 'bg-indigo-600 text-white hover:bg-indigo-500'
              }`}
            >
              {calendarStatus?.connected ? 'Disconnect Calendar' : 'Connect Calendar'}
            </button>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;
