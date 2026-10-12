import React, { useEffect, useState } from 'react';
import {
  Search,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Eye,
  X,
  Share2,
  Smartphone,
  ChevronLeft,
  ChevronRight,
  FileCheck,
} from 'lucide-react';
import { fetchBrands } from '../api/brandClient';
import {
  fetchInvestigationCandidates,
  fetchCandidateEvidence,
  updateCandidateStatus,
  EvidenceDetail,
} from '../api/investigationsClient';
import { Candidate } from '../api/socialClient';
import { Brand } from '../types/brand';

export const Investigations: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [includeOfficial, setIncludeOfficial] = useState<boolean>(false);

  // Evidence Drawer state
  const [activeEvidence, setActiveEvidence] = useState<EvidenceDetail | null>(null);

  // Status update modal / form state
  const [updatingCandidateId, setUpdatingCandidateId] = useState<string | null>(null);
  const [newStatus, setNewStatus] = useState<'new' | 'investigating' | 'resolved' | 'false_positive'>('investigating');
  const [statusNotes, setStatusNotes] = useState<string>('');
  const [submittingStatus, setSubmittingStatus] = useState<boolean>(false);

  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load brands on mount
  useEffect(() => {
    fetchBrands()
      .then((data) => {
        setBrands(data);
      })
      .catch((err) => setError(err.message));
  }, []);

  const loadCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchInvestigationCandidates({
        brand_id: selectedBrandId || undefined,
        candidate_type: typeFilter || undefined,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        source_type: sourceFilter || undefined,
        search: search || undefined,
        include_official: includeOfficial,
        page,
        limit: 25,
      });
      setCandidates(res.items);
      setTotal(res.total);
      setTotalPages(res.pages);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load candidates';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, [selectedBrandId, typeFilter, severityFilter, statusFilter, sourceFilter, includeOfficial, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadCandidates();
  };

  const handleOpenEvidence = async (candidateId: string) => {
    try {
      const ev = await fetchCandidateEvidence(candidateId);
      setActiveEvidence(ev);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch evidence';
      setError(msg);
    }
  };

  const handleOpenStatusModal = (cand: Candidate) => {
    setUpdatingCandidateId(cand.candidate_id);
    setNewStatus(cand.investigation_status || 'investigating');
    setStatusNotes('');
  };

  const handleStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updatingCandidateId) return;
    setSubmittingStatus(true);
    try {
      const updated = await updateCandidateStatus(updatingCandidateId, newStatus, statusNotes);
      setCandidates((prev) =>
        prev.map((c) => (c.candidate_id === updated.candidate_id ? updated : c))
      );
      if (activeEvidence && activeEvidence.candidate_id === updated.candidate_id) {
        // Refresh active evidence drawer
        const refreshedEv = await fetchCandidateEvidence(updated.candidate_id);
        setActiveEvidence(refreshedEv);
      }
      setFeedback(`Status updated to "${newStatus}" for candidate ${updatingCandidateId}`);
      setTimeout(() => setFeedback(null), 4000);
      setUpdatingCandidateId(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update status';
      setError(msg);
    } finally {
      setSubmittingStatus(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 p-6 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20 mb-2">
              <FileCheck className="h-3.5 w-3.5" />
              Unified Security Triage & Audit History
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Evidence Trail & Investigations
            </h1>
            <p className="mt-1 text-xs text-slate-400 max-w-2xl leading-relaxed">
              Examine explainable threat signals, verified collection timestamps, source attribution,
              and immutable audit trails across all social media accounts and mobile application listings.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadCandidates}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 px-3.5 py-2 text-xs font-medium text-slate-200 transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
              Refresh Triage
            </button>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {feedback && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-3.5 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>{feedback}</span>
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3.5 text-xs text-rose-300 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-300">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by candidate name, handle, package ID, or developer..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white transition shrink-0"
          >
            Search Records
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800/80 text-xs">
          {/* Brand select */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Brand:</span>
            <select
              value={selectedBrandId}
              onChange={(e) => {
                setSelectedBrandId(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Brands</option>
              {brands.map((b) => (
                <option key={b.brand_id} value={b.brand_id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          {/* Type select */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Types</option>
              <option value="social_profile">Social Profiles</option>
              <option value="app_listing">Mobile App Listings</option>
            </select>
          </div>

          {/* Status select */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="new">New / Unreviewed</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positive</option>
            </select>
          </div>

          {/* Severity select */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Severities</option>
              <option value="Critical">Critical (85–100)</option>
              <option value="High">High (70–84)</option>
              <option value="Medium">Medium (40–69)</option>
              <option value="Low">Low (&lt; 40)</option>
              <option value="Review Required">Review Required</option>
            </select>
          </div>

          {/* Source select */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Source:</span>
            <select
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Provenance</option>
              <option value="live_connector">Live Connector</option>
              <option value="manual">Manual Entry</option>
              <option value="demo">Demo Seed</option>
            </select>
          </div>

          {/* Include Official Toggle */}
          <label className="flex items-center gap-2 cursor-pointer ml-auto text-slate-400 hover:text-slate-300">
            <input
              type="checkbox"
              checked={includeOfficial}
              onChange={(e) => {
                setIncludeOfficial(e.target.checked);
                setPage(1);
              }}
              className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-0"
            />
            <span className="text-[11px]">Include Excluded Official Assets</span>
          </label>
        </div>
      </div>

      {/* Candidate List Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <span className="font-semibold text-white">{candidates.length}</span> of{' '}
            <span className="font-semibold text-white">{total}</span> candidates
          </div>
          <div className="text-slate-500">
            Page {page} of {totalPages || 1}
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
            <RefreshCw className="h-5 w-5 animate-spin text-indigo-400" />
            <span>Loading candidates from MongoDB Atlas...</span>
          </div>
        ) : candidates.length === 0 ? (
          <div className="py-16 text-center text-xs text-slate-500">
            No candidates match your active filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-semibold">Asset Type</th>
                  <th className="py-3 px-4 font-semibold">Candidate Identity</th>
                  <th className="py-3 px-4 font-semibold">Threat Score</th>
                  <th className="py-3 px-4 font-semibold">Severity</th>
                  <th className="py-3 px-4 font-semibold">Provenance</th>
                  <th className="py-3 px-4 font-semibold">Investigation Status</th>
                  <th className="py-3 px-4 text-right font-semibold">Triage Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {candidates.map((cand) => (
                  <tr key={cand.candidate_id} className="hover:bg-slate-800/20 transition">
                    {/* Asset Type */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                        {cand.candidate_type === 'app_listing' ? (
                          <Smartphone className="h-4 w-4 text-indigo-400 shrink-0" />
                        ) : (
                          <Share2 className="h-4 w-4 text-sky-400 shrink-0" />
                        )}
                        <span className="capitalize">{cand.platform || cand.store || 'public'}</span>
                      </div>
                    </td>

                    {/* Candidate Identity */}
                    <td className="py-3 px-4 font-medium text-white max-w-xs">
                      <div className="truncate font-semibold">
                        {cand.candidate_name || cand.app_name || cand.display_name}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono truncate">
                        {cand.handle
                          ? `@${cand.handle}`
                          : cand.package_or_bundle_id || cand.canonical_profile_url || ''}
                      </div>
                      {cand.publisher_or_developer && (
                        <div className="text-[10px] text-slate-500 truncate">
                          Publisher: {cand.publisher_or_developer}
                        </div>
                      )}
                    </td>

                    {/* Threat Score */}
                    <td className="py-3 px-4">
                      {cand.classification === 'OFFICIAL_EXCLUDED' ? (
                        <span className="font-mono font-bold text-emerald-400">0</span>
                      ) : (
                        <div>
                          <span className="font-mono font-bold text-slate-100">{cand.score}</span>
                          <span className="text-[10px] text-slate-500">/100</span>
                        </div>
                      )}
                    </td>

                    {/* Severity */}
                    <td className="py-3 px-4">
                      {cand.classification === 'OFFICIAL_EXCLUDED' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                          <CheckCircle2 className="h-3 w-3" />
                          Official Excluded
                        </span>
                      ) : (
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
                          {cand.classification === 'REVIEW_REQUIRED' ? 'Review Required' : cand.severity}
                        </span>
                      )}
                    </td>

                    {/* Provenance */}
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          cand.source_type === 'live_connector'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                            : cand.source_type === 'manual'
                            ? 'bg-indigo-950/60 text-indigo-400 border border-indigo-800/40'
                            : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                        }`}
                      >
                        {cand.source_type === 'live_connector'
                          ? 'Live Connector'
                          : cand.source_type === 'manual'
                          ? 'Manual'
                          : 'Demo Seed'}
                      </span>
                    </td>

                    {/* Investigation Status */}
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium capitalize ${
                          cand.investigation_status === 'resolved'
                            ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/30'
                            : cand.investigation_status === 'investigating'
                            ? 'bg-amber-950/40 text-amber-300 border border-amber-800/30'
                            : cand.investigation_status === 'false_positive'
                            ? 'bg-slate-800 text-slate-300 border border-slate-700'
                            : 'bg-slate-800/60 text-slate-300 border border-slate-700/60'
                        }`}
                      >
                        {cand.investigation_status === 'false_positive'
                          ? 'False Positive'
                          : cand.investigation_status || 'New'}
                      </span>
                      {cand.status_updated_at && (
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {new Date(cand.status_updated_at).toLocaleDateString()}
                        </div>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => handleOpenEvidence(cand.candidate_id)}
                          className="inline-flex items-center gap-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 px-2 py-1 text-[11px] font-medium text-slate-200 transition"
                          title="Inspect Evidence Trail"
                        >
                          <Eye className="h-3 w-3 text-indigo-400" />
                          Evidence
                        </button>
                        <button
                          onClick={() => handleOpenStatusModal(cand)}
                          className="inline-flex items-center gap-1 rounded bg-indigo-600/80 hover:bg-indigo-600 px-2 py-1 text-[11px] font-semibold text-white transition"
                          title="Update Investigation Lifecycle"
                        >
                          Status
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 rounded border border-slate-700 px-2.5 py-1 disabled:opacity-40 hover:bg-slate-800"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 rounded border border-slate-700 px-2.5 py-1 disabled:opacity-40 hover:bg-slate-800"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Evidence Trail Modal / Drawer */}
      {activeEvidence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-3xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl p-6 space-y-5 my-8">
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      activeEvidence.source_type === 'live_connector'
                        ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                        : activeEvidence.source_type === 'manual'
                        ? 'bg-indigo-950/60 text-indigo-400 border border-indigo-800/40'
                        : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                    }`}
                  >
                    {activeEvidence.source_type === 'live_connector'
                      ? 'Live Connector'
                      : activeEvidence.source_type === 'manual'
                      ? 'Manual Entry'
                      : 'Demo Seed'}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    ID: {activeEvidence.candidate_id}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-white">
                  {activeEvidence.candidate_name}
                </h2>
                <div className="text-xs text-slate-400 font-mono mt-0.5">
                  Platform: {activeEvidence.platform} | Connector: {activeEvidence.connector_id || 'manual'}
                </div>
              </div>
              <button
                onClick={() => setActiveEvidence(null)}
                className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Assessment Summary Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/60 rounded-xl p-3 border border-slate-800 text-xs">
              <div>
                <span className="text-[11px] text-slate-400">Deterministic Score</span>
                <div className="text-xl font-extrabold text-white mt-0.5">
                  {activeEvidence.classification === 'OFFICIAL_EXCLUDED' ? (
                    <span className="text-emerald-400">0 (Excluded)</span>
                  ) : (
                    <span>
                      {activeEvidence.score} <span className="text-xs text-slate-500 font-normal">/100</span>
                    </span>
                  )}
                </div>
              </div>

              <div>
                <span className="text-[11px] text-slate-400">Severity</span>
                <div className="mt-0.5 font-bold text-slate-200">
                  {activeEvidence.severity}
                </div>
              </div>

              <div>
                <span className="text-[11px] text-slate-400">Classification</span>
                <div className="mt-0.5 font-bold text-indigo-300">
                  {activeEvidence.classification}
                </div>
              </div>

              <div>
                <span className="text-[11px] text-slate-400">Evidence Completeness</span>
                <div className="mt-0.5 font-mono text-emerald-400 font-bold">
                  {(activeEvidence.evidence_completeness * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Official Exclusion Banner if present */}
            {activeEvidence.official_exclusion_reason && (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/30 p-3 text-xs text-emerald-300 flex items-start gap-2.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-emerald-200">Official Asset Exclusion Applied</div>
                  <div className="mt-0.5">{activeEvidence.official_exclusion_reason}</div>
                </div>
              </div>
            )}

            {/* External Identifiers */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                External Identifiers & Metadata
              </h3>
              <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-xs space-y-1.5 font-mono">
                {Object.entries(activeEvidence.external_identifiers).map(([k, v]) => (
                  <div key={k} className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                    <span className="text-slate-200 break-all">{v}</span>
                  </div>
                ))}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-1 border-t border-slate-800/80">
                  <span className="text-slate-500">Collection Timestamp:</span>
                  <span className="text-slate-300">{activeEvidence.collected_at || 'Recorded on ingestion'}</span>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span className="text-slate-500">Analysis Timestamp:</span>
                  <span className="text-slate-300">{activeEvidence.analyzed_at || 'Immediate'}</span>
                </div>
              </div>
            </div>

            {/* Contributing Detection Signals */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Contributing Detection Signals ({activeEvidence.signals.length})
              </h3>
              {activeEvidence.signals.length === 0 ? (
                <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-xs text-slate-500 text-center">
                  No threat signals detected.
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {activeEvidence.signals.map((sig, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800 bg-slate-950/50 p-2.5 text-xs flex items-start justify-between gap-3"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{sig.human_readable_reason}</span>
                          <span className="text-[10px] rounded bg-slate-800 px-1.5 py-0.5 text-slate-400 font-mono">
                            {sig.family}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Matched field: <span className="font-mono text-indigo-300">{sig.matched_field}</span> | Value:{' '}
                          <span className="font-mono text-slate-300">{sig.matched_value}</span>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className="font-mono font-bold text-amber-400">+{sig.points}</span>
                        <span className="text-[10px] text-slate-500">/{sig.max_points}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Audit History Timeline */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
                <span>Investigation Audit History Timeline</span>
                <span className="text-[10px] text-slate-500 font-normal">
                  {activeEvidence.investigation_history?.length || 0} transitions recorded
                </span>
              </h3>
              {activeEvidence.investigation_history && activeEvidence.investigation_history.length > 0 ? (
                <div className="space-y-2 border-l-2 border-indigo-500/40 ml-2 pl-3 py-1">
                  {activeEvidence.investigation_history.map((entry, idx) => (
                    <div key={idx} className="relative text-xs">
                      <div className="flex items-center gap-2">
                        <span className="capitalize font-semibold text-indigo-300">
                          {entry.status}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(entry.timestamp).toLocaleString()}
                        </span>
                      </div>
                      {entry.notes && (
                        <div className="mt-0.5 text-slate-300 text-[11px] bg-slate-950/50 rounded p-1.5 border border-slate-800/60">
                          {entry.notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-500">
                  Initial state: <span className="font-medium text-slate-400">{activeEvidence.investigation_status}</span>. No reviewer transitions logged yet.
                </div>
              )}
            </div>

            {/* Quick transition action within drawer */}
            <div className="border-t border-slate-800 pt-4 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Current status: <span className="font-bold text-white capitalize">{activeEvidence.investigation_status}</span>
              </span>
              <button
                onClick={() => {
                  const candMatch = candidates.find((c) => c.candidate_id === activeEvidence.candidate_id);
                  if (candMatch) {
                    handleOpenStatusModal(candMatch);
                  }
                }}
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-semibold text-white transition"
              >
                Change Investigation Status
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Update Status Modal */}
      {updatingCandidateId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileCheck className="h-4 w-4 text-indigo-400" />
                Update Investigation Lifecycle
              </h3>
              <button
                onClick={() => setUpdatingCandidateId(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleStatusSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) =>
                    setNewStatus(e.target.value as 'new' | 'investigating' | 'resolved' | 'false_positive')
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                >
                  <option value="investigating">Investigating (Active Review)</option>
                  <option value="resolved">Resolved (Takedown / Remediation Complete)</option>
                  <option value="false_positive">False Positive (Benign Variant)</option>
                  <option value="new">New (Revert to Unreviewed)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Audit Notes & Justification
                </label>
                <textarea
                  rows={3}
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  placeholder="Record rationale, ticket numbers, or takedown references..."
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setUpdatingCandidateId(null)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingStatus}
                  className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-1.5 text-xs font-semibold text-white transition disabled:opacity-50"
                >
                  {submittingStatus ? 'Persisting...' : 'Persist Transition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
