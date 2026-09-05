import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

export default function ProtectedRoute({ tokenKey = 'admin_token', redirectPath = '/admin/login', children }) {
  const token = sessionStorage.getItem(tokenKey);

  if (!token) {
    return <Navigate to={redirectPath} replace />;
  }

  return children ? children : <Outlet />;
}
