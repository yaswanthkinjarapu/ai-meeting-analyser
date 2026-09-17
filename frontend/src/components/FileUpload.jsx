import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export function FileUpload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ''));
      }
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ''));
      }
      setError(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a meeting file to upload.');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData();
    formData.append('file', file);
    if (title) {
      formData.append('title', title);
    }

    try {
      const res = await api.uploadMeeting(formData);
      setSuccess(res);
      setUploading(false);
      // Auto navigate after short delay
      setTimeout(() => {
        navigate(`/meetings/${res.meeting.id}`);
      }, 1200);
    } catch (err) {
      setError(err.message || 'Unable to upload meeting file.');
      setUploading(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">
            Meeting Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Q3 Architecture Sync"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">
            Meeting File (Audio, Video, or Transcript)
          </label>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-xl p-8 text-center bg-slate-950/50 hover:bg-slate-950/80 transition-all cursor-pointer group"
          >
            <input
              type="file"
              onChange={handleFileChange}
              accept=".txt,.pdf,.docx,.mp3,.wav,.m4a,.flac,.ogg,.mp4,.mov,.mkv,.avi,.webm"
              className="hidden"
              id="file-upload-input"
            />
            <label htmlFor="file-upload-input" className="cursor-pointer">
              <div className="w-12 h-12 rounded-full bg-indigo-600/10 text-indigo-400 mx-auto mb-3 flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>

              {file ? (
                <div>
                  <p className="text-sm font-semibold text-indigo-400">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-medium text-slate-300">
                    Click to browse or drag and drop meeting file
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Supported: TXT, PDF, DOCX, MP3, WAV, M4A, FLAC, OGG, MP4, MOV, MKV, AVI, WEBM
                  </p>
                </div>
              )}
            </label>
          </div>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs rounded-lg p-3">
            ⚠️ {error}
          </div>
        )}

        {success && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-lg p-3 flex items-center justify-between">
            <span>✅ {success.message}</span>
            <span className="animate-spin text-emerald-400">🌀</span>
          </div>
        )}

        <button
          type="submit"
          disabled={uploading || !file}
          className={`w-full py-3 px-4 rounded-xl font-medium text-sm transition-all shadow-lg ${
            uploading || !file
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20 active:scale-[0.99]'
          }`}
        >
          {uploading ? 'Uploading & Processing Meeting...' : 'Upload & Process Meeting'}
        </button>
      </form>
    </div>
  );
}
