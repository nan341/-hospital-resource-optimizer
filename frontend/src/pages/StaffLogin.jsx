import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserCheck, Key, ArrowLeft, AlertTriangle, LogIn } from 'lucide-react';
import { staffLogin } from '../api';

export default function StaffLogin() {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await staffLogin(password);
      if (res.data && res.data.token) {
        sessionStorage.setItem('staff_token', res.data.token);
        navigate('/staff');
      }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Invalid staff access code. Please try again.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl shadow-indigo-950/40 relative">
        {/* Back Link */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-200 mb-6 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Portals</span>
        </button>

        {/* Icon & Heading */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-indigo-500/10 border border-indigo-500/30 rounded-2xl flex items-center justify-center mx-auto mb-4 text-indigo-400 shadow-inner">
            <UserCheck className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">Clinical Staff Access</h2>
          <p className="text-xs text-slate-400 mt-1">
            Sign in to view your duty roster, live patient queues, and clinical notifications
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-3 bg-rose-950/80 border border-rose-600/80 rounded-xl text-xs text-rose-200 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Staff Access Code
            </label>
            <div className="relative">
              <input
                type="password"
                required
                placeholder="Enter staff access code"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 pl-10 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition"
              />
              <Key className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Default access code: <span className="font-mono text-indigo-400">staff123</span>
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold uppercase tracking-wider rounded-xl transition shadow-lg shadow-indigo-950/50 flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <LogIn className="w-4 h-4" />
            <span>{loading ? 'Verifying Code...' : 'Access Staff Workspace'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
