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
  AlertCircle
} from 'lucide-react';
import {
  getPatients,
  getAdminAppointments,
  getPatientCaseLog,
  getAppointmentCaseLog
} from '../api';

export default function AdminCaseLogs() {
  const token = sessionStorage.getItem('admin_token');

  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState('all'); // 'all' | 'inpatient' | 'outpatient'
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Modal Case Log State
  const [selectedCase, setSelectedCase] = useState(null); // { type: 'patient' | 'appointment', id: string, name: string }
  const [caseDetails, setCaseDetails] = useState(null);
  const [caseLoading, setCaseLoading] = useState(false);
  const [caseError, setCaseError] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ptsRes, aptsRes] = await Promise.all([
        getPatients(undefined, token).catch(() => ({ data: [] })),
        getAdminAppointments(undefined, token).catch(() => ({ data: [] }))
      ]);
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

  const handleOpenCase = async (type, id, name) => {
    setSelectedCase({ type, id, name });
    setCaseLoading(true);
    setCaseError(null);
    setCaseDetails(null);
    try {
      const res = type === 'patient'
        ? await getPatientCaseLog(id, undefined, token)
        : await getAppointmentCaseLog(id, undefined, token);
      setCaseDetails(res.data);
    } catch (err) {
      setCaseError(err.response?.data?.detail || 'Failed to load case log timeline.');
    } finally {
      setCaseLoading(false);
    }
  };

  // Combine & Filter records
  const allRecords = [
    ...patients.map((p) => ({
      recordType: 'inpatient',
      id: p.patient_id,
      name: p.name || p.patient_id,
      age: p.age,
      reason: p.reason_for_visit,
      department: p.department_needed,
      doctor: p.assigned_doctor_name || p.assigned_staff_id,
      nurse: p.assigned_nurse_name,
      status: p.status,
      severity: p.severity,
      time: p.arrival_time
    })),
    ...appointments.map((a) => ({
      recordType: 'outpatient',
      id: a.appointment_id,
      name: a.patient_name,
      age: a.patient_age,
      reason: a.reason_for_visit,
      department: a.department_name,
      doctor: a.doctor_name,
      nurse: null,
      status: a.status,
      severity: null,
      time: a.scheduled_time
    }))
  ];

  const filteredRecords = allRecords.filter((rec) => {
    if (filterType === 'inpatient' && rec.recordType !== 'inpatient') return false;
    if (filterType === 'outpatient' && rec.recordType !== 'outpatient') return false;

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
            </h3>
            <p className="text-xs text-slate-400">
              Browse consolidated clinical notes, doctor assessments, and historical events across all departments
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

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Filter Pills */}
        <div className="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
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
            Inpatient Admissions ({patients.length})
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
            Outpatient Appointments ({appointments.length})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative flex-1 sm:max-w-xs">
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
            No matching patient or appointment case records found.
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3.5">Record / ID</th>
                <th className="py-2.5 px-3.5">Patient Name</th>
                <th className="py-2.5 px-3.5">Department</th>
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
                          rec.recordType === 'inpatient'
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
                      {rec.status.replace('_', ' ')}
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
                    {selectedCase.type === 'patient' ? 'Inpatient Clinical History & Bed Allocation' : 'Outpatient Consultation & Queue Log'}
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

              {caseDetails && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="block text-slate-500 text-[10px] uppercase font-semibold">Department</span>
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
                      {selectedCase.type === 'patient' ? 'Assigned Nurse' : 'Room / Floor'}
                    </span>
                    <span className="font-semibold text-slate-200">
                      {selectedCase.type === 'patient'
                        ? caseDetails.assigned_nurse_name || 'None'
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
                                  ? (item.note_type || 'clinical_note').replace('_', ' ')
                                  : (item.event_type || 'event').replace('_', ' ')}
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
                                <span>Triggered By: {item.triggered_by || 'System Engine'}</span>
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
