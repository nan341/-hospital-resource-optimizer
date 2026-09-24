import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Filter,
  RefreshCw,
  User,
  Calendar,
  Building,
  Activity,
  ChevronRight,
  X,
  History,
  BookOpen,
  Stethoscope,
  BedDouble,
  Clock,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ArrowRightLeft
} from 'lucide-react';
import {
  getDepartments,
  getPatients,
  getAdminAppointments,
  getPatientCaseLog,
  getAppointmentCaseLog
} from '../api';

export default function AdminCaseLogs() {
  const token = sessionStorage.getItem('admin_token');

  const [departments, setDepartments] = useState([]);
  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState('all'); // 'all' | 'inpatient' | 'outpatient'
  const [selectedDept, setSelectedDept] = useState('all'); // 'all' | department_id
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Modal Case Log State
  const [selectedCase, setSelectedCase] = useState(null); // { type: 'patient' | 'appointment', id: string, name: string }
  const [caseDetails, setCaseDetails] = useState(null);
  const [caseLoading, setCaseLoading] = useState(false);
  const [caseError, setCaseError] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [deptsRes, ptsRes, aptsRes] = await Promise.all([
        getDepartments(token).catch(() => ({ data: [] })),
        getPatients(undefined, token).catch(() => ({ data: [] })),
        getAdminAppointments(undefined, token).catch(() => ({ data: [] }))
      ]);
      setDepartments(deptsRes.data || []);
      setPatients(ptsRes.data || []);
      setAppointments(aptsRes.data || []);
    } catch (err) {
      console.error('Error fetching admin case log data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  const getDeptName = (deptId) => {
    if (!deptId) return 'General';
    const d = departments.find((dept) => dept.department_id === deptId);
    return d ? d.name : deptId.toUpperCase();
  };

  const handleOpenCase = async (type, id, name) => {
    // Determine type strictly: 'patient' vs 'appointment'
    const isPatient = type === 'patient' || (typeof id === 'string' && id.startsWith('PAT-'));
    const resolvedType = isPatient ? 'patient' : 'appointment';

    setSelectedCase({ type: resolvedType, id, name });
    setCaseLoading(true);
    setCaseError(null);
    setCaseDetails(null);
    try {
      const res = isPatient
        ? await getPatientCaseLog(id, undefined, token)
        : await getAppointmentCaseLog(id, undefined, token);
      setCaseDetails(res.data);
    } catch (err) {
      setCaseError(err.response?.data?.detail || 'Failed to load case log timeline.');
    } finally {
      setCaseLoading(false);
    }
  };

  // Combine & Map records with explicit type discriminators
  const allRecords = [
    ...patients.map((p) => {
      const isOverflow = Boolean(
        p.is_overflow ||
        (p.assigned_bed_department && p.assigned_bed_department !== p.department_needed)
      );
      return {
        recordType: 'patient', // Explicit 'patient' discriminator
        id: p.patient_id,
        name: p.name || p.patient_id,
        age: p.age,
        reason: p.reason_for_visit,
        department_needed: p.department_needed, // ORIGINALLY REQUESTED department
        department: getDeptName(p.department_needed),
        assigned_bed_id: p.assigned_bed_id,
        assigned_bed_department: p.assigned_bed_department,
        is_overflow: isOverflow,
        doctor: p.assigned_doctor_name || p.assigned_staff_id,
        nurse: p.assigned_nurse_name,
        status: p.status,
        severity: p.severity,
        time: p.arrival_time
      };
    }),
    ...appointments.map((a) => ({
      recordType: 'appointment', // Explicit 'appointment' discriminator
      id: a.appointment_id,
      name: a.patient_name,
      age: a.patient_age,
      reason: a.reason_for_visit,
      department_needed: a.department_id,
      department: a.department_name || getDeptName(a.department_id),
      assigned_bed_id: null,
      assigned_bed_department: null,
      is_overflow: false,
      doctor: a.doctor_name,
      nurse: null,
      status: a.status,
      severity: null,
      time: a.scheduled_time
    }))
  ];

  // Filtering: Type, Department (Requested Ward), and Search query
  const filteredRecords = allRecords.filter((rec) => {
    // 1. Type Filter
    if (filterType === 'inpatient' && rec.recordType !== 'patient') return false;
    if (filterType === 'outpatient' && rec.recordType !== 'appointment') return false;

    // 2. Department Filter: Must match Patient.department_needed (Requested department, NOT bed location)
    if (selectedDept !== 'all' && rec.department_needed !== selectedDept) {
      return false;
    }

    // 3. Search Query Filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = (rec.name || '').toLowerCase().includes(q);
      const matchId = (rec.id || '').toLowerCase().includes(q);
      const matchDept = (rec.department || '').toLowerCase().includes(q);
      const matchDoctor = (rec.doctor || '').toLowerCase().includes(q);
      const matchReason = (rec.reason || '').toLowerCase().includes(q);
      return matchName || matchId || matchDept || matchDoctor || matchReason;
    }
    return true;
  });

  // Calculate True Requested Demand vs Physical Bed Occupancy metrics per inpatient department
  const inpatientDepts = departments.filter((d) => d.total_beds > 0);
  const overflowedPatientsCount = patients.filter(
    (p) => p.is_overflow || (p.assigned_bed_department && p.assigned_bed_department !== p.department_needed)
  ).length;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3.5">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-100 text-sm md:text-base flex items-center gap-2">
              Patient & Appointment Case Logs
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                Audited Timeline
              </span>
              {overflowedPatientsCount > 0 && (
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  {overflowedPatientsCount} Overflow Active
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400">
              Browse consolidated clinical notes, doctor assessments, and historical events categorized by originally requested department
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="self-start sm:self-auto flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold rounded-xl transition border border-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* True Demand vs Bed Occupancy Ribbon */}
      {inpatientDepts.length > 0 && (
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          {inpatientDepts.map((d) => {
            const requestedCount = patients.filter((p) => p.department_needed === d.department_id && p.status !== 'discharged').length;
            const physicalOccupancy = d.occupied_beds;
            const hasOverflowDemand = requestedCount > physicalOccupancy;
            return (
              <div key={d.department_id} className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-300 text-[11px] truncate">{d.name}</span>
                  {hasOverflowDemand && (
                    <span className="text-[9px] font-bold text-amber-400 bg-amber-950 px-1.5 py-0.2 rounded border border-amber-800">
                      Surge
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-baseline justify-between text-[11px]">
                  <span className="text-slate-400">Requested Demand:</span>
                  <span className={`font-bold font-mono ${hasOverflowDemand ? 'text-amber-300' : 'text-slate-200'}`}>
                    {requestedCount}
                  </span>
                </div>
                <div className="flex items-baseline justify-between text-[11px]">
                  <span className="text-slate-500">Physical Beds:</span>
                  <span className="font-mono text-slate-400">{physicalOccupancy}/{d.total_beds}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Filter Pills */}
          <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setFilterType('all')}
              className={`px-3 py-1 rounded-lg transition ${
                filterType === 'all'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Cases ({allRecords.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterType('inpatient')}
              className={`px-3 py-1 rounded-lg transition ${
                filterType === 'inpatient'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Inpatients ({patients.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterType('outpatient')}
              className={`px-3 py-1 rounded-lg transition ${
                filterType === 'outpatient'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Outpatients ({appointments.length})
            </button>
          </div>

          {/* Department / Ward Filter Dropdown */}
          <div className="flex items-center space-x-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
            <Building className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer pr-1"
            >
              <option value="all" className="bg-slate-950 text-slate-200">
                All Requested Departments
              </option>
              {departments.map((d) => (
                <option key={d.department_id} value={d.department_id} className="bg-slate-950 text-slate-200">
                  {d.name} {d.total_beds > 0 ? '(Inpatient)' : '(Outpatient)'}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative flex-1 lg:max-w-xs">
          <input
            type="text"
            placeholder="Search patient, ID, doctor..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-1.5 pl-9 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-2 text-slate-500 hover:text-slate-300"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Records Table / Cards */}
      <div className="max-h-96 overflow-y-auto border border-slate-800/80 rounded-xl overflow-hidden">
        {filteredRecords.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs italic bg-slate-950/40">
            No matching patient or appointment case records found for this filter.
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3.5">Record / ID</th>
                <th className="py-2.5 px-3.5">Patient Name</th>
                <th className="py-2.5 px-3.5">Requested Dept</th>
                <th className="py-2.5 px-3.5">Care Team</th>
                <th className="py-2.5 px-3.5">Status</th>
                <th className="py-2.5 px-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 bg-slate-950/30">
              {filteredRecords.map((rec) => (
                <tr
                  key={rec.id}
                  className="hover:bg-slate-800/30 transition group cursor-pointer"
                  onClick={() => handleOpenCase(rec.recordType, rec.id, rec.name)}
                >
                  <td className="py-3 px-3.5 font-mono">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                          rec.recordType === 'patient'
                            ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                            : 'bg-purple-950 text-purple-300 border border-purple-800'
                        }`}
                      >
                        {rec.recordType}
                      </span>
                      <span className="text-slate-300 font-medium">{rec.id}</span>
                    </div>
                  </td>

                  <td className="py-3 px-3.5">
                    <div className="font-semibold text-slate-100">{rec.name}</div>
                    {rec.age !== null && rec.age !== undefined && (
                      <div className="text-[10px] text-slate-400">{rec.age} yrs • {rec.reason || 'Clinical consultation'}</div>
                    )}
                  </td>

                  <td className="py-3 px-3.5 text-slate-300">
                    <div className="flex items-center space-x-1 font-medium">
                      <Building className="w-3 h-3 text-slate-500" />
                      <span>{rec.department}</span>
                    </div>
                    {/* Overflow Tag */}
                    {rec.is_overflow && (
                      <div className="mt-1 flex items-center gap-1 text-[9px] font-bold text-amber-300 bg-amber-950/80 border border-amber-700/80 px-1.5 py-0.5 rounded">
                        <AlertTriangle className="w-2.5 h-2.5 text-amber-400 flex-shrink-0" />
                        <span>Req: {getDeptName(rec.department_needed)} → Bed: {getDeptName(rec.assigned_bed_department)} (Overflow)</span>
                      </div>
                    )}
                  </td>

                  <td className="py-3 px-3.5 text-slate-300 text-[11px]">
                    {rec.doctor ? (
                      <div>
                        <span className="text-slate-400">Doc:</span> {rec.doctor}
                      </div>
                    ) : (
                      <span className="text-slate-500 italic">Unassigned</span>
                    )}
                    {rec.nurse && (
                      <div className="text-slate-400">
                        <span className="text-slate-500">Nurse:</span> {rec.nurse}
                      </div>
                    )}
                  </td>

                  <td className="py-3 px-3.5">
                    <span
                      className={`inline-block text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                        rec.status === 'admitted' || rec.status === 'in_consultation'
                          ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                          : rec.status === 'waiting' || rec.status === 'scheduled'
                          ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
                          : rec.status === 'completed' || rec.status === 'discharged'
                          ? 'bg-slate-800 text-slate-300 border-slate-700'
                          : 'bg-rose-950 text-rose-300 border-rose-700'
                      }`}
                    >
                      {(rec.status ?? '').replace(/_/g, ' ')}
                    </span>
                  </td>

                  <td className="py-3 px-3.5 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenCase(rec.recordType, rec.id, rec.name);
                      }}
                      className="px-2.5 py-1 bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-700/60 text-indigo-200 text-xs font-semibold rounded-lg transition inline-flex items-center space-x-1"
                    >
                      <FileText className="w-3 h-3 text-indigo-400" />
                      <span>Case Log</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* CASE LOG TIMELINE MODAL */}
      {selectedCase && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span>Clinical Case Log: {selectedCase.name}</span>
                    <span className="text-xs font-mono font-normal text-slate-400">({selectedCase.id})</span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    {selectedCase.type === 'patient' || selectedCase.id?.startsWith('PAT-')
                      ? 'Inpatient Clinical History & Bed Allocation'
                      : 'Outpatient Consultation & Queue Log'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {caseError && (
                <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 rounded-xl text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{caseError}</span>
                </div>
              )}

              {/* Overflow Placement Banner in Modal */}
              {caseDetails?.is_overflow && (
                <div className="p-3 bg-amber-950/80 border border-amber-600/80 text-amber-200 rounded-xl text-xs flex items-center space-x-2.5 shadow-md">
                  <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                  <div>
                    <span className="font-bold uppercase tracking-wider text-[11px] block text-amber-300">
                      Surge Overflow Diversion
                    </span>
                    <span className="text-slate-200">
                      Patient originally requested <span className="font-bold text-white">{caseDetails.department_name || getDeptName(caseDetails.department_id)}</span> and was overflow-allocated to Bed <span className="font-mono text-cyan-300 font-bold">{caseDetails.assigned_bed_id}</span> in <span className="font-bold text-white">{caseDetails.assigned_bed_department_name || getDeptName(caseDetails.assigned_bed_department)}</span>.
                    </span>
                  </div>
                </div>
              )}

              {caseDetails && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="block text-slate-500 text-[10px] uppercase font-semibold">Requested Dept</span>
                    <span className="font-semibold text-slate-200">{caseDetails.department_name || caseDetails.department_id}</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 text-[10px] uppercase font-semibold">Assigned Doctor</span>
                    <span className="font-semibold text-slate-200">
                      {caseDetails.assigned_doctor_name || caseDetails.doctor_name || 'None'}
                    </span>
                  </div>
                  <div>
                    <span className="block text-slate-500 text-[10px] uppercase font-semibold">
                      {(selectedCase.type === 'patient' || selectedCase.id?.startsWith('PAT-')) ? 'Bed / Location' : 'Room / Floor'}
                    </span>
                    <span className="font-semibold text-slate-200">
                      {(selectedCase.type === 'patient' || selectedCase.id?.startsWith('PAT-'))
                        ? `${caseDetails.assigned_bed_id || 'Triage'} (${caseDetails.assigned_bed_department_name || caseDetails.department_name || 'Unit'})`
                        : `${caseDetails.room_number || 'Room 101'} (${caseDetails.floor || '1st Fl'})`}
                    </span>
                  </div>
                  <div>
                    <span className="block text-slate-500 text-[10px] uppercase font-semibold">Status</span>
                    <span className="font-bold text-indigo-300 uppercase">{caseDetails.status}</span>
                  </div>
                </div>
              )}

              {/* TIMELINE */}
              <div>
                <div className="flex items-center space-x-2 text-xs font-bold text-slate-200 mb-4">
                  <History className="w-4 h-4 text-cyan-400" />
                  <span>Chronological Case Timeline & Clinical Notes</span>
                </div>

                {caseLoading ? (
                  <div className="py-12 text-center text-xs text-slate-400 space-y-2">
                    <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto" />
                    <p>Loading clinical case history...</p>
                  </div>
                ) : !caseDetails || (caseDetails.timeline || []).length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500 italic bg-slate-950/40 rounded-xl border border-slate-800/60">
                    No clinical events or notes logged for this case.
                  </div>
                ) : (
                  <div className="relative pl-6 space-y-4 border-l border-slate-800">
                    {caseDetails.timeline.map((item, idx) => {
                      const isNote = item.type === 'note' || item.type === 'clinical_note';
                      return (
                        <div key={idx} className="relative group">
                          {/* Dot */}
                          <div
                            className={`absolute -left-[31px] top-1.5 w-3 h-3 rounded-full border-2 border-slate-900 ${
                              isNote
                                ? item.note_type === 'discharge_summary'
                                  ? 'bg-emerald-400'
                                  : 'bg-indigo-400'
                                : 'bg-cyan-500'
                            }`}
                          />

                          <div
                            className={`p-3.5 rounded-xl border text-xs space-y-1.5 transition ${
                              isNote
                                ? item.note_type === 'discharge_summary'
                                  ? 'bg-emerald-950/30 border-emerald-700/50 text-slate-200'
                                  : 'bg-indigo-950/30 border-indigo-700/50 text-slate-200'
                                : 'bg-slate-950/60 border-slate-800/80 text-slate-300'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span
                                className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                                  isNote
                                    ? item.note_type === 'discharge_summary'
                                      ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/60'
                                      : 'bg-indigo-900/60 text-indigo-300 border border-indigo-700/60'
                                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                                }`}
                              >
                                {isNote
                                  ? (item.note_type ?? 'clinical_note').replace(/_/g, ' ')
                                  : (item.event_type ?? 'event').replace(/_/g, ' ')}
                              </span>
                              <span className="text-[10px] font-mono text-slate-500">
                                {item.timestamp ? new Date(item.timestamp).toLocaleString() : ''}
                              </span>
                            </div>

                            <p className="text-xs leading-relaxed">
                              {isNote ? item.content : item.description}
                            </p>

                            <div className="text-[10px] text-slate-500 font-medium">
                              {isNote ? (
                                <span>Author: {item.author_name || item.author_id || 'Clinician'}</span>
                              ) : (
                                <span>Triggered By: {item.triggered_by || item.author || 'System Engine'}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end">
              <button
                onClick={() => setSelectedCase(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition"
              >
                Close Case Log
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
