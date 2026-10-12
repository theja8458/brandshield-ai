import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Activity,
  AlertTriangle,
  RefreshCw,
  Search,
  CheckCircle2,
  BookOpen,
  ArrowUpRight,
  Clock,
  Smartphone,
  Share2,
  Filter,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchDashboardMetrics, DashboardMetrics } from '../api/dashboardClient';
import { checkApiHealth, HealthStatus } from '../config';

export const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>('');
  const [showDocSection, setShowDocSection] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [metricsData, healthData] = await Promise.all([
        fetchDashboardMetrics(),
        checkApiHealth(),
      ]);
      setMetrics(metricsData);
      setHealth(healthData);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to backend';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute severity percentage for visual bars
  const totalThreats = metrics?.active_threats_count || 0;
  const criticalCount = metrics?.active_threats_by_severity?.['Critical'] || 0;
  const highCount = metrics?.active_threats_by_severity?.['High'] || 0;
  const mediumCount = metrics?.active_threats_by_severity?.['Medium'] || 0;
  const lowCount = metrics?.active_threats_by_severity?.['Low'] || 0;
  const reviewCount = metrics?.identity_reviews_required || 0;

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-900 p-6 md:p-8 backdrop-blur-sm relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20 mb-3">
              <ShieldCheck className="h-3.5 w-3.5" />
              Evidence Trail & Operations Integrity Center
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              BrandShield AI Dashboard
            </h1>
            <p className="mt-2 text-sm text-slate-300 max-w-2xl leading-relaxed">
              Auditable Digital Risk Protection operations. All counts are derived strictly from
              persisted MongoDB Atlas records with guaranteed backend official-asset exclusion.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 px-3.5 py-2 text-xs font-medium text-slate-200 transition disabled:opacity-50"
              title="Refresh metrics from MongoDB Atlas"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
              {loading ? 'Refreshing...' : 'Refresh Records'}
            </button>
            <Link
              to="/investigations"
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 transition"
            >
              <Search className="h-3.5 w-3.5" />
              Open Investigations
            </Link>
          </div>
        </div>

        {lastRefreshed && (
          <div className="mt-4 flex items-center gap-4 text-xs text-slate-400 border-t border-slate-800/60 pt-3">
            <span className="flex items-center gap-1.5">
              <Clock className="h-3 w-3 text-slate-500" />
              Last Atlas Sync: <span className="font-mono text-slate-300">{lastRefreshed}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Database:{' '}
              <span className="font-mono text-emerald-300">
                {health?.database_name || 'brandshield_dev'}
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Error Alert if any */}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-300 flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold text-rose-200">Database Connection Issue</div>
            <div>{error}</div>
          </div>
          <button
            onClick={loadData}
            className="rounded border border-rose-700 px-2.5 py-1 text-xs hover:bg-rose-900/50"
          >
            Retry
          </button>
        </div>
      )}

      {/* Primary Executive Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Monitored Brands */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Monitored Brands</span>
            <ShieldCheck className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading && !metrics ? '...' : metrics?.monitored_brands_count ?? 0}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
            <span>Active Brand Profiles</span>
            <Link to="/brand-profile" className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              Manage <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Total Candidates Analyzed */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Candidates Analyzed</span>
            <Activity className="h-4 w-4 text-sky-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading && !metrics ? '...' : metrics?.total_candidates_analyzed ?? 0}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
            <span className="rounded bg-sky-950/60 border border-sky-800/40 px-1.5 py-0.5 text-sky-300 font-medium">
              {metrics?.candidates_by_type?.social_profile ?? 0} Social
            </span>
            <span className="rounded bg-indigo-950/60 border border-indigo-800/40 px-1.5 py-0.5 text-indigo-300 font-medium">
              {metrics?.candidates_by_type?.app_listing ?? 0} Apps
            </span>
          </div>
        </div>

        {/* Active Threats */}
        <div className="rounded-xl border border-rose-900/30 bg-rose-950/10 p-5 hover:border-rose-700/40 transition">
          <div className="flex items-center justify-between text-rose-300 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Threats</span>
            <AlertTriangle className="h-4 w-4 text-rose-400" />
          </div>
          <div className="text-3xl font-extrabold text-rose-200">
            {loading && !metrics ? '...' : metrics?.active_threats_count ?? 0}
          </div>
          <div className="mt-2 text-xs text-rose-300/80 flex items-center justify-between">
            <span>Score &gt; 0 external alerts</span>
            <Link to="/investigations" className="text-rose-300 hover:text-white flex items-center gap-1">
              Triage <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Excluded Official Assets */}
        <div className="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-5 hover:border-emerald-700/40 transition">
          <div className="flex items-center justify-between text-emerald-300 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Official Excluded</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-300">
            {loading && !metrics ? '...' : metrics?.official_assets_excluded ?? 0}
          </div>
          <div className="mt-2 text-xs text-emerald-300/80">
            Backend safe guard: <span className="font-semibold text-emerald-200">0 Risk Score</span>
          </div>
        </div>
      </div>

      {/* Secondary Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Threat Severity Breakdown */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              Active Threats by Severity Level
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Total: {totalThreats}
            </span>
          </div>

          <div className="space-y-3">
            {/* Critical */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-rose-400 font-medium">Critical (Score 85–100)</span>
                <span className="font-mono text-slate-300">{criticalCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-rose-500 rounded-full transition-all duration-500"
                  style={{ width: `${totalThreats > 0 ? (criticalCount / totalThreats) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* High */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-amber-400 font-medium">High (Score 70–84)</span>
                <span className="font-mono text-slate-300">{highCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full transition-all duration-500"
                  style={{ width: `${totalThreats > 0 ? (highCount / totalThreats) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Medium */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-yellow-400 font-medium">Medium (Score 40–69)</span>
                <span className="font-mono text-slate-300">{mediumCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-yellow-500 rounded-full transition-all duration-500"
                  style={{ width: `${totalThreats > 0 ? (mediumCount / totalThreats) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Low */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-blue-400 font-medium">Low (Score &lt; 40)</span>
                <span className="font-mono text-slate-300">{lowCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-500"
                  style={{ width: `${totalThreats > 0 ? (lowCount / totalThreats) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* Identity Reviews */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-purple-400 font-medium">Review Required (Identity Conflicts)</span>
                <span className="font-mono text-slate-300">{reviewCount}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all duration-500"
                  style={{ width: `${totalThreats > 0 ? (reviewCount / totalThreats) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Investigation Lifecycle & Provenance */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Filter className="h-4 w-4 text-indigo-400" />
                Investigation Lifecycle Distribution
              </h3>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
              <div className="rounded-lg bg-slate-800/60 border border-slate-700/60 p-2.5 text-center">
                <div className="text-[10px] uppercase font-bold text-slate-400">New</div>
                <div className="text-lg font-bold text-white mt-1">
                  {metrics?.investigation_status_distribution?.new ?? 0}
                </div>
              </div>
              <div className="rounded-lg bg-amber-950/20 border border-amber-800/40 p-2.5 text-center">
                <div className="text-[10px] uppercase font-bold text-amber-400">Investigating</div>
                <div className="text-lg font-bold text-amber-300 mt-1">
                  {metrics?.investigation_status_distribution?.investigating ?? 0}
                </div>
              </div>
              <div className="rounded-lg bg-emerald-950/20 border border-emerald-800/40 p-2.5 text-center">
                <div className="text-[10px] uppercase font-bold text-emerald-400">Resolved</div>
                <div className="text-lg font-bold text-emerald-300 mt-1">
                  {metrics?.investigation_status_distribution?.resolved ?? 0}
                </div>
              </div>
              <div className="rounded-lg bg-slate-800/40 border border-slate-700/40 p-2.5 text-center">
                <div className="text-[10px] uppercase font-bold text-slate-400">False Positive</div>
                <div className="text-lg font-bold text-slate-300 mt-1">
                  {metrics?.investigation_status_distribution?.false_positive ?? 0}
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-3">
            <div className="text-xs font-semibold text-slate-300 mb-2">Provenance Attribution</div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-emerald-400 border border-emerald-500/20 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Live Connector: {metrics?.provenance_breakdown?.live_connector ?? 0}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 px-2.5 py-1 text-indigo-400 border border-indigo-500/20 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                Manual: {metrics?.provenance_breakdown?.manual ?? 0}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-amber-400 border border-amber-500/20 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                Demo Seed: {metrics?.provenance_breakdown?.demo ?? 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Public Connector Health Status */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-400" />
            Public Connector & Data Source Health
          </h3>
          <Link to="/sources" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
            Configure Sources <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {metrics?.connector_health?.connectors?.map((conn) => (
            <div
              key={conn.connector_id}
              className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-white truncate">{conn.display_name}</span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      conn.state === 'available'
                        ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                        : conn.state === 'degraded'
                        ? 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                        : 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
                    }`}
                  >
                    {conn.state}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Mode: <span className="font-mono text-slate-300">{conn.mode}</span> | Platform:{' '}
                  <span className="text-slate-300">{conn.platform}</span>
                </div>
              </div>
              {conn.last_checked && (
                <div className="mt-2 text-[10px] text-slate-500">
                  Last checked: {new Date(conn.last_checked).toLocaleTimeString()}
                </div>
              )}
            </div>
          )) || (
            <div className="col-span-4 text-xs text-slate-500 py-3 text-center">
              No connector health records loaded.
            </div>
          )}
        </div>
      </div>

      {/* Recent Detections Stream */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Activity className="h-4 w-4 text-rose-400" />
            Recent Threat Detections Stream
          </h3>
          <Link
            to="/investigations"
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
          >
            View All Investigations <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>

        {metrics?.recent_detections && metrics.recent_detections.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/50 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Type</th>
                  <th className="py-2.5 px-3 font-semibold">Candidate</th>
                  <th className="py-2.5 px-3 font-semibold">Score</th>
                  <th className="py-2.5 px-3 font-semibold">Severity</th>
                  <th className="py-2.5 px-3 font-semibold">Provenance</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {metrics.recent_detections.map((cand) => (
                  <tr key={cand.candidate_id} className="hover:bg-slate-800/30 transition">
                    <td className="py-2.5 px-3">
                      <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
                        {cand.candidate_type === 'app_listing' ? (
                          <Smartphone className="h-3.5 w-3.5 text-indigo-400" />
                        ) : (
                          <Share2 className="h-3.5 w-3.5 text-sky-400" />
                        )}
                        {cand.platform || cand.store}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-medium text-white">
                      <div>{cand.candidate_name || cand.app_name || cand.display_name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {cand.handle || cand.package_or_bundle_id}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-mono font-bold text-slate-200">{cand.score}</span>
                      <span className="text-[10px] text-slate-500">/100</span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                          cand.severity === 'Critical'
                            ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
                            : cand.severity === 'High'
                            ? 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                            : cand.severity === 'Medium'
                            ? 'bg-yellow-950/60 text-yellow-400 border border-yellow-800/40'
                            : cand.classification === 'REVIEW_REQUIRED'
                            ? 'bg-purple-950/60 text-purple-400 border border-purple-800/40'
                            : 'bg-blue-950/60 text-blue-400 border border-blue-800/40'
                        }`}
                      >
                        {cand.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          cand.source_type === 'live_connector'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                            : cand.source_type === 'manual'
                            ? 'bg-indigo-950/60 text-indigo-400 border border-indigo-800/40'
                            : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                        }`}
                      >
                        {cand.source_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="capitalize text-[11px] text-slate-300 font-medium">
                        {cand.investigation_status || 'new'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Link
                        to={`/investigations?search=${encodeURIComponent(cand.candidate_name || cand.handle || '')}`}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
                      >
                        Investigate <ArrowUpRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500">
            No threat detections recorded in Atlas yet.
          </div>
        )}
      </div>

      {/* Transparent Metric Definitions & Data Integrity Documentation */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => setShowDocSection(!showDocSection)}
            className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white transition"
          >
            <BookOpen className="h-4 w-4 text-indigo-400" />
            <span>Documented Metric Definitions & Data Integrity Rules</span>
            <span className="text-[10px] rounded bg-slate-800 px-2 py-0.5 text-slate-400 font-normal">
              {showDocSection ? 'Hide Details' : 'Show Details'}
            </span>
          </button>
        </div>

        {showDocSection && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 border-t border-slate-800 pt-4">
            {metrics?.metric_definitions?.map((def) => (
              <div
                key={def.name}
                className="rounded-lg border border-slate-800 bg-slate-950/60 p-3.5 space-y-2 text-xs"
              >
                <div className="font-bold text-white flex items-center justify-between">
                  <span>{def.name}</span>
                </div>
                <p className="text-slate-300 leading-relaxed text-[11px]">{def.description}</p>
                <div className="bg-slate-900 rounded p-2 text-[10px] space-y-1">
                  <div>
                    <span className="font-semibold text-slate-400">Calculation: </span>
                    <span className="font-mono text-indigo-300">{def.calculation}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-400">Integrity Rule: </span>
                    <span className="text-emerald-300">{def.integrity_rule}</span>
                  </div>
                </div>
              </div>
            )) || (
              <div className="text-xs text-slate-500">No definitions loaded.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
