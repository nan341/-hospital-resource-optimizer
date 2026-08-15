import React from 'react';
import {
  Activity,
  UserPlus,
  CheckCircle,
  GitBranch,
  Stethoscope,
  Users,
  ShieldAlert,
  Zap,
  LogOut,
  Radio
} from 'lucide-react';

export default function EventFeed({ events = [] }) {
  const getEventBadge = (eventType) => {
    switch (eventType) {
      case 'surge_triggered':
        return {
          icon: <Zap className="w-3.5 h-3.5 text-rose-400 fill-current" />,
          bg: 'bg-rose-950/60 border-rose-600/70 text-rose-300',
          tag: 'SURGE'
        };
      case 'critical_no_capacity':
        return {
          icon: <ShieldAlert className="w-3.5 h-3.5 text-rose-400 animate-bounce" />,
          bg: 'bg-rose-950/80 border-rose-500 text-rose-200',
          tag: 'CAPACITY ALERT'
        };
      case 'overflow_assigned':
        return {
          icon: <GitBranch className="w-3.5 h-3.5 text-amber-400" />,
          bg: 'bg-amber-950/60 border-amber-600/70 text-amber-300',
          tag: 'OVERFLOW ROUTING'
        };
      case 'bed_assigned':
        return {
          icon: <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />,
          bg: 'bg-emerald-950/40 border-emerald-700/50 text-emerald-300',
          tag: 'BED ASSIGNED'
        };
      case 'diagnostic_assigned':
        return {
          icon: <Stethoscope className="w-3.5 h-3.5 text-cyan-400" />,
          bg: 'bg-cyan-950/40 border-cyan-700/50 text-cyan-300',
          tag: 'DIAGNOSTIC'
        };
      case 'diagnostic_released':
        return {
          icon: <Stethoscope className="w-3.5 h-3.5 text-teal-400" />,
          bg: 'bg-teal-950/40 border-teal-700/50 text-teal-300',
          tag: 'DIAG FREE'
        };
      case 'staff_reassigned':
        return {
          icon: <Users className="w-3.5 h-3.5 text-indigo-400" />,
          bg: 'bg-indigo-950/50 border-indigo-700/50 text-indigo-300',
          tag: 'STAFF REBALANCE'
        };
      case 'patient_discharged':
        return {
          icon: <LogOut className="w-3.5 h-3.5 text-emerald-400" />,
          bg: 'bg-emerald-950/30 border-emerald-800/40 text-emerald-400',
          tag: 'DISCHARGE'
        };
      case 'patient_arrival':
        return {
          icon: <UserPlus className="w-3.5 h-3.5 text-blue-400" />,
          bg: 'bg-blue-950/40 border-blue-700/50 text-blue-300',
          tag: 'ARRIVAL'
        };
      default:
        return {
          icon: <Activity className="w-3.5 h-3.5 text-slate-400" />,
          bg: 'bg-slate-900 border-slate-700 text-slate-300',
          tag: 'SYSTEM'
        };
    }
  };

  const formatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="bg-slate-900/85 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-full">
      {/* Header with live pulsing dot */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
          <h3 className="font-bold text-slate-100 text-sm">Real-Time Allocation Decisions</h3>
        </div>
        <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          Live WebSocket Stream
        </span>
      </div>

      {/* Scrolling Events Feed */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[460px]">
        {events.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No events logged yet. Start simulation to observe live decisions.
          </div>
        ) : (
          events.map((event) => {
            const badge = getEventBadge(event.event_type);
            return (
              <div
                key={event.event_id || `${event.timestamp}-${Math.random()}`}
                className={`p-2.5 rounded-lg border text-xs transition-all duration-300 ${badge.bg}`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-slate-950/60 border border-slate-700">
                    {badge.icon}
                    {badge.tag}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {formatTime(event.timestamp)}
                  </span>
                </div>
                <p className="text-slate-200 text-xs leading-relaxed font-sans break-words">
                  {event.description}
                </p>
                {event.triggered_by && (
                  <div className="text-[9px] text-slate-400 mt-1 flex items-center justify-end gap-1">
                    <span className="opacity-60">Source:</span>
                    <span className="font-mono text-cyan-300/80">{event.triggered_by}</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
