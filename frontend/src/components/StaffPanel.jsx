import React from 'react';
import { Users, UserCheck, ArrowRightLeft, Activity, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function StaffPanel({ staff = [], departments = [] }) {
  // Total on-duty and busy counts
  const onDutyCount = staff.filter((s) => s.status === 'on_duty' || s.status === 'reassigned').length;
  const busyCount = staff.filter((s) => s.is_busy && s.status !== 'off_duty').length;
  const reassignedCount = staff.filter((s) => s.status === 'reassigned').length;

  return (
    <div className="bg-slate-900/85 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <Users className="w-4 h-4 text-indigo-400" />
          <h3 className="font-bold text-slate-100 text-sm">Clinical Staff & Duty Roster</h3>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          {reassignedCount > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-bold bg-amber-950/80 text-amber-300 border border-amber-600/80 animate-pulse text-[10px]">
              <ArrowRightLeft className="w-3 h-3" />
              {reassignedCount} Reassigned
            </span>
          )}
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-950/80 text-blue-300 border border-blue-800/80">
            {busyCount} Busy
          </span>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80">
            {onDutyCount}/{staff.length} On Duty
          </span>
        </div>
      </div>

      {/* Department Staff Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {departments.map((dept) => {
          const deptStaff = staff.filter((s) => s.department_id === dept.department_id);
          const deptOnDuty = deptStaff.filter((s) => s.status === 'on_duty' || s.status === 'reassigned');

          return (
            <div
              key={dept.department_id}
              className="bg-slate-950/70 border border-slate-800/90 rounded-lg p-3 flex flex-col justify-between"
            >
              {/* Department Title */}
              <div className="flex items-center justify-between border-b border-slate-800/60 pb-2 mb-2">
                <span className="text-xs font-bold text-slate-200 truncate">
                  {dept.name.replace('Emergency Room (ER)', 'ER').replace('Intensive Care Unit (ICU)', 'ICU')}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {deptOnDuty.length} Active
                </span>
              </div>

              {/* Staff Badges with 3 distinct visual states: Reassigned (amber), Busy (blue), Free (green) */}
              <div className="space-y-1.5 min-h-[90px]">
                {deptStaff.length === 0 ? (
                  <div className="text-[11px] text-slate-500 italic py-2 text-center">
                    No staff stationed
                  </div>
                ) : (
                  deptStaff.map((member) => {
                    const isReassigned = member.status === 'reassigned';
                    const isBusy = member.is_busy && !isReassigned;

                    let containerStyle = 'bg-emerald-950/40 border-emerald-700/50 text-emerald-200 hover:border-emerald-600';
                    let icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />;
                    let tag = (
                      <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        FREE
                      </span>
                    );

                    if (isReassigned) {
                      containerStyle = 'bg-amber-950/70 border-amber-500/80 text-amber-200 shadow-[0_0_8px_rgba(245,158,11,0.25)] animate-pulse';
                      icon = <ArrowRightLeft className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />;
                      tag = (
                        <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          REALLOCATED
                        </span>
                      );
                    } else if (isBusy) {
                      containerStyle = 'bg-blue-950/70 border-blue-600/70 text-blue-200 shadow-[0_0_6px_rgba(59,130,246,0.2)]';
                      icon = <Activity className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />;
                      tag = (
                        <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40">
                          {member.active_patients} {member.active_patients === 1 ? 'PT' : 'PTS'}
                        </span>
                      );
                    } else if (member.status === 'off_duty') {
                      containerStyle = 'bg-slate-900/40 border-slate-800/50 text-slate-500';
                      icon = <Users className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />;
                      tag = <span className="text-[9px] uppercase text-slate-500">OFF DUTY</span>;
                    }

                    return (
                      <div
                        key={member.staff_id}
                        className={`flex items-center justify-between px-2 py-1.5 rounded text-xs transition border ${containerStyle}`}
                      >
                        <div className="flex items-center space-x-1.5 truncate">
                          {icon}
                          <span className="font-medium text-[11px] truncate">
                            {member.role}
                            {isBusy && (
                              <span className="ml-1 text-[10px] text-blue-300/80 font-mono">
                                ({member.active_patients} {member.active_patients === 1 ? 'pt' : 'pts'})
                              </span>
                            )}
                          </span>
                        </div>

                        <div className="flex items-center space-x-1 flex-shrink-0">
                          {tag}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
