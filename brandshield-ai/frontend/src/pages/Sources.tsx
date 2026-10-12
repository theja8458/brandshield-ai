import React, { useEffect, useState } from 'react';
import {
  Radio,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Server,
  ShieldAlert,
  Info,
} from 'lucide-react';
import { fetchSources, testSourceConnection, ConnectorStatus } from '../api/sourcesClient';

export const Sources: React.FC = () => {
  const [sources, setSources] = useState<ConnectorStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSources();
      setSources(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to backend';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleTestConnection = async (connectorId: string) => {
    setTestingId(connectorId);
    setError(null);
    setFeedback(null);
    try {
      const updated = await testSourceConnection(connectorId);
      setSources((prev) =>
        prev.map((s) => (s.connector_id === connectorId ? updated : s))
      );
      setFeedback(`Connector '${updated.display_name}' tested: status is ${updated.state.toUpperCase()}.`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Connection test failed';
      setError(message);
    } finally {
      setTestingId(null);
    }
  };

  const getModeBadge = (mode: string) => {
    switch (mode) {
      case 'live':
        return (
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-400 border border-emerald-500/20">
            LIVE CONNECTOR
          </span>
        );
      case 'demo':
        return (
          <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-400 border border-indigo-500/20">
            DEMO SEED
          </span>
        );
      case 'manual':
        return (
          <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-400 border border-amber-500/20">
            MANUAL SUBMISSION
          </span>
        );
      default:
        return null;
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'available':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-amber-400" />;
      case 'unavailable':
        return <XCircle className="h-4 w-4 text-rose-400" />;
      default:
        return <Server className="h-4 w-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Radio className="h-6 w-6 text-indigo-400" />
            Public Data Sources & Connector Telemetry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real public endpoints with graceful degradation, bounded timeouts, and strict provenance labeling.
          </p>
        </div>

        <button
          onClick={loadSources}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>

      {/* Notifications */}
      {feedback && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{feedback}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {error && (
        <div className="flex items-center justify-between rounded-lg border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Connector Cards Grid */}
      {loading && sources.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-400 text-sm">
          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-indigo-400 mb-2" />
          Probing connector endpoints...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sources.map((src) => (
            <div
              key={src.connector_id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 flex flex-col justify-between space-y-4 shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      {src.display_name}
                    </h3>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                      ID: <span className="text-slate-300">{src.connector_id}</span> • Platform: <span className="text-slate-300">{src.platform}</span>
                    </div>
                  </div>
                  {getModeBadge(src.mode)}
                </div>

                {/* State Pill */}
                <div className="flex items-center gap-2 mt-3 text-xs">
                  <div className="flex items-center gap-1.5 font-semibold">
                    {getStateIcon(src.state)}
                    <span
                      className={`capitalize ${
                        src.state === 'available'
                          ? 'text-emerald-400'
                          : src.state === 'degraded'
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {src.state}
                    </span>
                  </div>

                  <span className="text-slate-600">•</span>
                  <span className="text-[11px] text-slate-400">
                    Last success: {src.last_success_at ? new Date(src.last_success_at).toLocaleTimeString() : 'Never'}
                  </span>
                </div>

                {src.last_error_message && (
                  <div className="mt-2 rounded bg-rose-950/30 border border-rose-500/20 p-2 text-[11px] text-rose-300">
                    <strong>Error:</strong> {src.last_error_message}
                  </div>
                )}
              </div>

              {/* Actions & Details Footer */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-[11px] text-slate-500">
                  {src.mode === 'live' ? '8s timeout • allowlisted host' : 'Offline / internal'}
                </span>

                {src.mode === 'live' && (
                  <button
                    onClick={() => handleTestConnection(src.connector_id)}
                    disabled={testingId === src.connector_id}
                    className="inline-flex items-center gap-1.5 rounded bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50 transition-colors border border-slate-700"
                  >
                    <RefreshCw className={`h-3 w-3 ${testingId === src.connector_id ? 'animate-spin text-indigo-400' : ''}`} />
                    {testingId === src.connector_id ? 'Testing...' : 'Test Connection'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Safety & Allowlist Guarantee Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-indigo-400" />
          Outbound Ingestion Guardrails & Security Policies
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-300">
          <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/80">
            <div className="font-semibold text-white mb-1">Fixed Allowlisted Hosts</div>
            <p className="text-[11px] text-slate-400">
              Only <code className="text-indigo-300">itunes.apple.com</code> and <code className="text-indigo-300">public.api.bsky.app</code> are queried. Server never requests arbitrary user-supplied URLs.
            </p>
          </div>

          <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/80">
            <div className="font-semibold text-white mb-1">Graceful Degradation</div>
            <p className="text-[11px] text-slate-400">
              If a public service experiences an upstream timeout, BrandShield AI reports the failure honestly and never silently replaces it with synthetic data.
            </p>
          </div>

          <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/80">
            <div className="font-semibold text-white mb-1">Bounded Resiliency</div>
            <p className="text-[11px] text-slate-400">
              Strict 8.0s timeout, max 2MB payload ceiling, max 2 retries with exponential backoff, and query batching capped at 6 queries per brand scan.
            </p>
          </div>
        </div>
      </div>

      {/* Transparent Scope Note */}
      <div className="flex items-start gap-2.5 rounded-lg border border-slate-800 bg-slate-950/50 p-3.5 text-xs text-slate-400">
        <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-200">Platform Exclusions:</strong> Google Play Store, Instagram, and X are not integrated in this prototype due to the absence of public unauthenticated REST APIs. Full compliance details documented in <code className="text-indigo-300">docs/sources.md</code>.
        </div>
      </div>
    </div>
  );
};
