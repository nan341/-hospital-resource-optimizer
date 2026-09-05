import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, UserCheck, HeartHandshake, Activity, Stethoscope, Building2, Clock, ChevronRight } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 md:p-12">
      {/* Header */}
      <header className="max-w-6xl mx-auto w-full flex items-center justify-between border-b border-slate-800/80 pb-6">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl text-white shadow-lg shadow-cyan-900/40">
            <Activity className="w-7 h-7 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-black tracking-tight text-white flex items-center gap-2">
              HOSPITAL RESOURCE OPTIMIZER
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                v2.0 Multi-Portal
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Intelligent Bed Allocation • Dynamic Staff Balancing • Outpatient Appointment Scheduling
            </p>
          </div>
        </div>
        <div className="hidden sm:flex items-center space-x-2 text-xs font-mono text-slate-400 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>PORTAL GATEWAY ONLINE</span>
        </div>
      </header>

      {/* Main Portal Selection Cards */}
      <main className="max-w-6xl mx-auto w-full my-auto py-10">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight mb-3">
            Select Your Access Portal
          </h2>
          <p className="text-sm md:text-base text-slate-400">
            Choose your designated interface to access operational controls, personal clinical duty tools, or public outpatient services.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {/* Admin Portal Card */}
          <div
            onClick={() => navigate('/admin/login')}
            className="group relative bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/60 rounded-2xl p-7 flex flex-col justify-between transition-all duration-300 hover:shadow-2xl hover:shadow-cyan-950/50 hover:-translate-y-1.5 cursor-pointer"
          >
            <div>
              <div className="w-14 h-14 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-6 group-hover:bg-cyan-500 group-hover:text-slate-950 transition-colors duration-300">
                <Shield className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 flex items-center justify-between">
                <span>Administration Portal</span>
                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Executive dashboard, real-time bed occupancy map, ICU critical overflow routing, simulation controls, and 2-hour ML demand forecasting.
              </p>
            </div>
            <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 group-hover:text-cyan-400 font-medium">
              <span>Admin Login Required</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800/70 border border-slate-700/60">/admin</span>
            </div>
          </div>

          {/* Clinical Staff Portal Card */}
          <div
            onClick={() => navigate('/staff/login')}
            className="group relative bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/60 rounded-2xl p-7 flex flex-col justify-between transition-all duration-300 hover:shadow-2xl hover:shadow-indigo-950/50 hover:-translate-y-1.5 cursor-pointer"
          >
            <div>
              <div className="w-14 h-14 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-6 group-hover:bg-indigo-500 group-hover:text-slate-950 transition-colors duration-300">
                <UserCheck className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 flex items-center justify-between">
                <span>Clinical Staff Portal</span>
                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Personal duty roster, duty toggle, real-time patient assignment alerts with age/chief complaints, and outpatient consultation queues.
              </p>
            </div>
            <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 group-hover:text-indigo-400 font-medium">
              <span>Staff Code Required</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800/70 border border-slate-700/60">/staff</span>
            </div>
          </div>

          {/* Patient Services Portal Card */}
          <div
            onClick={() => navigate('/patient')}
            className="group relative bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-emerald-500/60 rounded-2xl p-7 flex flex-col justify-between transition-all duration-300 hover:shadow-2xl hover:shadow-emerald-950/50 hover:-translate-y-1.5 cursor-pointer"
          >
            <div>
              <div className="w-14 h-14 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-6 group-hover:bg-emerald-500 group-hover:text-slate-950 transition-colors duration-300">
                <HeartHandshake className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 flex items-center justify-between">
                <span>Patient Services</span>
                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Public service availability, book OPD and ENT appointments, get instant queue tickets, and check live wait time status.
              </p>
            </div>
            <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 group-hover:text-emerald-400 font-medium">
              <span className="text-emerald-400 font-semibold">Public Access (No Login)</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800/70 border border-slate-700/60">/patient</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto w-full text-center text-xs text-slate-500 border-t border-slate-900 pt-6">
        Hospital Resource Optimizer • Autonomous Multi-Agent Resource Optimization Engine
      </footer>
    </div>
  );
}
