import React from 'react';
import { Users, Clock, Flame, AlertCircle, HeartPulse } from 'lucide-react';

export default function PatientQueue({ waitingPatients = [] }) {
  // Sort patients: critical first, then moderate, then low, then arrival time
  const severityRank = { critical: 1, moderate: 2, low: 3 };
  const sortedPatients = [...waitingPatients].sort((a, b) => {
    const rankDiff = (severityRank[a.severity] || 4) - (severityRank[b.severity] || 4);
    if (rankDiff !== 0) return rankDiff;
    return new Date(a.arrival_time) - new Date(b.arrival_time);
  });

  const getSeverityBadge = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return {
          badge: 'bg-rose-950/80 text-rose-300 border-rose-600/80',
          icon: <Flame className="w-3.5 h-3.5 text-rose-400 animate-pulse" />,
          label: 'CRITICAL (ESI 1)'
        };
      case 'moderate':
        return {
          badge: 'bg-amber-950/80 text-amber-300 border-amber-600/80',
          icon: <AlertCircle className="w-3.5 h-3.5 text-amber-400" />,
          label: 'MODERATE (ESI 3)'
        };
      default:
        return {
          badge: 'bg-emerald-950/80 text-emerald-300 border-emerald-600/80',
          icon: <HeartPulse className="w-3.5 h-3.5 text-emerald-400" />,
          label: 'LOW (ESI 5)'
        };
    }
  };

  const formatWaitTime = (arrivalIso) => {
    if (!arrivalIso) return '< 1m';
    const elapsedSecs = Math.max(0, Math.floor((new Date() - new Date(arrivalIso)) / 1000));
    if (elapsedSecs < 60) return `${elapsedSecs}s`;
    const mins = Math.floor(elapsedSecs / 60);
    return `${mins}m`;
  };

  return (
    <div className="bg-slate-900/85 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <Users className="w-4 h-4 text-cyan-400" />
          <h3 className="font-bold text-slate-100 text-sm">Triage Waiting Queue</h3>
        </div>
        <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800/80">
          {sortedPatients.length} Waiting
        </span>
      </div>

      {/* Queue List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[460px]">
        {sortedPatients.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-40" />
            No patients currently in queue. All admitted or treated.
          </div>
        ) : (
          sortedPatients.map((patient, index) => {
            const sev = getSeverityBadge(patient.severity);
            return (
              <div
                key={patient.patient_id}
                className="bg-slate-950/70 hover:bg-slate-950 border border-slate-800/90 rounded-lg p-2.5 transition flex items-center justify-between gap-3 text-xs"
              >
                {/* Left: Priority Rank + Patient ID */}
                <div className="flex items-center space-x-2.5 min-w-0">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300">
                    #{index + 1}
                  </span>
                  <div className="truncate">
                    <div className="font-mono font-bold text-slate-200 truncate">
                      {patient.patient_id}
                    </div>
                    <div className="text-[10px] text-slate-400 capitalize truncate">
                      Dept: {patient.department_needed.replace('_', ' ')}
                    </div>
                  </div>
                </div>

                {/* Right: Severity Badge + Stay & Wait Time */}
                <div className="flex flex-col items-end space-y-1 flex-shrink-0">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-bold ${sev.badge}`}>
                    {sev.icon}
                    {sev.label}
                  </span>
                  <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                    <span>Est: {patient.predicted_stay_hours}h</span>
                    <span>•</span>
                    <span className="text-cyan-300 font-mono">Wait: {formatWaitTime(patient.arrival_time)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
