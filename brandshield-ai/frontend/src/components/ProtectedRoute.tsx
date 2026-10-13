import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center gap-4">
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/20 border border-indigo-500/30 shadow-xl shadow-indigo-600/20 animate-pulse">
            <Shield className="h-8 w-8 text-indigo-400" />
            <div className="absolute inset-0 rounded-2xl ring-2 ring-indigo-500/40 animate-ping opacity-25"></div>
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold tracking-wide text-slate-200">BrandShield AI</p>
            <p className="text-xs text-slate-400 mt-0.5">Verifying authenticated session...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
};
