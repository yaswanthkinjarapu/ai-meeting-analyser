import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { UploadMeeting } from './pages/UploadMeeting';
import { MeetingDetails } from './pages/MeetingDetails';
import { LiveMeeting } from './pages/LiveMeeting';
import { FollowUpCenter } from './pages/FollowUpCenter';
import { Settings } from './pages/Settings';
import { Login } from './pages/Login';
import { Register } from './pages/Register';

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live" element={<LiveMeeting />} />
              <Route path="/live/:sessionId" element={<LiveMeeting />} />
              <Route path="/upload" element={<UploadMeeting />} />
              <Route path="/follow-ups" element={<FollowUpCenter />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/meetings/:meetingId" element={<MeetingDetails />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
            </Routes>
          </main>
          <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-600">
            Meeting AI Intelligence & Follow-up Agent &copy; {new Date().getFullYear()}
          </footer>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
