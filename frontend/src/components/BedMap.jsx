import React, { useState } from 'react';
import { BedDouble, Activity, Stethoscope, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export default function BedMap({ departments = [], beds = [], diagnostics = [] }) {
  const [selectedBed, setSelectedBed] = useState(null);

  // Status styling map
  const getStatusColor = (status) => {
    switch (status) {
      case 'available':
        return {
          bg: 'bg-emerald-950/40 hover:bg-emerald-900/60',
          border: 'border-emerald-500/40 text-emerald-300',
          badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
          dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]'
        };
      case 'occupied':
        return {
          bg: 'bg-rose-950/40 hover:bg-rose-900/60',
          border: 'border-rose-500/50 text-rose-200',
          badge: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
          dot: 'bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.8)]'
        };
      case 'cleaning':
        return {
          bg: 'bg-amber-950/40 hover:bg-amber-900/60',
          border: 'border-amber-500/40 text-amber-300',
          badge: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
          dot: 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]'
        };
      default:
        return {
          bg: 'bg-slate-900/40 hover:bg-slate-800/60',
          border: 'border-slate-700 text-slate-300',
          badge: 'bg-slate-700/40 text-slate-300 border-slate-600',
          dot: 'bg-slate-400'
        };
    }
  };

  return (
    <div className="space-y-4">
      {/* Legend & Summary Ribbon */}
      <div className="flex items-center justify-between bg-slate-900/70 border border-slate-800/80 px-4 py-2.5 rounded-xl text-xs">
        <div className="flex items-center space-x-4">
          <span className="text-slate-400 font-medium">Bed Status:</span>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            <span className="text-emerald-300">Available</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-400"></span>
            <span className="text-rose-300">Occupied</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span className="text-amber-300">Cleaning</span>
          </div>
        </div>
        <div className="text-slate-400">
          Total Beds: <span className="font-semibold text-slate-200">{beds.length}</span>
        </div>
      </div>

      {/* Department Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {departments.map((dept) => {
          const deptBeds = beds.filter((b) => b.department_id === dept.department_id);
          const deptDiags = diagnostics.filter((d) => d.department_id === dept.department_id);
          const freeDiags = deptDiags.filter((d) => d.status === 'free').length;
          const occupiedCount = deptBeds.filter((b) => b.status === 'occupied').length;
          const occupancyPct = dept.total_beds > 0 ? Math.round((occupiedCount / dept.total_beds) * 100) : 0;

          return (
            <div
              key={dept.department_id}
              className="bg-slate-900/85 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between"
            >
              {/* Header: Dept Name, Occupancy Bar & Diagnostic Facility Free Badge */}
              <div className="border-b border-slate-800 pb-3 mb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                      <BedDouble className="w-4 h-4 text-cyan-400" />
                      {dept.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Capacity: {occupiedCount}/{dept.total_beds} beds occupied ({occupancyPct}%)
                    </p>
                  </div>

                  {/* Diagnostic Facility Status Badge (Phase 6 requirement) */}
                  <div className="flex flex-col items-end">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                        freeDiags > 0
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700/60'
                          : 'bg-rose-950/60 text-rose-300 border-rose-700/60'
                      }`}
                      title={deptDiags.map((d) => `${d.type}: ${d.status}`).join('\n')}
                    >
                      <Stethoscope className="w-3.5 h-3.5" />
                      {freeDiags}/{deptDiags.length || 2} Diagnostics Free
                    </span>
                    <span className="text-[10px] text-slate-500 mt-0.5">
                      {dept.on_duty_staff || dept.total_staff_slots} Staff on Duty
                    </span>
                  </div>
                </div>

                {/* Occupancy Progress Bar */}
                <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      occupancyPct > 85 ? 'bg-rose-500' : occupancyPct > 60 ? 'bg-amber-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, occupancyPct)}%` }}
                  />
                </div>
              </div>

              {/* Bed Grid */}
              <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-4 lg:grid-cols-5 gap-2 my-2">
                {deptBeds.map((bed) => {
                  const style = getStatusColor(bed.status);
                  const isSelected = selectedBed?.bed_id === bed.bed_id;

                  return (
                    <button
                      key={bed.bed_id}
                      onClick={() => setSelectedBed(isSelected ? null : bed)}
                      className={`relative flex flex-col items-center justify-center p-2 rounded-lg border text-center transition-all ${
                        style.bg
                      } ${style.border} ${isSelected ? 'ring-2 ring-cyan-400 scale-105' : ''}`}
                    >
                      <div className="flex items-center justify-between w-full mb-1">
                        <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                        <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold">
                          {bed.bed_id.split('-').pop()}
                        </span>
                      </div>
                      <span className="text-xs font-bold leading-tight truncate w-full">
                        {bed.status === 'occupied' ? (
                          <span className="text-rose-300 font-mono text-[11px]">{bed.current_patient_id || 'OCCUPIED'}</span>
                        ) : (
                          <span className="text-emerald-400 font-medium text-[11px]">FREE</span>
                        )}
                      </span>
                      <span className="text-[9px] text-slate-400 capitalize mt-0.5 truncate w-full">
                        {bed.bed_type}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Selected Bed Quick Drawer / Tooltip Info */}
              {selectedBed && deptBeds.some((b) => b.bed_id === selectedBed.bed_id) && (
                <div className="mt-3 p-2.5 bg-slate-950/80 border border-slate-700/70 rounded-lg text-xs flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-cyan-300">{selectedBed.bed_id}</span>
                    <span className="text-slate-400 ml-2">Type: {selectedBed.bed_type}</span>
                    {selectedBed.current_patient_id && (
                      <span className="ml-2 text-rose-300">Patient: {selectedBed.current_patient_id}</span>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${getStatusColor(selectedBed.status).badge}`}>
                    {selectedBed.status}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
