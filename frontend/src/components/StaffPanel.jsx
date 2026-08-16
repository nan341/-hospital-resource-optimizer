import React from 'react';
import { Users, UserCheck, ArrowRightLeft, Clock, ShieldCheck } from 'lucide-react';

export default function StaffPanel({ staff = [], departments = [] }) {
  // Total on-duty count
  const onDutyCount = staff.filter((s) => s.status === 'on_duty' || s.status === 'reassigned').length;
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

              {/* Staff Badges */}
              <div className="space-y-1.5 min-h-[90px]">
                {deptStaff.length === 0 ? (
                  <div className="text-[11px] text-slate-500 italic py-2 text-center">
                    No staff stationed
                  </div>
                ) : (
                  deptStaff.map((member) => {
                    const isReassigned = member.status === 'reassigned';
                    return (
                      <div
                        key={member.staff_id}
                        className={`flex items-center justify-between px-2 py-1.5 rounded text-xs transition border ${
                          isReassigned
                            ? 'bg-amber-950/70 border-amber-500/80 text-amber-200 shadow-[0_0_8px_rgba(245,158,11,0.25)] animate-pulse'
                            : member.status === 'on_duty'
                            ? 'bg-slate-900/90 border-slate-800 text-slate-200 hover:border-slate-700'
                            : 'bg-slate-900/40 border-slate-800/50 text-slate-500'
                        }`}
                      >
                        <div className="flex items-center space-x-1.5 truncate">
                          {isReassigned ? (
                            <ArrowRightLeft className="w-3 h-3 text-amber-400 flex-shrink-0" />
                          ) : (
                            <UserCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                          )}
                          <span className="font-medium text-[11px] truncate">
                            {member.role}
                          </span>
                        </div>

                        <div className="flex items-center space-x-1 flex-shrink-0">
                          {isReassigned ? (
                            <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                              REALLOCATED
                            </span>
                          ) : (
                            <span className="text-[9px] font-mono text-slate-400">
                              {member.shift_start}-{member.shift_end}
                            </span>
                          )}
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
