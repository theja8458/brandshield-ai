import React, { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  Shield,
  LayoutDashboard,
  Building2,
  Share2,
  Smartphone,
  Network,
  SearchCheck,
  Radio,
  Server,
  Database,
  ExternalLink,
  Menu,
  X,
  RefreshCw,
  LogOut,
  User as UserIcon,
} from 'lucide-react';
import { checkApiHealth, HealthStatus, API_BASE_URL } from '../config';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/brand', label: 'Brand Profile', icon: Building2 },
  { path: '/social', label: 'Social Monitoring', icon: Share2 },
  { path: '/apps', label: 'App Monitoring', icon: Smartphone },
  { path: '/campaigns', label: 'Campaigns', icon: Network },
  { path: '/investigations', label: 'Investigations', icon: SearchCheck },
  { path: '/sources', label: 'Sources', icon: Radio },
];

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const refreshHealth = async () => {
    setIsChecking(true);
    const status = await checkApiHealth();
    setHealth(status);
    setIsChecking(false);
  };

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isDbReady = health?.status === 'ready' && health?.database === 'connected';

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Sidebar for Desktop */}
      <aside className="hidden md:flex w-64 flex-col border-r border-slate-800/80 bg-slate-900/40 backdrop-blur-md">
        {/* Brand Header */}
        <div className="flex h-16 items-center gap-3 border-b border-slate-800/80 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 shadow-md shadow-indigo-600/30">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-sm tracking-wide text-white">BrandShield AI</span>
            <span className="block text-[10px] text-indigo-400 font-medium">Digital Risk Protection</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* User Card & Logout in Sidebar Footer */}
        {user && (
          <div className="border-t border-slate-800/80 p-3 mx-2 my-2 rounded-xl bg-slate-900/50 border border-slate-800/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="h-7 w-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 shrink-0">
                  <UserIcon className="h-3.5 w-3.5" />
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-medium text-slate-200 truncate">{user.email}</p>
                  <span className={`inline-block text-[9px] uppercase tracking-wider font-semibold px-1 rounded ${
                    user.role === 'admin'
                      ? 'bg-purple-500/20 text-purple-300'
                      : 'bg-indigo-500/20 text-indigo-300'
                  }`}>
                    {user.role}
                  </span>
                </div>
              </div>
              <button
                onClick={() => logout()}
                title="Sign Out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Backend & DB Health Telemetry */}
        <div className="border-t border-slate-800/80 p-4 text-xs bg-slate-950/40">
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-slate-400 text-[11px] uppercase tracking-wider">Telemetry</span>
            <button
              onClick={refreshHealth}
              disabled={isChecking}
              title="Refresh health status"
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <RefreshCw className={`h-3 w-3 ${isChecking ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Server className="h-3 w-3 text-slate-500" /> API:
              </span>
              <span className={`inline-flex items-center gap-1 font-mono text-[11px] font-semibold ${
                health?.status === 'ready' || health?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  health?.status === 'ready' || health?.status === 'ok' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                }`}></span>
                {health?.status || 'checking...'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Database className="h-3 w-3 text-slate-500" /> Atlas:
              </span>
              <span className={`inline-flex items-center gap-1 font-mono text-[11px] font-semibold ${
                isDbReady ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  isDbReady ? 'bg-emerald-400' : 'bg-amber-400'
                }`}></span>
                {health?.database || 'disconnected'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b border-slate-800/80 bg-slate-900/30 px-4 md:px-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-400 hover:bg-slate-800"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium px-2 py-0.5 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-300">
                Hackathon Prototype
              </span>
              <span className="hidden sm:inline-block text-xs text-slate-500">
                • Kampus.VC Social & App Monitoring
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs">
            {/* User details in top header */}
            {user && (
              <div className="hidden sm:flex items-center gap-2 bg-slate-900/60 border border-slate-800 px-3 py-1 rounded-lg">
                <UserIcon className="h-3.5 w-3.5 text-indigo-400" />
                <span className="text-slate-300 font-medium">{user.email}</span>
                <span className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded ${
                  user.role === 'admin'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                }`}>
                  {user.role}
                </span>
              </div>
            )}

            <button
              onClick={() => logout()}
              title="Sign Out"
              className="inline-flex items-center gap-1.5 text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 px-2.5 py-1 rounded border border-slate-700/60 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Sign Out</span>
            </button>

            <a
              href={`${API_BASE_URL}/health`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-slate-400 hover:text-indigo-300 transition-colors bg-slate-800/60 px-2.5 py-1 rounded border border-slate-700/60"
            >
              <span>API /health</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </header>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-slate-800 bg-slate-900 px-4 py-3 space-y-2">
            {user && (
              <div className="p-2 mb-2 rounded bg-slate-800/50 border border-slate-700/50 flex items-center justify-between text-xs">
                <div>
                  <p className="font-semibold text-slate-200">{user.email}</p>
                  <span className="text-[10px] text-indigo-400 uppercase font-semibold">{user.role}</span>
                </div>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    logout();
                  }}
                  className="text-xs text-rose-300 flex items-center gap-1"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Logout</span>
                </button>
              </div>
            )}
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'bg-indigo-600/20 text-indigo-300 font-semibold'
                        : 'text-slate-400 hover:bg-slate-800'
                    }`
                  }
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        )}

        {/* Page Content Body */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
