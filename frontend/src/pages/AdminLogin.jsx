import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, ArrowLeft, AlertTriangle, KeyRound } from 'lucide-react';
import { adminLogin } from '../api';

export default function AdminLogin() {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await adminLogin(password);
      if (res.data && res.data.token) {
        sessionStorage.setItem('admin_token', res.data.token);
        navigate('/admin');
      }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Invalid administrator password. Please try again.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl shadow-cyan-950/40 relative">
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
          <div className="w-16 h-16 bg-cyan-500/10 border border-cyan-500/30 rounded-2xl flex items-center justify-center mx-auto mb-4 text-cyan-400 shadow-inner">
            <Shield className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">Hospital Administration</h2>
          <p className="text-xs text-slate-400 mt-1">
            Authenticate to access live capacity controls and predictive orchestration
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
              Admin Master Password
            </label>
            <div className="relative">
              <input
                type="password"
                required
                placeholder="Enter admin password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 pl-10 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500 transition"
              />
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Default password: <span className="font-mono text-cyan-400">changeme</span>
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold uppercase tracking-wider rounded-xl transition shadow-lg shadow-cyan-950/50 flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <KeyRound className="w-4 h-4" />
            <span>{loading ? 'Authenticating...' : 'Enter Admin Dashboard'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
