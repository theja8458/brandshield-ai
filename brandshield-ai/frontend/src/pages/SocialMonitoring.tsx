import React, { useEffect, useState } from 'react';
import {
  Share2,
  Search,
  RefreshCw,
  Plus,
  Radio,
  Sparkles,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
} from 'lucide-react';
import { fetchBrands } from '../api/brandClient';
import {
  fetchSocialCandidates,
  scanSocialMedia,
  seedSocialDemo,
  submitManualCandidate,
  updateCandidateInvestigationStatus,
  Candidate,
} from '../api/socialClient';
import { Brand } from '../types/brand';

export const SocialMonitoring: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [includeOfficial, setIncludeOfficial] = useState<boolean>(false);

  // Actions state
  const [scanning, setScanning] = useState<boolean>(false);
  const [seeding, setSeeding] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Evidence Drawer state
  const [activeEvidenceCand, setActiveEvidenceCand] = useState<Candidate | null>(null);

  // Manual Submission Modal state
  const [showManualModal, setShowManualModal] = useState<boolean>(false);
  const [manualName, setManualName] = useState<string>('');
  const [manualHandle, setManualHandle] = useState<string>('');
  const [manualUrl, setManualUrl] = useState<string>('');
  const [manualBio, setManualBio] = useState<string>('');
  const [manualLinks, setManualLinks] = useState<string>('');
  const [submittingManual, setSubmittingManual] = useState<boolean>(false);

  // Load brands on mount
  useEffect(() => {
    fetchBrands()
      .then((data) => {
        setBrands(data);
        if (data.length > 0) {
          setSelectedBrandId(data[0].brand_id);
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  const loadCandidates = async () => {
    if (!selectedBrandId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSocialCandidates({
        brand_id: selectedBrandId,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        source_type: sourceFilter || undefined,
        search: search || undefined,
        include_official: includeOfficial,
        page,
        limit: 15,
      });
      setCandidates(res.items);
      setTotal(res.total);
      setTotalPages(res.pages);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load candidates';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, [selectedBrandId, severityFilter, statusFilter, sourceFilter, includeOfficial, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadCandidates();
  };

  const handleScan = async () => {
    if (!selectedBrandId) return;
    setScanning(true);
    setError(null);
    setFeedback(null);
    try {
      const res = await scanSocialMedia(selectedBrandId);
      const bskyRes = res.source_results?.find((s: { connector_id: string }) => s.connector_id === 'bluesky');
      setFeedback(
        `Live Bluesky Scan Complete: Found ${res.total_found} profiles (${res.total_new} new, ${res.total_excluded_official} official excluded).`
      );
      if (bskyRes && !bskyRes.ok) {
        setError(`Bluesky scan warning: ${bskyRes.error}`);
      }
      await loadCandidates();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Scan execution failed';
      setError(message);
    } finally {
      setScanning(false);
    }
  };

  const handleSeedDemo = async () => {
    if (!selectedBrandId) return;
    setSeeding(true);
    setError(null);
    setFeedback(null);
    try {
      const res = await seedSocialDemo(selectedBrandId);
      setFeedback(`Seeded ${res.seeded_count} synthetic demo social candidates into Atlas.`);
      await loadCandidates();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Demo seeding failed';
      setError(message);
    } finally {
      setSeeding(false);
    }
  };

  const handleStatusChange = async (
    candidateId: string,
    newStatus: 'new' | 'investigating' | 'resolved' | 'false_positive'
  ) => {
    try {
      const updated = await updateCandidateInvestigationStatus(candidateId, newStatus);
      setCandidates((prev) =>
        prev.map((c) => (c.candidate_id === candidateId ? updated : c))
      );
      if (activeEvidenceCand?.candidate_id === candidateId) {
        setActiveEvidenceCand(updated);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update status';
      setError(message);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBrandId) return;
    setSubmittingManual(true);
    setError(null);
    try {
      const extLinks = manualLinks
        .split(',')
        .map((l) => l.trim())
        .filter(Boolean);

      const created = await submitManualCandidate({
        brand_id: selectedBrandId,
        display_name: manualName.trim(),
        handle: manualHandle.trim(),
        canonical_profile_url: manualUrl.trim() || undefined,
        bio: manualBio.trim() || undefined,
        external_links: extLinks,
      });

      setShowManualModal(false);
      setManualName('');
      setManualHandle('');
      setManualUrl('');
      setManualBio('');
      setManualLinks('');
      setFeedback(`Manual candidate '@${created.handle}' submitted and scored (${created.score}/100 - ${created.severity})!`);
      await loadCandidates();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Submission failed';
      setError(message);
    } finally {
      setSubmittingManual(false);
    }
  };

  const getSourceBadge = (sourceType: string) => {
    switch (sourceType) {
      case 'live_connector':
        return (
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-400 border border-emerald-500/20">
            LIVE CONNECTOR
          </span>
        );
      case 'manual':
        return (
          <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-400 border border-amber-500/20">
            MANUAL
          </span>
        );
      case 'demo':
        return (
          <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-400 border border-indigo-500/20">
            DEMO SEED
          </span>
        );
      default:
        return null;
    }
  };

  const getSeverityBadge = (severity: string, score: number) => {
    let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
    if (severity === 'Critical') colorClasses = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
    else if (severity === 'High') colorClasses = 'bg-orange-500/20 text-orange-300 border-orange-500/40';
    else if (severity === 'Medium') colorClasses = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    else if (severity === 'Low') colorClasses = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';

    return (
      <span className={`rounded px-2 py-0.5 text-[11px] font-bold border inline-flex items-center gap-1 ${colorClasses}`}>
        <span>{score}/100</span>
        <span className="font-normal opacity-75">({severity})</span>
      </span>
    );
  };

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case 'OFFICIAL_EXCLUDED':
        return <span className="text-[11px] text-emerald-400 font-semibold">OFFICIAL_EXCLUDED</span>;
      case 'REVIEW_REQUIRED':
        return <span className="text-[11px] text-amber-400 font-semibold">REVIEW_REQUIRED</span>;
      case 'POTENTIAL_THREAT':
        return <span className="text-[11px] text-rose-400 font-semibold">POTENTIAL_THREAT</span>;
      default:
        return <span className="text-[11px] text-slate-400">LOW_RISK</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Share2 className="h-6 w-6 text-indigo-400" />
            Social Media Monitoring
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time surveillance of Bluesky public search and seeded impersonation datasets.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Brand Selector */}
          <select
            value={selectedBrandId}
            onChange={(e) => {
              setSelectedBrandId(e.target.value);
              setPage(1);
            }}
            className="rounded-lg bg-slate-900 border border-slate-800 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
          >
            {brands.map((b) => (
              <option key={b.brand_id} value={b.brand_id}>
                Brand: {b.name}
              </option>
            ))}
          </select>

          {/* Live Scan Button */}
          <button
            onClick={handleScan}
            disabled={scanning || !selectedBrandId}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors shadow-sm"
          >
            <Radio className={`h-3.5 w-3.5 ${scanning ? 'animate-pulse' : ''}`} />
            {scanning ? 'Scanning Bluesky...' : 'Scan Bluesky (Live)'}
          </button>

          {/* Seed Demo Button */}
          <button
            onClick={handleSeedDemo}
            disabled={seeding || !selectedBrandId}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors shadow-sm"
          >
            <Sparkles className={`h-3.5 w-3.5 ${seeding ? 'animate-spin' : ''}`} />
            {seeding ? 'Seeding...' : 'Seed Demo Data'}
          </button>

          {/* Manual Entry Button */}
          <button
            onClick={() => setShowManualModal(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Manual Candidate
          </button>
        </div>
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

      {/* Filter Toolbar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by handle, name, or keywords in bio..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg bg-slate-950 border border-slate-800 pl-9 pr-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Severity Filter */}
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-2 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">Severity: All</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-2 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">Status: All</option>
              <option value="new">New</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positive</option>
            </select>

            {/* Source Filter */}
            <select
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-2 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">Source: All</option>
              <option value="live_connector">Live Connector</option>
              <option value="manual">Manual Entry</option>
              <option value="demo">Demo Seed</option>
            </select>

            {/* Include Official Checkbox */}
            <label className="inline-flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer bg-slate-950 px-2.5 py-2 rounded-lg border border-slate-800">
              <input
                type="checkbox"
                checked={includeOfficial}
                onChange={(e) => {
                  setIncludeOfficial(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-slate-700 text-indigo-600 focus:ring-0"
              />
              Show Official Excluded
            </label>

            <button
              type="submit"
              className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              Apply Filter
            </button>
          </div>
        </form>
      </div>

      {/* Candidate List / Table */}
      {loading ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-400 text-sm">
          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-indigo-400 mb-2" />
          Loading social candidates...
        </div>
      ) : candidates.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-10 text-center">
          <Share2 className="mx-auto h-10 w-10 text-slate-600 mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No Social Candidates Found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-5">
            Click <strong>Scan Bluesky (Live)</strong> to perform a public search, or <strong>Seed Demo Data</strong> to populate standard test candidates.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Candidate / Handle</th>
                  <th className="p-3.5">Source & Origin</th>
                  <th className="p-3.5">Risk Score</th>
                  <th className="p-3.5">Classification</th>
                  <th className="p-3.5">Investigation Status</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {candidates.map((cand) => (
                  <tr key={cand.candidate_id} className="hover:bg-slate-800/30 transition-colors">
                    {/* Candidate & Handle */}
                    <td className="p-3.5 max-w-xs">
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span>{cand.candidate_name}</span>
                        <span className="rounded bg-indigo-500/10 px-1 py-0.2 text-[9px] text-indigo-300 font-mono uppercase">
                          {cand.platform}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5 flex items-center gap-1">
                        <span>@{cand.handle}</span>
                        {cand.canonical_profile_url && (
                          <a
                            href={cand.canonical_profile_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-indigo-400 hover:text-indigo-300"
                          >
                            <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        )}
                      </div>
                      {cand.bio && (
                        <p className="text-[11px] text-slate-400 line-clamp-1 mt-1">{cand.bio}</p>
                      )}
                    </td>

                    {/* Source & Origin */}
                    <td className="p-3.5 whitespace-nowrap">
                      {getSourceBadge(cand.source_type)}
                      <div className="text-[10px] text-slate-500 font-mono mt-1">
                        {cand.collected_at ? new Date(cand.collected_at).toLocaleDateString() : 'N/A'}
                      </div>
                    </td>

                    {/* Score & Severity */}
                    <td className="p-3.5 whitespace-nowrap">
                      {getSeverityBadge(cand.severity, cand.score)}
                    </td>

                    {/* Classification */}
                    <td className="p-3.5 whitespace-nowrap">
                      {getClassificationBadge(cand.classification)}
                    </td>

                    {/* Investigation Status */}
                    <td className="p-3.5 whitespace-nowrap">
                      <select
                        value={cand.investigation_status}
                        onChange={(e) =>
                          handleStatusChange(
                            cand.candidate_id,
                            e.target.value as 'new' | 'investigating' | 'resolved' | 'false_positive'
                          )
                        }
                        className="rounded bg-slate-950 border border-slate-800 px-2 py-1 text-[11px] text-slate-200 focus:outline-none"
                      >
                        <option value="new">New</option>
                        <option value="investigating">Investigating</option>
                        <option value="resolved">Resolved</option>
                        <option value="false_positive">False Positive</option>
                      </select>
                    </td>

                    {/* Actions */}
                    <td className="p-3.5 text-right whitespace-nowrap">
                      <button
                        onClick={() => setActiveEvidenceCand(cand)}
                        className="inline-flex items-center gap-1 rounded bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700 transition-colors border border-slate-700"
                      >
                        <Eye className="h-3 w-3 text-indigo-400" />
                        Evidence ({cand.signals.length})
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 text-xs text-slate-400 bg-slate-950/40">
            <div>
              Showing <span className="font-semibold text-white">{candidates.length}</span> of{' '}
              <span className="font-semibold text-white">{total}</span> candidates
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1 rounded hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-slate-300">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1 rounded hover:bg-slate-800 disabled:opacity-40"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Drawer / Modal */}
      {activeEvidenceCand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">
                    {activeEvidenceCand.candidate_name}
                  </h3>
                  {getSourceBadge(activeEvidenceCand.source_type)}
                </div>
                <div className="text-xs font-mono text-slate-400 mt-0.5">
                  @{activeEvidenceCand.handle} • ID: {activeEvidenceCand.candidate_id}
                </div>
              </div>
              <button
                onClick={() => setActiveEvidenceCand(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Score Summary Banner */}
            <div className="flex items-center justify-between rounded-lg bg-slate-950 p-3.5 border border-slate-800 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Final Risk Assessment</span>
                <div className="font-bold text-white text-sm flex items-center gap-2 mt-0.5">
                  {getSeverityBadge(activeEvidenceCand.severity, activeEvidenceCand.score)}
                  <span>•</span>
                  {getClassificationBadge(activeEvidenceCand.classification)}
                </div>
              </div>

              <div className="text-right text-[11px] text-slate-400 font-mono">
                <div>Completeness: {(activeEvidenceCand.evidence_completeness * 100).toFixed(0)}%</div>
                <div>Status: <span className="text-indigo-300 font-bold capitalize">{activeEvidenceCand.investigation_status}</span></div>
              </div>
            </div>

            {/* Signal Breakdown */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Deterministic Signal Attributions ({activeEvidenceCand.signals.length})
              </h4>

              {activeEvidenceCand.signals.length === 0 ? (
                <div className="rounded bg-slate-950/50 p-3 text-xs text-slate-500 italic">
                  No threat signals triggered (score = 0).
                </div>
              ) : (
                <div className="space-y-2">
                  {activeEvidenceCand.signals.map((sig, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
                          {sig.family.toUpperCase()} : {sig.id}
                        </span>
                        <span className="rounded bg-indigo-950/80 px-2 py-0.5 font-mono text-[11px] font-bold text-indigo-300 border border-indigo-800/50">
                          +{sig.points} / {sig.max_points} pts
                        </span>
                      </div>
                      <div className="text-slate-300 text-[11px]">
                        <strong>Reason:</strong> {sig.human_readable_reason}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        Field: {sig.matched_field} = "{sig.matched_value}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Missing Evidence Warnings */}
            {activeEvidenceCand.missing_evidence?.length > 0 && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-950/20 p-3 text-xs space-y-1">
                <span className="font-semibold text-amber-300 flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5" /> Missing Evidence Warnings
                </span>
                <ul className="list-disc list-inside text-[11px] text-amber-200/80">
                  {activeEvidenceCand.missing_evidence.map((warn, idx) => (
                    <li key={idx}>{warn}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Close Button */}
            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setActiveEvidenceCand(null)}
                className="rounded bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close Evidence
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Candidate Submission Modal */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="h-4 w-4 text-indigo-400" />
                Submit Manual Social Candidate
              </h3>
              <button onClick={() => setShowManualModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">Display Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. NovaPay Support"
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Handle *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. novapay_support"
                  value={manualHandle}
                  onChange={(e) => setManualHandle(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Profile URL</label>
                <input
                  type="url"
                  placeholder="https://bsky.app/profile/..."
                  value={manualUrl}
                  onChange={(e) => setManualUrl(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Bio / Description</label>
                <textarea
                  rows={2}
                  placeholder="Bio or suspicious phrasing"
                  value={manualBio}
                  onChange={(e) => setManualBio(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">External Links (comma-separated)</label>
                <input
                  type="text"
                  placeholder="https://novapay-claim.example"
                  value={manualLinks}
                  onChange={(e) => setManualLinks(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  className="rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingManual}
                  className="rounded bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  {submittingManual ? 'Evaluating...' : 'Submit & Analyze'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
