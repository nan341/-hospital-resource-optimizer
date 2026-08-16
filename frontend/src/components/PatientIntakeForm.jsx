import React, { useState, useRef, useEffect } from 'react';
import { UserPlus, Flame, AlertCircle, HeartPulse, CheckCircle2, AlertTriangle, Clock, Send, ShieldCheck, BedDouble } from 'lucide-react';
import { registerPatientIntake, getPatientById } from '../api';

export default function PatientIntakeForm({ departments = [], onIntakeSuccess }) {
  const [departmentNeeded, setDepartmentNeeded] = useState('er');
  const [severity, setSeverity] = useState('critical');
  const [predictedStayHours, setPredictedStayHours] = useState(4.0);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const pollIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const startPatientStatusPolling = (patientId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    let attempts = 0;
    const maxAttempts = 10;

    pollIntervalRef.current = setInterval(async () => {
      attempts += 1;
      try {
        const res = await getPatientById(patientId);
        const p = res.data;

        if (p.status === 'admitted') {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          setMessage({
            type: 'admitted',
            text: `Assigned Bed ${p.assigned_bed_id || 'Allocated'}, Staff ${p.assigned_staff_id || 'On Duty'}`
          });
          if (onIntakeSuccess) onIntakeSuccess(p);
        } else if (attempts >= maxAttempts) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          if (p.status === 'waiting') {
            setMessage({
              type: 'queued',
              text: `Still queued — no bed currently available`
            });
          }
        }
      } catch (err) {
        console.warn('Error polling patient status:', err);
        if (attempts >= maxAttempts) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    }, 1500);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const payload = {
        department_needed: departmentNeeded,
        severity: severity,
        predicted_stay_hours: Number(predictedStayHours) || 4.0,
        notes: notes.trim() || undefined
      };

      const response = await registerPatientIntake(payload);
      const patientId = response.data.patient_id;

      // Stage 1: Immediately show registered and waiting in queue
      setMessage({
        type: 'waiting',
        text: `Registered ${patientId} — waiting in queue...`
      });

      // Clear notes field on success, keep department & severity
      setNotes('');

      if (onIntakeSuccess) {
        onIntakeSuccess(response.data);
      }

      // Start live polling to track allocation transition
      startPatientStatusPolling(patientId);

    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message;
      setMessage({
        type: 'error',
        text: `Intake failed: ${errorDetail}`
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-cyan-500/20 text-cyan-400 rounded-lg border border-cyan-500/30">
            <UserPlus className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-slate-100 text-sm">Real-Time Patient Intake</h3>
            <p className="text-[11px] text-slate-400">Manual Walk-in / Ambulance Registration</p>
          </div>
        </div>
        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/80">
          Direct Triage
        </span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Department Selector */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Destination Department
          </label>
          <select
            value={departmentNeeded}
            onChange={(e) => setDepartmentNeeded(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
          >
            {departments.length === 0 ? (
              <>
                <option value="er">Emergency Room (ER)</option>
                <option value="general_ward">General Ward</option>
                <option value="icu">Intensive Care Unit (ICU)</option>
                <option value="pediatrics">Pediatrics</option>
              </>
            ) : (
              departments.map((d) => (
                <option key={d.department_id} value={d.department_id}>
                  {d.name} ({d.available_beds ?? d.total_beds} beds available)
                </option>
              ))
            )}
          </select>
        </div>

        {/* Severity Acuity Selector (3 Buttons) */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Acuity / Severity Level
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setSeverity('critical')}
              className={`flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-lg text-xs font-bold transition border ${
                severity === 'critical'
                  ? 'bg-rose-950/90 text-rose-200 border-rose-500 shadow-md shadow-rose-950/60 ring-1 ring-rose-400'
                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <Flame className="w-3.5 h-3.5 text-rose-400" />
              <span>Critical</span>
            </button>

            <button
              type="button"
              onClick={() => setSeverity('moderate')}
              className={`flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-lg text-xs font-bold transition border ${
                severity === 'moderate'
                  ? 'bg-amber-950/90 text-amber-200 border-amber-500 shadow-md shadow-amber-950/60 ring-1 ring-amber-400'
                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>Moderate</span>
            </button>

            <button
              type="button"
              onClick={() => setSeverity('low')}
              className={`flex items-center justify-center space-x-1.5 py-2 px-2.5 rounded-lg text-xs font-bold transition border ${
                severity === 'low'
                  ? 'bg-emerald-950/90 text-emerald-200 border-emerald-500 shadow-md shadow-emerald-950/60 ring-1 ring-emerald-400'
                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <HeartPulse className="w-3.5 h-3.5 text-emerald-400" />
              <span>Low</span>
            </button>
          </div>
        </div>

        {/* Estimated Stay Duration & Optional Notes */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Est. Stay (Hours)
            </label>
            <input
              type="number"
              min="0.5"
              max="336"
              step="0.5"
              value={predictedStayHours}
              onChange={(e) => setPredictedStayHours(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Admission Notes (Optional)
            </label>
            <input
              type="text"
              maxLength={200}
              placeholder="e.g. Trauma MVC, severe asthma, chest pain"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Live Multi-Stage Inline Status / Feedback */}
        {message && (
          <div
            className={`p-2.5 rounded-lg text-xs flex items-center space-x-2 border transition-all ${
              message.type === 'admitted'
                ? 'bg-emerald-950/80 border-emerald-500 text-emerald-200 shadow-md shadow-emerald-950/50'
                : message.type === 'waiting'
                ? 'bg-blue-950/80 border-blue-600 text-blue-200 animate-pulse'
                : message.type === 'queued'
                ? 'bg-slate-900 border-slate-700 text-slate-300'
                : 'bg-rose-950/80 border-rose-600 text-rose-200'
            }`}
          >
            {message.type === 'admitted' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : message.type === 'waiting' ? (
              <Clock className="w-4 h-4 text-blue-400 flex-shrink-0 animate-spin" style={{ animationDuration: '3s' }} />
            ) : message.type === 'queued' ? (
              <BedDouble className="w-4 h-4 text-slate-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            )}
            <span className="truncate font-medium">{message.text}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center space-x-2 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-lg transition shadow-md shadow-cyan-950/50 disabled:opacity-50"
        >
          <Send className="w-3.5 h-3.5" />
          <span>{loading ? 'Admitting Patient...' : 'Register & Queue Patient'}</span>
        </button>
      </form>
    </div>
  );
}
