import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import LandingPage from './pages/LandingPage';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import StaffLogin from './pages/StaffLogin';
import StaffPortal from './pages/StaffPortal';
import PatientPortal from './pages/PatientPortal';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
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
  );
}
