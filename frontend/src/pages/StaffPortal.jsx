import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserCheck,
  Bell,
  Check,
  Clock,
  LogOut,
  ArrowRightLeft,
  Activity,
  Calendar,
  AlertCircle,
  Building,
  MapPin,
  Stethoscope,
  Users,
  CheckCircle2,
  RefreshCw,
  Power
} from 'lucide-react';
import {
  getStaffRoster,
  getStaffDashboard,
  getStaffNotifications,
  markNotificationRead,
  toggleStaffDuty
} from '../api';

export default function StaffPortal() {
  const navigate = useNavigate();
  const token = sessionStorage.getItem('staff_token');

  const [roster, setRoster] = useState([]);
  const [selectedStaffId, setSelectedStaffId] = useState(
    sessionStorage.getItem('selected_staff_id') || ''
  );
  const [dashboardData, setDashboardData] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dutyLoading, setDutyLoading] = useState(false);

  const pollRef = useRef(null);

  const handleLogout = () => {
    sessionStorage.removeItem('staff_token');
    sessionStorage.removeItem('selected_staff_id');
    navigate('/');
  };

  // 1. Fetch Roster on load
  useEffect(() => {
    const fetchRoster = async () => {
      try {
        setLoading(true);
        const res = await getStaffRoster(token);
        setRoster(res.data);
        if (!selectedStaffId && res.data.length > 0) {
          // Default to first staff or saved
          setSelectedStaffId(res.data[0].staff_id);
          sessionStorage.setItem('selected_staff_id', res.data[0].staff_id);
        }
      } catch (err) {
        console.error('Error fetching staff roster:', err);
        if (err.response?.status === 401 || err.response?.status === 403) {
          handleLogout();
        } else {
          setError('Failed to load staff roster.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchRoster();
  }, [token]);

  // 2. Fetch Selected Staff Dashboard and Poll Notifications
  const loadStaffDetails = async () => {
    if (!selectedStaffId) return;
    try {
      const [dashRes, notifsRes] = await Promise.all([
        getStaffDashboard(selectedStaffId, token),
        getStaffNotifications(selectedStaffId, false, token)
      ]);
      setDashboardData(dashRes.data);
      setNotifications(notifsRes.data);
    } catch (err) {
      console.error('Error loading staff details:', err);
    }
  };

  useEffect(() => {
    if (!selectedStaffId) return;
    sessionStorage.setItem('selected_staff_id', selectedStaffId);
    loadStaffDetails();

    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(loadStaffDetails, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [selectedStaffId, token]);

  // 3. Handle Notification Mark Read
  const handleMarkRead = async (notifId) => {
    try {
      await markNotificationRead(selectedStaffId, notifId, token);
      setNotifications((prev) =>
        prev.map((n) => (n.notification_id === notifId ? { ...n, is_read: true } : n))
      );
      if (dashboardData) {
        setDashboardData((prev) => ({
          ...prev,
          unread_notifications_count: Math.max(0, (prev.unread_notifications_count || 1) - 1)
        }));
      }
    } catch (err) {
      console.error('Error marking notification read:', err);
    }
  };

  // 4. Handle Toggle Duty (On Duty <-> Off Duty)
  const handleToggleDuty = async () => {
    if (!selectedStaffId || dutyLoading) return;
    setDutyLoading(true);
    try {
      const res = await toggleStaffDuty(selectedStaffId, token);
      if (dashboardData) {
        setDashboardData((prev) => ({
          ...prev,
          status: res.data.new_status
        }));
      }
      setRoster((prev) =>
        prev.map((s) => (s.staff_id === selectedStaffId ? { ...s, status: res.data.new_status } : s))
      );
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to toggle duty status.');
    } finally {
      setDutyLoading(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  if (loading && roster.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading Clinical Staff Portal...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col p-4 md:p-6 space-y-6">
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-xl text-white shadow-lg shadow-indigo-950/50">
            <UserCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-black tracking-tight text-white flex items-center gap-2">
              CLINICAL STAFF PORTAL
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                Staff Workspace
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Personal Duty Roster • Live Patient Queue • Direct Acuity Alerts
            </p>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center space-x-3">
          {/* Staff Identity Selector */}
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
            <Users className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
            <select
              value={selectedStaffId}
              onChange={(e) => setSelectedStaffId(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer pr-2"
            >
              {roster.map((s) => (
                <option key={s.staff_id} value={s.staff_id} className="bg-slate-950 text-slate-200">
                  {s.role} - {s.staff_id} ({s.department_name})
                </option>
              ))}
            </select>
          </div>

          {/* Notification Bell with Badge */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className={`relative p-2 rounded-xl border transition ${
                showNotifications || unreadCount > 0
                  ? 'bg-indigo-950/80 border-indigo-600/80 text-indigo-200'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 text-white rounded-full text-[10px] font-bold flex items-center justify-center animate-pulse">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notification Dropdown */}
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 md:w-96 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center space-x-2">
                    <Bell className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-xs font-bold text-slate-200">Clinical Alerts</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    {unreadCount} unread
                  </span>
                </div>

                <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                  {notifications.length === 0 ? (
                    <p className="text-xs text-slate-500 italic text-center py-4">No notifications</p>
                  ) : (
                    notifications.map((n) => (
                      <div
                        key={n.notification_id}
                        className={`p-2.5 rounded-xl border text-xs transition flex items-start justify-between gap-2 ${
                          n.is_read
                            ? 'bg-slate-950/50 border-slate-800/60 text-slate-400'
                            : 'bg-indigo-950/50 border-indigo-600/60 text-indigo-200 shadow-sm'
                        }`}
                      >
                        <div className="space-y-1">
                          <p className="font-medium text-[11px] leading-snug">{n.message}</p>
                          <span className="text-[9px] font-mono text-slate-500">
                            {n.created_at ? new Date(n.created_at).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        {!n.is_read && (
                          <button
                            onClick={() => handleMarkRead(n.notification_id)}
                            title="Mark as read"
                            className="p-1 rounded bg-indigo-500/20 hover:bg-indigo-500/40 text-indigo-300 transition flex-shrink-0"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="flex items-center space-x-1.5 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 px-3 py-1.5 rounded-xl transition text-xs font-semibold"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Staff Identity & Shift Summary Ribbon */}
      {dashboardData && (
        <section className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            {/* Staff Bio */}
            <div className="flex items-center space-x-4">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold text-lg">
                {dashboardData.role.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white">{dashboardData.role}</h2>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    ID: {dashboardData.staff_id}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mt-1">
                  <span className="flex items-center gap-1">
                    <Building className="w-3.5 h-3.5 text-slate-500" />
                    {dashboardData.department_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <Stethoscope className="w-3.5 h-3.5 text-slate-500" />
                    {dashboardData.specialty || 'General Practice'}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    {dashboardData.floor || '1st Floor'} • {dashboardData.room_number || 'Room 101'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    Shift: {dashboardData.shift_start} - {dashboardData.shift_end}
                  </span>
                </div>
              </div>
            </div>

            {/* Duty Status & Toggle Button */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="sm:text-right">
                <span className="block text-[10px] uppercase font-semibold text-slate-400">Current Status</span>
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                    dashboardData.status === 'reassigned'
                      ? 'bg-amber-950 text-amber-300 border-amber-500 animate-pulse'
                      : dashboardData.status === 'on_duty'
                      ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      dashboardData.status === 'reassigned'
                        ? 'bg-amber-400 animate-ping'
                        : dashboardData.status === 'on_duty'
                        ? 'bg-emerald-400'
                        : 'bg-slate-500'
                    }`}
                  />
                  {dashboardData.status === 'reassigned'
                    ? 'SURGE REASSIGNED'
                    : dashboardData.status === 'on_duty'
                    ? 'ON DUTY'
                    : 'OFF DUTY'}
                </span>
              </div>

              {/* Two-Way Toggle Button */}
              <button
                type="button"
                onClick={handleToggleDuty}
                disabled={dutyLoading || dashboardData.status === 'reassigned'}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2 border disabled:opacity-50 ${
                  dashboardData.status === 'on_duty'
                    ? 'bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-800 hover:bg-slate-750 text-slate-300 border-slate-700'
                }`}
              >
                <Power className={`w-3.5 h-3.5 ${dashboardData.status === 'on_duty' ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>
                  {dutyLoading
                    ? 'Updating...'
                    : dashboardData.status === 'on_duty'
                    ? 'Set Off Duty'
                    : 'Set On Duty'}
                </span>
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Main Work Area: Inpatient Patients or Outpatient Appointments */}
      {dashboardData && (
        <main className="flex-1 space-y-4">
          {dashboardData.is_outpatient ? (
            /* OUTPATIENT CONSULTATION QUEUE */
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-indigo-400" />
                  <h3 className="font-bold text-slate-100 text-sm">
                    Outpatient Consultation Queue ({dashboardData.appointments.length} active)
                  </h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  Room: {dashboardData.room_number || 'OPD-101'}
                </span>
              </div>

              {dashboardData.appointments.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500/40 mx-auto" />
                  <p>No waiting patients in queue. You are all caught up!</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {dashboardData.appointments.map((apt) => (
                    <div
                      key={apt.appointment_id}
                      className={`p-4 rounded-xl border flex flex-col justify-between transition ${
                        apt.status === 'in_consultation'
                          ? 'bg-indigo-950/60 border-indigo-500/80 shadow-md shadow-indigo-950/50'
                          : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-sm text-slate-100">{apt.patient_name}</span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                              apt.status === 'in_consultation'
                                ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 animate-pulse'
                                : 'bg-slate-800 text-slate-300 border-slate-700'
                            }`}
                          >
                            {apt.status === 'in_consultation' ? 'In Consultation' : `Queue #${apt.queue_position}`}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 space-y-1 mb-3">
                          <p>
                            <span className="text-slate-500">Age:</span>{' '}
                            {apt.patient_age !== null ? `${apt.patient_age} yrs` : 'Not specified'}
                          </p>
                          <p>
                            <span className="text-slate-500">Chief Complaint:</span>{' '}
                            <span className="text-slate-300 font-medium">{apt.reason_for_visit}</span>
                          </p>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                        <span>ID: {apt.appointment_id}</span>
                        <span>Est. Wait: {apt.estimated_wait_minutes}m</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* INPATIENT ASSIGNED ADMITTED PATIENTS */
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div className="flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-slate-100 text-sm">
                    Assigned Inpatient Cases ({dashboardData.assigned_patients.length} admitted)
                  </h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {dashboardData.department_name}
                </span>
              </div>

              {dashboardData.assigned_patients.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500/40 mx-auto" />
                  <p>No currently assigned admitted patients. Ready for new admissions.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {dashboardData.assigned_patients.map((p) => (
                    <div
                      key={p.patient_id}
                      className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-sm text-slate-100 font-mono">{p.patient_id}</span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                              p.severity === 'critical'
                                ? 'bg-rose-950 text-rose-300 border-rose-600'
                                : p.severity === 'moderate'
                                ? 'bg-amber-950 text-amber-300 border-amber-600'
                                : 'bg-emerald-950 text-emerald-300 border-emerald-600'
                            }`}
                          >
                            {p.severity} Acuity
                          </span>
                        </div>

                        <div className="text-xs text-slate-400 space-y-1 mb-3">
                          <p>
                            <span className="text-slate-500">Age:</span>{' '}
                            {p.age !== null && p.age !== undefined ? `${p.age} years` : 'N/A'}
                          </p>
                          <p>
                            <span className="text-slate-500">Reason:</span>{' '}
                            <span className="text-slate-300 font-medium">{p.reason_for_visit}</span>
                          </p>
                          <p>
                            <span className="text-slate-500">Bed Location:</span>{' '}
                            <span className="font-mono text-cyan-400 font-semibold">{p.assigned_bed_id || 'Triage'}</span>
                          </p>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                        <span>Est. Stay: {p.predicted_stay_hours}h</span>
                        <span>{p.arrival_time ? new Date(p.arrival_time).toLocaleTimeString() : ''}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      )}
    </div>
  );
}
