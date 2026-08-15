import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getDepartments = () => api.get('/departments');
export const getBeds = (departmentId) => api.get('/beds', { params: { department_id: departmentId } });
export const getPatients = (status) => api.get('/patients', { params: { status } });
export const getStaff = (departmentId) => api.get('/staff', { params: { department_id: departmentId } });
export const getDiagnostics = (departmentId) => api.get('/diagnostics', { params: { department_id: departmentId } });
export const getEvents = (limit = 50) => api.get('/events', { params: { limit } });
export const getForecast = (departmentId, horizonHours = 2) => api.get(`/forecast/${departmentId}`, { params: { horizon_hours: horizonHours } });

export const startSimulation = (speedFactor = 2.0) => api.post('/simulation/start', { speed_factor: speedFactor });
export const stopSimulation = () => api.post('/simulation/stop');
export const triggerSurge = (department = 'er', patientCount = 8) => api.post('/simulation/surge', { department, patient_count: patientCount });
export const resetSystem = () => api.post('/simulation/reset');
export const getSimulationStatus = () => api.get('/simulation/status');

export const WS_LIVE_URL = 'ws://127.0.0.1:8000/ws/live';

export default api;
