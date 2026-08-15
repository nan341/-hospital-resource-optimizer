import React, { useState } from 'react';
import { AlertTriangle, Play, Pause, Zap, RotateCcw, Activity, ShieldAlert, Cpu } from 'lucide-react';
import { startSimulation, stopSimulation, triggerSurge, resetSystem } from '../api';

export default function SurgeAlert({ criticalAlert, isSimRunning, onResetSuccess, onSurgeSuccess }) {
  const [loading, setLoading] = useState(false);
  const [selectedDept, setSelectedDept] = useState('er');
  const [patientCount, setPatientCount] = useState(8);
  const [feedback, setFeedback] = useState(null);

  const handleToggleSim = async () => {
    try {
      setLoading(true);
      if (isSimRunning) {
        await stopSimulation();
        setFeedback('Simulation paused.');
      } else {
        await startSimulation(2.5);
        setFeedback('Simulation running at 2.5x speed.');
      }
    } catch (err) {
      setFeedback('Error toggling simulation: ' + err.message);
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 3500);
    }
  };

  const handleTriggerSurge = async () => {
    try {
      setLoading(true);
      const res = await triggerSurge(selectedDept, Number(patientCount));
      setFeedback(`Surge Triggered: ${patientCount} critical patients sent to ${selectedDept.toUpperCase()}!`);
      if (onSurgeSuccess) onSurgeSuccess(res.data);
    } catch (err) {
      setFeedback('Error triggering surge: ' + err.message);
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset hospital database to fresh seed state?')) return;
    try {
      setLoading(true);
      await resetSystem();
      setFeedback('Hospital database reset to initial seeded state.');
      if (onResetSuccess) onResetSuccess();
    } catch (err) {
      setFeedback('Error resetting system: ' + err.message);
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 3500);
    }
  };

  return (
    <div className="space-y-3">
      {/* Critical No Capacity Alert Banner */}
      {criticalAlert && (
        <div className="bg-rose-950/80 border-2 border-rose-500/80 rounded-xl p-4 flex items-center justify-between text-rose-100 shadow-xl shadow-rose-950/50 animate-pulse">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-rose-600 rounded-lg text-white">
              <ShieldAlert className="w-6 h-6 animate-bounce" />
            </div>
            <div>
              <div className="font-bold text-lg text-rose-200 tracking-wide flex items-center gap-2">
                CRITICAL HOSPITAL OVERFLOW / CAPACITY EXHAUSTION
              </div>
              <p className="text-sm text-rose-300">
                {criticalAlert.description || 'Zero bed capacity hospital-wide for incoming critical trauma cases. Automatic triage re-routing initiated.'}
              </p>
            </div>
          </div>
          <button
            onClick={() => handleReset()}
            className="px-4 py-2 bg-rose-700 hover:bg-rose-600 text-white text-xs font-semibold rounded-lg transition"
          >
            Reset Hospital State
          </button>
        </div>
      )}

      {/* Simulation & Surge Control Ribbon */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg backdrop-blur flex flex-wrap items-center justify-between gap-4">
        {/* Left: Simulation State Indicator */}
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${isSimRunning ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'}`}>
            <Activity className={`w-5 h-5 ${isSimRunning ? 'animate-spin' : ''}`} style={{ animationDuration: '3s' }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Simulation Engine</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                isSimRunning ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'
              }`}>
                {isSimRunning ? '● LIVE (2.5x)' : '○ PAUSED'}
              </span>
            </div>
            <p className="text-xs text-slate-400">Poisson patient arrival simulator & automated priority-queue engine</p>
          </div>
        </div>

        {/* Center/Right: Actions */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* Start/Pause Button */}
          <button
            onClick={handleToggleSim}
            disabled={loading}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium text-sm transition shadow-sm ${
              isSimRunning
                ? 'bg-amber-600/90 hover:bg-amber-500 text-white'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            {isSimRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{isSimRunning ? 'Pause Sim' : 'Start Sim'}</span>
          </button>

          {/* Surge Controller Group */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-lg p-1 space-x-1.5">
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="bg-slate-900 text-slate-200 text-xs px-2.5 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-cyan-500"
            >
              <option value="er">Emergency Room (ER)</option>
              <option value="general_ward">General Ward</option>
              <option value="icu">ICU</option>
              <option value="pediatrics">Pediatrics</option>
            </select>

            <select
              value={patientCount}
              onChange={(e) => setPatientCount(e.target.value)}
              className="bg-slate-900 text-slate-200 text-xs px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-cyan-500"
            >
              <option value="4">4 pts</option>
              <option value="8">8 pts (Saturate)</option>
              <option value="12">12 pts (Mass Surge)</option>
            </select>

            <button
              onClick={handleTriggerSurge}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded transition shadow-md shadow-rose-900/30"
              title="Force deterministic surge of critical patients"
            >
              <Zap className="w-3.5 h-3.5 fill-current" />
              <span>Trigger Surge</span>
            </button>
          </div>

          {/* Reset System Button */}
          <button
            onClick={handleReset}
            disabled={loading}
            className="flex items-center space-x-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition border border-slate-700"
            title="Reset database to initial seeded capacity"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset DB</span>
          </button>
        </div>
      </div>

      {/* Transient Action Feedback */}
      {feedback && (
        <div className="bg-cyan-950/80 border border-cyan-700/60 text-cyan-200 text-xs px-4 py-2 rounded-lg shadow-md flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            {feedback}
          </span>
          <span className="text-[10px] text-cyan-400 uppercase tracking-wider">System Action</span>
        </div>
      )}
    </div>
  );
}
