import React from 'react';
import { FileUpload } from '../components/FileUpload';

export function UploadMeeting() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Upload Meeting File</h1>
        <p className="text-slate-400 text-sm mt-1">
          Select an audio, video, or text transcript file to process through the Meeting AI Intelligence pipeline.
        </p>
      </div>

      <FileUpload />
    </div>
  );
}
