import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  HeartPulse,
  Calendar,
  Search,
  CheckCircle2,
  Clock,
  MapPin,
  Building2,
  AlertCircle,
  ArrowLeft,
  ChevronRight,
  User,
  ShieldCheck,
  Stethoscope
} from 'lucide-react';
import {
  getPublicAvailability,
  getOutpatientDepartments,
  bookAppointment,
  checkAppointmentStatus
} from '../api';

export default function PatientPortal() {
  const navigate = useNavigate();

  const [availability, setAvailability] = useState([]);
  const [outpatientDepts, setOutpatientDepts] = useState([]);
  const [loadingAvail, setLoadingAvail] = useState(true);

  // Booking Form State
  const [patientName, setPatientName] = useState('');
  const [patientAge, setPatientAge] = useState('');
  const [reasonForVisit, setReasonForVisit] = useState('');
  const [departmentId, setDepartmentId] = useState('opd');
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingResult, setBookingResult] = useState(null);
  const [bookingError, setBookingError] = useState(null);

  // Status Lookup State
  const [lookupId, setLookupId] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState(null);

  // Fetch Public Data on load
  const loadData = async () => {
    try {
      setLoadingAvail(true);
      const [availRes, deptsRes] = await Promise.all([
        getPublicAvailability(),
        getOutpatientDepartments()
      ]);
      setAvailability(availRes.data);
      setOutpatientDepts(deptsRes.data);
      if (deptsRes.data.length > 0) {
        setDepartmentId(deptsRes.data[0].department_id);
      }
    } catch (err) {
      console.error('Error loading patient portal data:', err);
    } finally {
      setLoadingAvail(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 8000);
    return () => clearInterval(timer);
  }, []);

  // Handle Booking
  const handleBookingSubmit = async (e) => {
    e.preventDefault();
    setBookingLoading(true);
    setBookingError(null);
    setBookingResult(null);

    try {
      const payload = {
        patient_name: patientName,
        patient_age: patientAge ? parseInt(patientAge, 10) : undefined,
        reason_for_visit: reasonForVisit.trim() || undefined,
        department_id: departmentId
      };

      const res = await bookAppointment(payload);
      setBookingResult(res.data);
      setPatientName('');
      setPatientAge('');
      setReasonForVisit('');
      loadData();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to schedule appointment. Please try again.';
      setBookingError(msg);
    } finally {
      setBookingLoading(false);
    }
  };

  // Handle Appointment Lookup
  const handleLookupSubmit = async (e) => {
    e.preventDefault();
    if (!lookupId.trim()) return;

    setLookupLoading(true);
    setLookupError(null);
    setLookupResult(null);

    try {
      const res = await checkAppointmentStatus(lookupId.trim().toUpperCase());
      setLookupResult(res.data);
    } catch (err) {
      const msg = err.response?.data?.detail || `No appointment found with ticket ID "${lookupId}".`;
      setLookupError(msg);
    } finally {
      setLookupLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Top Friendly Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-emerald-600 rounded-xl text-white shadow-md shadow-emerald-600/30">
              <HeartPulse className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg md:text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                CityCare Patient & Outpatient Services
              </h1>
              <p className="text-xs text-slate-500">
                Hospital Service Status • Online Clinic Appointments • Live Queue Check
              </p>
            </div>
          </div>

          <button
            onClick={() => navigate('/')}
            className="flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-emerald-700 bg-slate-100 hover:bg-emerald-50 px-3 py-2 rounded-xl transition border border-slate-200"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Portal Selection</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* SECTION 1: LIVE HOSPITAL SERVICE AVAILABILITY (QUALITATIVE ONLY) */}
        <section className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4 mb-5">
            <div>
              <h2 className="text-base md:text-lg font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-emerald-600" />
                Live Hospital Department Availability
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Current operational capacity and walk-in status across inpatient units and outpatient clinics
              </p>
            </div>
            <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 self-start sm:self-auto">
              Updated Live
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {availability.map((dept) => {
              const isInpatient = dept.type === 'inpatient';
              return (
                <div
                  key={dept.department_id}
                  className="bg-slate-50/70 border border-slate-200 rounded-xl p-4 flex flex-col justify-between hover:border-emerald-300 transition"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-sm text-slate-900">{dept.name}</h3>
                      <span className="text-[11px] text-slate-500 font-medium">
                        {isInpatient ? 'Inpatient Care Unit' : 'Outpatient Clinic'}
                      </span>
                    </div>
                    <span
                      className={`text-[10px] uppercase font-bold px-2.5 py-1 rounded-full border ${
                        isInpatient
                          ? dept.beds_status === 'Available'
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                            : 'bg-rose-100 text-rose-800 border-rose-300'
                          : 'bg-blue-100 text-blue-800 border-blue-300'
                      }`}
                    >
                      {isInpatient ? `Beds ${dept.beds_status}` : 'Walk-ins Open'}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-600 border-t border-slate-200/60 pt-3">
                    {isInpatient ? (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Bed Admission Status:</span>
                          <span className={`font-semibold ${dept.beds_status === 'Available' ? 'text-emerald-700' : 'text-rose-700'}`}>
                            {dept.beds_status === 'Available' ? 'Accepting Patients' : 'At Capacity'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Diagnostic Scanners:</span>
                          <span className="font-medium text-slate-700">{dept.diagnostics_status}</span>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Consultation Status:</span>
                          <span className="font-semibold text-blue-700">{dept.clinic_status}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500">Est. Wait Time:</span>
                          <span className="font-bold text-slate-800">
                            ~{dept.estimated_wait_minutes || 0} mins wait
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* SECTION 2 & 3 SPLIT: APPOINTMENT BOOKING & STATUS LOOKUP */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* LEFT: BOOK APPOINTMENT (7 COLS) */}
          <div className="lg:col-span-7 bg-white rounded-2xl p-6 md:p-8 border border-slate-200/80 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2.5 border-b border-slate-100 pb-4 mb-6">
                <div className="p-2 bg-emerald-100 text-emerald-700 rounded-lg">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base md:text-lg font-bold text-slate-900">
                    Book Outpatient Appointment
                  </h2>
                  <p className="text-xs text-slate-500">
                    Get an instant queue ticket for General OPD or ENT consultation
                  </p>
                </div>
              </div>

              {/* Booking Confirmation Card */}
              {bookingResult ? (
                <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 text-slate-900 space-y-4 animate-in fade-in duration-300">
                  <div className="flex items-center space-x-2 text-emerald-800 font-bold text-base">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                    <span>Appointment Confirmed!</span>
                  </div>

                  <p className="text-xs text-slate-600">
                    Your appointment has been scheduled with the least-loaded physician. Please proceed directly to your assigned consultation room.
                  </p>

                  <div className="bg-white rounded-xl p-4 border border-emerald-200/80 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="block text-slate-500 text-[11px]">Ticket ID</span>
                      <span className="font-mono font-bold text-sm text-emerald-700">{bookingResult.appointment_id}</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[11px]">Assigned Doctor</span>
                      <span className="font-bold text-slate-900">{bookingResult.doctor_name}</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[11px]">Clinic Room</span>
                      <span className="font-bold text-slate-900">{bookingResult.floor} • {bookingResult.room_number}</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[11px]">Queue Position</span>
                      <span className="font-bold text-indigo-700 text-sm">
                        You are #{bookingResult.queue_position} in line
                      </span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[11px]">Est. Wait Time</span>
                      <span className="font-bold text-slate-900">~{bookingResult.estimated_wait_minutes} minutes</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[11px]">Patient Name</span>
                      <span className="font-medium text-slate-800">{bookingResult.patient_name}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => setBookingResult(null)}
                    className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition shadow-sm"
                  >
                    Book Another Appointment
                  </button>
                </div>
              ) : (
                <form onSubmit={handleBookingSubmit} className="space-y-4">
                  {bookingError && (
                    <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center space-x-2">
                      <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                      <span>{bookingError}</span>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                      Clinic Department
                    </label>
                    <select
                      value={departmentId}
                      onChange={(e) => setDepartmentId(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition"
                    >
                      {outpatientDepts.map((d) => (
                        <option key={d.department_id} value={d.department_id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                        Patient Full Name *
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. John Doe"
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                        Age (Years)
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="120"
                        placeholder="Age"
                        value={patientAge}
                        onChange={(e) => setPatientAge(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                      Reason for Consultation / Symptoms
                    </label>
                    <textarea
                      rows={2}
                      maxLength={300}
                      placeholder="e.g. Sore throat for 3 days, mild fever, earache"
                      value={reasonForVisit}
                      onChange={(e) => setReasonForVisit(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={bookingLoading}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold uppercase tracking-wider rounded-xl transition shadow-md shadow-emerald-600/30 flex items-center justify-center space-x-2 disabled:opacity-50"
                  >
                    <Calendar className="w-4 h-4" />
                    <span>{bookingLoading ? 'Scheduling...' : 'Confirm & Get Ticket'}</span>
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* RIGHT: CHECK MY APPOINTMENT STATUS (5 COLS) */}
          <div className="lg:col-span-5 bg-white rounded-2xl p-6 md:p-8 border border-slate-200/80 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2.5 border-b border-slate-100 pb-4 mb-6">
                <div className="p-2 bg-blue-100 text-blue-700 rounded-lg">
                  <Search className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base md:text-lg font-bold text-slate-900">
                    Check My Appointment
                  </h2>
                  <p className="text-xs text-slate-500">
                    Track your current position in the consultation queue
                  </p>
                </div>
              </div>

              <form onSubmit={handleLookupSubmit} className="space-y-3 mb-6">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Appointment Ticket ID
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      required
                      placeholder="e.g. APT-A1B2C3D4"
                      value={lookupId}
                      onChange={(e) => setLookupId(e.target.value)}
                      className="w-full uppercase font-mono bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={lookupLoading}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold uppercase tracking-wider rounded-xl transition shadow-md shadow-blue-600/30 flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <Search className="w-4 h-4" />
                  <span>{lookupLoading ? 'Checking...' : 'Check Status'}</span>
                </button>
              </form>

              {lookupError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                  <span>{lookupError}</span>
                </div>
              )}

              {/* Lookup Status Card */}
              {lookupResult && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 animate-in fade-in duration-300">
                  <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
                    <span className="text-xs font-mono font-bold text-blue-700">{lookupResult.appointment_id}</span>
                    <span
                      className={`text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                        lookupResult.status === 'in_consultation'
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : lookupResult.status === 'completed'
                          ? 'bg-slate-200 text-slate-700 border-slate-300'
                          : 'bg-indigo-100 text-indigo-800 border-indigo-300'
                      }`}
                    >
                      {lookupResult.status === 'in_consultation'
                        ? 'Now In Consultation'
                        : lookupResult.status === 'completed'
                        ? 'Completed'
                        : `Waiting (#${lookupResult.queue_position})`}
                    </span>
                  </div>

                  <div className="text-xs space-y-2 text-slate-700">
                    <p className="font-bold text-sm text-slate-900">{lookupResult.patient_name}</p>
                    <p>
                      <span className="text-slate-500">Doctor:</span>{' '}
                      <span className="font-semibold">{lookupResult.doctor_name} ({lookupResult.specialty})</span>
                    </p>
                    <p>
                      <span className="text-slate-500">Location:</span>{' '}
                      <span className="font-semibold">{lookupResult.floor} • {lookupResult.room_number}</span>
                    </p>
                    {lookupResult.status === 'scheduled' && (
                      <div className="pt-2 border-t border-slate-200 text-xs font-medium text-indigo-700">
                        You are currently #{lookupResult.queue_position} in line (~{lookupResult.estimated_wait_minutes} mins estimated wait).
                      </div>
                    )}
                    {lookupResult.status === 'in_consultation' && (
                      <div className="pt-2 border-t border-slate-200 text-xs font-bold text-emerald-700 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" />
                        Please enter {lookupResult.room_number} now for your consultation.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 text-[11px] text-slate-400 text-center">
              Need immediate emergency care? Please visit the Emergency Room directly.
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
