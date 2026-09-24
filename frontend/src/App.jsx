import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Info } from 'lucide-react';

import LandingPage from './pages/LandingPage';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import StaffLogin from './pages/StaffLogin';
import StaffPortal from './pages/StaffPortal';
import PatientPortal from './pages/PatientPortal';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  return (
    <ErrorBoundary>
      <div className="bg-cyan-950/90 border-b border-cyan-800/80 px-4 py-1.5 text-center text-xs text-cyan-200 font-medium flex items-center justify-center space-x-2 shadow-inner">
        <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        <span>Demo – all data is simulated. No real patient information.</span>
      </div>
      <BrowserRouter>
        <Routes>
          {/* Public Landing Gateway */}
          <Route path="/" element={<LandingPage />} />

          {/* Public Patient Services Portal */}
          <Route path="/patient" element={<PatientPortal />} />

          {/* Admin Login & Protected Admin Dashboard */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute tokenKey="admin_token" redirectPath="/admin/login">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Staff Login & Protected Clinical Staff Workspace */}
          <Route path="/staff/login" element={<StaffLogin />} />
          <Route
            path="/staff"
            element={
              <ProtectedRoute tokenKey="staff_token" redirectPath="/staff/login">
                <StaffPortal />
              </ProtectedRoute>
            }
          />

          {/* Fallback to Home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
