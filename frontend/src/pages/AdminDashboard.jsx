import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  BedDouble,
  Users,
  AlertOctagon,
  Stethoscope,
  TrendingUp,
  Clock,
  Wifi,
  WifiOff,
  ShieldAlert,
  BarChart3,
  UserPlus,
  LogOut,
  ArrowLeft
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

import BedMap from '../components/BedMap';
import PatientQueue from '../components/PatientQueue';
import EventFeed from '../components/EventFeed';
import SurgeAlert from '../components/SurgeAlert';
import StaffPanel from '../components/StaffPanel';
import PatientIntakeForm from '../components/PatientIntakeForm';

import {
  getDepartments,
  getBeds,
  getStaff,
  getPatients,
  getDiagnostics,
  getEvents,
  getSimulationStatus,
  WS_LIVE_URL
} from '../api';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [departments, setDepartments] = useState([]);
  const [beds, setBeds] = useState([]);
  const [staff, setStaff] = useState([]);
  const [waitingPatients, setWaitingPatients] = useState([]);
  const [events, setEvents] = useState([]);
  const [diagnostics, setDiagnostics] = useState([]);
  const [forecasts, setForecasts] = useState({});
  const [isSimRunning, setIsSimRunning] = useState(false);
  const [simSpeed, setSimSpeed] = useState(2.0);
  const [wsConnected, setWsConnected] = useState(false);
  const [criticalAlert, setCriticalAlert] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const wsRef = useRef(null);

  const handleLogout = () => {
    sessionStorage.removeItem('admin_token');
    navigate('/');
  };

  // Initial Data Fetch with Admin Token
  const loadInitialData = async () => {
    const token = sessionStorage.getItem('admin_token');
    try {
      const [deptRes, bedsRes, staffRes, patientsRes, diagRes, eventsRes, simRes] = await Promise.all([
        getDepartments(token),
        getBeds(undefined, token),
        getStaff(undefined, token),
        getPatients('waiting', token),
        getDiagnostics(undefined, token),
        getEvents(40, token),
        getSimulationStatus(token).catch(() => ({ data: { is_running: false, speed_factor: 2.0 } }))
      ]);

      setDepartments(deptRes.data);
      setBeds(bedsRes.data);
      setStaff(staffRes.data);
      setWaitingPatients(patientsRes.data);
      setDiagnostics(diagRes.data);
      setEvents(eventsRes.data);
      setIsSimRunning(simRes.data?.is_running || false);
      setSimSpeed(simRes.data?.speed_factor || 2.0);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching initial admin data:', err);
      if (err.response?.status === 401 || err.response?.status === 403) {
        handleLogout();
      }
    }
  };

  // Connect WebSocket
  useEffect(() => {
    loadInitialData();

    const connectWebSocket = () => {
      const ws = new WebSocket(WS_LIVE_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected to live hospital feed.');
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_update') {
            if (data.departments) setDepartments(data.departments);
            if (data.beds) setBeds(data.beds);
            if (data.staff) setStaff(data.staff);
            if (data.waiting_patients) setWaitingPatients(data.waiting_patients);
            if (data.recent_events) {
              setEvents(data.recent_events);
              const topAlert = data.recent_events.find((e) => e.event_type === 'critical_no_capacity');
              if (topAlert) {
                setCriticalAlert(topAlert);
              } else {
                setCriticalAlert(null);
              }
            }
            if (data.diagnostics) setDiagnostics(data.diagnostics);
            if (data.forecasts) setForecasts(data.forecasts);
            if (data.simulation) {
              setIsSimRunning(data.simulation.is_running);
              setSimSpeed(data.simulation.speed_factor);
            }
            setLastUpdate(new Date());
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected. Retrying in 3s...');
        setWsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (err) => {
        console.warn('WebSocket error:', err);
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Aggregated KPIs
  const totalBeds = beds.length || 44;
  const occupiedBeds = beds.filter((b) => b.status === 'occupied').length;
  const overallOccupancyPct = totalBeds > 0 ? Math.round((occupiedBeds / totalBeds) * 100) : 0;
  const criticalInQueue = waitingPatients.filter((p) => p.severity === 'critical').length;
  const freeDiagnosticsCount = diagnostics.filter((d) => d.status === 'free').length;
  const totalDiagnosticsCount = diagnostics.length || 8;
  const onDutyStaffCount = staff.filter((s) => s.status === 'on_duty' || s.status === 'reassigned').length;

  // Prepare chart data for 2-hour forecasts
  const forecastChartData = Object.keys(forecasts).map((deptId) => {
    const fc = forecasts[deptId];
    return {
      department: fc.department_name.replace('Emergency Room (ER)', 'ER').replace('Intensive Care Unit (ICU)', 'ICU'),
      predicted: fc.predicted_count,
      ci_lower: fc.ci_lower,
      ci_upper: fc.ci_upper,
    };
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6">
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl text-white shadow-lg shadow-cyan-900/40">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-black tracking-tight text-white flex items-center gap-2">
                ADMINISTRATION DASHBOARD
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  v2.0 Orchestrator
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Load-Aware Staff Allocation • Dynamic Surge Rebalancing • 2-Hour Demand Forecasting • Bed & Diagnostic Orchestration
              </p>
            </div>
          </div>
        </div>

        {/* Status Indicators & Navigation */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-1.5 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
            {wsConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">WS LIVE</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
                <span className="text-rose-400 font-semibold">CONNECTING</span>
              </>
            )}
          </div>
          <div className="flex items-center space-x-1.5 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>{lastUpdate.toLocaleTimeString()}</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-1.5 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 px-3 py-1.5 rounded-lg transition font-sans text-xs font-semibold"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* KPI Ribbon */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        {/* Total Bed Occupancy */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Bed Occupancy</span>
            <BedDouble className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-slate-100">{overallOccupancyPct}%</span>
            <span className="text-xs text-slate-400 font-mono">
              {occupiedBeds}/{totalBeds} Beds
            </span>
          </div>
          <div className="w-full bg-slate-800 h-1 rounded-full mt-2 overflow-hidden">
            <div
              className={`h-full ${
                overallOccupancyPct > 80 ? 'bg-rose-500' : overallOccupancyPct > 55 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${overallOccupancyPct}%` }}
            />
          </div>
        </div>

        {/* Triage Waiting Queue */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Triage Queue</span>
            <Users className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-slate-100">{waitingPatients.length}</span>
            <span className="text-xs text-slate-400">In Triage</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Acuity-ranked FIFO dispatch</p>
        </div>

        {/* Critical Cases in Queue */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Critical (ESI 1)</span>
            <AlertOctagon className={`w-4 h-4 ${criticalInQueue > 0 ? 'text-rose-500 animate-bounce' : 'text-slate-500'}`} />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className={`text-2xl font-black ${criticalInQueue > 0 ? 'text-rose-400' : 'text-slate-100'}`}>
              {criticalInQueue}
            </span>
            <span className="text-xs text-slate-400">High Priority</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Auto-overflow eligible</p>
        </div>

        {/* Free Diagnostic Facilities */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Diagnostics Free</span>
            <Stethoscope className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-emerald-300">
              {freeDiagnosticsCount}/{totalDiagnosticsCount}
            </span>
            <span className="text-xs text-slate-400">Available</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">CT, X-Ray, Ultrasound, ECG</p>
        </div>

        {/* On-Duty Clinical Staff */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Clinical Staff</span>
            <Users className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-indigo-300">
              {onDutyStaffCount}/{staff.length || 27}
            </span>
            <span className="text-xs text-slate-400 font-mono">On Duty</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Protected ICU • Auto Rebalance</p>
        </div>
      </section>

      {/* Surge Alert & Interactive Simulation Controls */}
      <SurgeAlert
        criticalAlert={criticalAlert}
        isSimRunning={isSimRunning}
        onResetSuccess={loadInitialData}
        onSurgeSuccess={loadInitialData}
      />

      {/* Control Split: Patient Intake Form & 2-Hour Demand Forecast Strip */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Patient Intake Form (5 cols) */}
        <div className="lg:col-span-5">
          <PatientIntakeForm
            departments={departments.filter((d) => d.total_beds > 0)}
            onIntakeSuccess={loadInitialData}
          />
        </div>

        {/* Right: 2-Hour Demand Forecast Chart Strip (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <h3 className="font-bold text-slate-200 text-sm">2-Hour Inpatient Demand Forecast</h3>
            </div>
            <span className="text-xs text-slate-400">Seasonality Adjusted (80% CI)</span>
          </div>

          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={forecastChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="department" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                  labelStyle={{ color: '#f8fafc', fontWeight: 'bold' }}
                />
                <Bar dataKey="predicted" fill="#38bdf8" radius={[4, 4, 0, 0]}>
                  {forecastChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#f43f5e' : index === 2 ? '#a855f7' : '#0284c7'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Staff Roster Panel */}
      <section>
        <StaffPanel staff={staff} departments={departments} />
      </section>

      {/* Main Grid: Bed Map and Patient Queue + Event Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-4">
          <BedMap departments={departments.filter((d) => d.total_beds > 0)} beds={beds} diagnostics={diagnostics} />
        </div>
        <div className="lg:col-span-5 space-y-6">
          <div className="h-[280px]">
            <PatientQueue waitingPatients={waitingPatients} />
          </div>
          <div className="h-[360px]">
            <EventFeed events={events} />
          </div>
        </div>
      </div>
    </div>
  );
}
