import axios from 'axios';

// Dynamically detect server host (works on localhost AND across LAN laptops automatically)
const defaultHost = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1';
export const API_BASE = import.meta.env.VITE_API_BASE && !import.meta.env.VITE_API_BASE.includes('127.0.0.1')
  ? import.meta.env.VITE_API_BASE
  : `http://${defaultHost}:8000`;

export const WS_BASE = import.meta.env.VITE_WS_BASE && !import.meta.env.VITE_WS_BASE.includes('127.0.0.1')
  ? import.meta.env.VITE_WS_BASE
  : `ws://${defaultHost}:8000`;

export const WS_LIVE_URL = `${WS_BASE}/ws/live`;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization header from sessionStorage if token is present
api.interceptors.request.use((config) => {
  // Check for admin_token first, then staff_token
  const adminToken = sessionStorage.getItem('admin_token');
  const staffToken = sessionStorage.getItem('staff_token');

  if (adminToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${adminToken}`;
  } else if (staffToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${staffToken}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// ==========================================
// AUTHENTICATION
// ==========================================
export const adminLogin = (password) => api.post('/admin/login', { password });
export const staffLogin = (password) => api.post('/staff/login', { password });

// ==========================================
// PATIENT PORTAL (PUBLIC / NO AUTH)
// ==========================================
export const getPublicAvailability = () => api.get('/patient-portal/availability');
export const getOutpatientDepartments = () => api.get('/patient-portal/departments');
export const bookAppointment = (data) => api.post('/patient-portal/book-appointment', data);
export const checkAppointmentStatus = (appointmentId) => api.get(`/patient-portal/appointment/${appointmentId}`);

// ==========================================
// STAFF PORTAL (REQUIRES STAFF TOKEN)
// ==========================================
export const getStaffRoster = (token) => api.get('/staff-portal/roster', {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getStaffDashboard = (staffId, token) => api.get(`/staff-portal/${staffId}/dashboard`, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getStaffNotifications = (staffId, unreadOnly = true, token) => api.get(`/staff-portal/${staffId}/notifications`, {
  params: { unread_only: unreadOnly },
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const markNotificationRead = (staffId, notificationId, token) => api.post(`/staff-portal/${staffId}/notifications/${notificationId}/mark-read`, {}, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const toggleStaffDuty = (staffId, token) => api.post(`/staff-portal/${staffId}/toggle-duty`, {}, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});

// ==========================================
// ADMIN DASHBOARD & SIMULATION (REQUIRES ADMIN TOKEN)
// ==========================================
export const getDepartments = (token) => api.get('/departments', {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getBeds = (departmentId, token) => api.get('/beds', {
  params: { department_id: departmentId },
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getPatients = (status, token) => api.get('/patients', {
  params: { status },
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getPatientById = (patientId, token) => api.get(`/patients/${patientId}`, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getStaff = (departmentId, token) => api.get('/staff', {
  params: { department_id: departmentId },
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getDiagnostics = (departmentId, token) => api.get('/diagnostics', {
  params: { department_id: departmentId },
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getEvents = (limit = 50, token) => api.get('/events', {
  params: { limit },
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getForecast = (departmentId, horizonHours = 2) => api.get(`/forecast/${departmentId}`, {
  params: { horizon_hours: horizonHours }
});

export const registerPatientIntake = (data, token) => api.post('/patients/intake', data, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});

export const startSimulation = (speedFactor = 2.0, token) => api.post('/simulation/start', { speed_factor: speedFactor }, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const stopSimulation = (token) => api.post('/simulation/stop', {}, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const triggerSurge = (department = 'er', patientCount = 8, token) => api.post('/simulation/surge', { department, patient_count: patientCount }, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const resetSystem = (token) => api.post('/simulation/reset', {}, {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});
export const getSimulationStatus = (token) => api.get('/simulation/status', {
  headers: token ? { Authorization: `Bearer ${token}` } : undefined
});

export default api;
