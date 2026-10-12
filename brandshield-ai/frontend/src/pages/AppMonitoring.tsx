import React, { useEffect, useState } from 'react';
import {
  Smartphone,
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
  Layers,
  AlertCircle,
  Building,
} from 'lucide-react';
import { fetchBrands } from '../api/brandClient';
import {
  fetchAppCandidates,
  scanAppStore,
  seedAppDemo,
  submitManualAppCandidate,
  updateAppInvestigationStatus,
} from '../api/appClient';
import { Candidate } from '../api/socialClient';
import { Brand } from '../types/brand';

export const AppMonitoring: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [scanning, setScanning] = useState<boolean>(false);
  const [seeding, setSeeding] = useState<boolean>(false);
  const [scanResult, setScanResult] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState<string>('');
  const [storeFilter, setStoreFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);

  // Evidence Drawer & Manual Modal
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [isManualModalOpen, setIsManualModalOpen] = useState<boolean>(false);
  const [manualForm, setManualForm] = useState({
    app_name: '',
    store: 'apple_app_store',
    package_or_bundle_id: '',
    publisher_or_developer: '',
    publisher_id: '',
    canonical_listing_url: '',
    description: '',
  });
  const [manualSubmitting, setManualSubmitting] = useState<boolean>(false);

  // Initial load: Brands
  useEffect(() => {
    async function loadBrands() {
      try {
        const brandList = await fetchBrands();
        setBrands(brandList);
        if (brandList.length > 0) {
          setSelectedBrandId(brandList[0].brand_id);
        }
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to load brand profiles.');
      }
    }
    loadBrands();
  }, []);

  // Fetch Candidates on filter change
  useEffect(() => {
    if (!selectedBrandId) return;
    loadCandidates();
  }, [selectedBrandId, search, storeFilter, severityFilter, statusFilter, sourceFilter, page]);

  async function loadCandidates() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetchAppCandidates({
        brand_id: selectedBrandId,
        store: storeFilter || undefined,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        source_type: sourceFilter || undefined,
        search: search || undefined,
        page,
        limit: 15,
      });
      setCandidates(res.items);
      setTotalPages(res.pages);
      setTotalItems(res.total);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error fetching mobile app candidates.');
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    if (!selectedBrandId) return;
    setScanning(true);
    setErrorMessage(null);
    setScanResult(null);
    try {
      const res = await scanAppStore(selectedBrandId);
      setScanResult(res);
      await loadCandidates();
    } catch (err: any) {
      setErrorMessage(err.message || 'Apple App Store scan failed.');
    } finally {
      setScanning(false);
    }
  }

  async function handleSeedDemo() {
    if (!selectedBrandId) return;
    setSeeding(true);
    setErrorMessage(null);
    try {
      await seedAppDemo(selectedBrandId);
      await loadCandidates();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to seed synthetic app dataset.');
    } finally {
      setSeeding(false);
    }
  }

  async function handleStatusChange(candidateId: string, newStatus: any) {
    try {
      const updated = await updateAppInvestigationStatus(candidateId, newStatus);
      setCandidates((prev) =>
        prev.map((c) => (c.candidate_id === candidateId ? updated : c))
      );
      if (selectedCandidate && selectedCandidate.candidate_id === candidateId) {
        setSelectedCandidate(updated);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update investigation status.');
    }
  }

  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedBrandId || !manualForm.app_name.trim()) return;
    setManualSubmitting(true);
    try {
      await submitManualAppCandidate(selectedBrandId, manualForm);
      setIsManualModalOpen(false);
      setManualForm({
        app_name: '',
        store: 'apple_app_store',
        package_or_bundle_id: '',
        publisher_or_developer: '',
        publisher_id: '',
        canonical_listing_url: '',
        description: '',
      });
      await loadCandidates();
    } catch (err: any) {
      setErrorMessage(err.message || 'Manual app submission failed.');
    } finally {
      setManualSubmitting(false);
    }
  }

  const selectedBrand = brands.find((b) => b.brand_id === selectedBrandId);

  return (
    <div className="space-y-6">
      {/* Top Header & Brand Selector */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Smartphone className="w-6 h-6 text-indigo-400" />
            Mobile App Store Monitoring
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated surveillance of rogue iOS apps via Apple iTunes API, bundle ID conflicts, and publisher mismatches.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-slate-400">Target Brand:</label>
          <select
            id="brand-select"
            value={selectedBrandId}
            onChange={(e) => {
              setSelectedBrandId(e.target.value);
              setPage(1);
            }}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          >
            {brands.map((b) => (
              <option key={b.brand_id} value={b.brand_id}>
                {b.name} ({b.brand_id})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            id="btn-scan-appstore"
            onClick={handleScan}
            disabled={scanning || !selectedBrandId}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
          >
            {scanning ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-white" />
            ) : (
              <Radio className="w-3.5 h-3.5 text-white" />
            )}
            {scanning ? 'Querying Apple App Store...' : 'Scan Apple App Store'}
          </button>

          <button
            id="btn-seed-app-demo"
            onClick={handleSeedDemo}
            disabled={seeding || !selectedBrandId}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition-all"
            title="Seeds repeatable synthetic app candidates from the official dataset"
          >
            {seeding ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            )}
            Load App Demo Dataset
          </button>
        </div>

        <button
          id="btn-manual-app-submit"
          onClick={() => setIsManualModalOpen(true)}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition-all"
        >
          <Plus className="w-3.5 h-3.5 text-indigo-400" />
          Submit Rogue App
        </button>
      </div>

      {/* Error & Scan Summary Banners */}
      {errorMessage && (
        <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center justify-between text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {scanResult && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-medium text-slate-200">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Apple App Store Scan Completed</span>
            </div>
            <span className="text-slate-400">Total Scanned: {scanResult.total_found}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-2 border-t border-slate-800">
            {scanResult.source_results?.map((s: any) => (
              <div key={s.connector_id} className="p-2.5 bg-slate-950/60 rounded border border-slate-800/80">
                <div className="flex items-center justify-between font-mono text-[11px] text-slate-300">
                  <span>{s.display_name}</span>
                  <span className={s.ok ? 'text-emerald-400' : 'text-rose-400'}>
                    {s.ok ? 'OK' : 'ERROR'}
                  </span>
                </div>
                <div className="mt-1 text-[11px] text-slate-400 flex gap-3">
                  <span>Found: {s.candidates_found}</span>
                  <span>New: {s.new_candidates}</span>
                  <span>Excluded: {s.excluded_official}</span>
                </div>
                {s.error && (
                  <p className="mt-1 text-[10px] text-rose-400 truncate">{s.error}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 bg-slate-900/40 p-3.5 border border-slate-800/80 rounded-xl">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search app, bundle, publisher..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-900 border border-slate-800 text-slate-200 pl-8 pr-3 py-1.5 text-xs rounded-lg focus:outline-none focus:border-indigo-500"
          />
        </div>

        <select
          value={storeFilter}
          onChange={(e) => {
            setStoreFilter(e.target.value);
            setPage(1);
          }}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All App Stores</option>
          <option value="apple_app_store">Apple App Store (iOS)</option>
        </select>

        <select
          value={severityFilter}
          onChange={(e) => {
            setSeverityFilter(e.target.value);
            setPage(1);
          }}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Severities</option>
          <option value="Critical">Critical (85-100)</option>
          <option value="High">High (70-84)</option>
          <option value="Medium">Medium (40-69)</option>
          <option value="Low">Low (&lt;40)</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Investigation Statuses</option>
          <option value="new">New / Unreviewed</option>
          <option value="investigating">Investigating</option>
          <option value="resolved">Resolved</option>
          <option value="false_positive">False Positive</option>
        </select>

        <select
          value={sourceFilter}
          onChange={(e) => {
            setSourceFilter(e.target.value);
            setPage(1);
          }}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Data Sources</option>
          <option value="live_connector">Live Connector</option>
          <option value="demo">Demo Seed</option>
          <option value="manual">Manual Submission</option>
        </select>
      </div>

      {/* Main Candidates Table / Content */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-3.5 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>
            Showing <strong className="text-white">{candidates.length}</strong> of{' '}
            <strong className="text-white">{totalItems}</strong> recorded app listings
          </span>
          <button
            onClick={loadCandidates}
            className="flex items-center gap-1 hover:text-white transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-7 h-7 text-indigo-400 animate-spin" />
            <p className="text-xs text-slate-400">Loading app store findings...</p>
          </div>
        ) : candidates.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center text-center px-4">
            <Smartphone className="w-10 h-10 text-slate-600 mb-2" />
            <p className="text-sm font-medium text-slate-300">No App Listings Found</p>
            <p className="text-xs text-slate-500 max-w-sm mt-1">
              No matching rogue apps for {selectedBrand?.name || 'this brand'}. Trigger an Apple App Store scan or load the demo dataset.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/70 text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">App & Identity</th>
                  <th className="py-3 px-4">Publisher / Developer</th>
                  <th className="py-3 px-4">Store</th>
                  <th className="py-3 px-4">Provenance</th>
                  <th className="py-3 px-4">Risk & Severity</th>
                  <th className="py-3 px-4">Investigation</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {candidates.map((cand) => {
                  const severityColors: Record<string, string> = {
                    Critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
                    High: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
                    Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                    Low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
                  };

                  const isReviewRequired = cand.classification === 'REVIEW_REQUIRED';
                  const isOfficialExcluded = cand.classification === 'OFFICIAL_EXCLUDED';

                  // Check if publisher mismatch signal is present
                  const hasPubMismatch = cand.signals?.some(
                    (s) => s.id === 'publisher_mismatch' || s.id === 'publisher_missing'
                  );

                  return (
                    <tr key={cand.candidate_id} className="hover:bg-slate-800/30 transition-colors">
                      {/* App & Identity */}
                      <td className="py-3 px-4">
                        <div className="flex items-start gap-3">
                          {cand.image_url ? (
                            <img
                              src={cand.image_url}
                              alt=""
                              className="w-9 h-9 rounded-xl object-cover bg-slate-800 border border-slate-700/80 shadow-sm flex-shrink-0"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                          ) : (
                            <div className="w-9 h-9 rounded-xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-400 flex-shrink-0">
                              <Smartphone className="w-4 h-4" />
                            </div>
                          )}
                          <div className="space-y-0.5">
                            <span className="font-semibold text-white hover:text-indigo-300 transition-colors block">
                              {cand.app_name || cand.candidate_name}
                            </span>
                            <span className="font-mono text-[10px] text-slate-400 block truncate max-w-[200px]" title={cand.package_or_bundle_id}>
                              {cand.package_or_bundle_id || 'Bundle ID unrecorded'}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Publisher / Developer */}
                      <td className="py-3 px-4">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <Building className="w-3 h-3 text-slate-500" />
                            <span className="text-slate-200 truncate max-w-[170px]" title={cand.publisher_or_developer}>
                              {cand.publisher_or_developer || '[Unknown Publisher]'}
                            </span>
                          </div>
                          {hasPubMismatch && (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">
                              <AlertCircle className="w-2.5 h-2.5" /> Mismatch
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Store */}
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 bg-slate-800 text-slate-300 border border-slate-700/80 rounded text-[11px] font-mono">
                          Apple App Store
                        </span>
                      </td>

                      {/* Source Provenance Badge */}
                      <td className="py-3 px-4">
                        {cand.source_type === 'live_connector' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            LIVE CONNECTOR
                          </span>
                        )}
                        {cand.source_type === 'demo' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            <Sparkles className="w-2.5 h-2.5 text-amber-400" />
                            DEMO SEED
                          </span>
                        )}
                        {cand.source_type === 'manual' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                            MANUAL
                          </span>
                        )}
                      </td>

                      {/* Threat Score & Severity */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-white">
                            {cand.score}
                            <span className="text-[10px] text-slate-500">/100</span>
                          </span>

                          {isOfficialExcluded ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                              OFFICIAL EXCLUDED
                            </span>
                          ) : isReviewRequired ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                              REVIEW REQUIRED
                            </span>
                          ) : (
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                                severityColors[cand.severity] || severityColors.Low
                              }`}
                            >
                              {cand.severity}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Investigation Status Selector */}
                      <td className="py-3 px-4">
                        <select
                          value={cand.investigation_status}
                          onChange={(e) => handleStatusChange(cand.candidate_id, e.target.value)}
                          className="bg-slate-950 border border-slate-800 text-slate-300 text-[11px] rounded px-2 py-1 focus:outline-none focus:border-indigo-500"
                        >
                          <option value="new">New</option>
                          <option value="investigating">Investigating</option>
                          <option value="resolved">Resolved</option>
                          <option value="false_positive">False Positive</option>
                        </select>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setSelectedCandidate(cand)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-[11px] font-medium rounded border border-slate-700 transition-colors"
                        >
                          <Eye className="w-3 h-3" />
                          Evidence
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Bounded Pagination Controls */}
        <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>
            Page <strong className="text-white">{page}</strong> of{' '}
            <strong className="text-white">{totalPages}</strong>
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Sliding Evidence Drawer */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/80 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
          <div className="w-full max-w-xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto p-6 space-y-6 shadow-2xl">
            {/* Drawer Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                  Candidate ID: {selectedCandidate.candidate_id}
                </span>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Smartphone className="w-5 h-5 text-indigo-400" />
                  {selectedCandidate.app_name || selectedCandidate.candidate_name}
                </h2>
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-xs text-slate-400 font-mono">
                    Bundle: {selectedCandidate.package_or_bundle_id || '[Not specified]'}
                  </span>
                  {selectedCandidate.canonical_listing_url && (
                    <a
                      href={selectedCandidate.canonical_listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-400 hover:underline flex items-center gap-1"
                    >
                      Store Listing <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Score & Verdict Banner */}
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between">
              <div>
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                  Threat Suspiciousness Score
                </span>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-2xl font-bold font-mono text-white">
                    {selectedCandidate.score}
                  </span>
                  <span className="text-xs text-slate-500">/ 100</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700 ml-2">
                    {selectedCandidate.severity}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                  Safety Classification
                </span>
                <span className="font-mono text-xs text-slate-200 mt-1 inline-block">
                  {selectedCandidate.classification}
                </span>
              </div>
            </div>

            {/* Publisher Evidence Section */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase text-slate-400 tracking-wider flex items-center gap-2">
                <Building className="w-3.5 h-3.5 text-indigo-400" />
                Developer & Publisher Identity
              </h3>
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Developer Name:</span>
                  <span className="text-slate-200 font-medium">
                    {selectedCandidate.publisher_or_developer || '[Missing from listing]'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Developer ID:</span>
                  <span className="text-slate-200 font-mono">
                    {selectedCandidate.publisher_id || '[None]'}
                  </span>
                </div>
              </div>
            </div>

            {/* Heuristic Signals Triggered */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase text-slate-400 tracking-wider flex items-center gap-2">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                Triggered Heuristic Detection Signals ({selectedCandidate.signals?.length || 0})
              </h3>
              {selectedCandidate.signals && selectedCandidate.signals.length > 0 ? (
                <div className="space-y-2">
                  {selectedCandidate.signals.map((sig, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200 capitalize">
                          {sig.family.replace('_', ' ')}: {sig.id}
                        </span>
                        <span className="font-mono font-bold text-amber-400">
                          +{sig.points} pts
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px] leading-relaxed">
                        {sig.human_readable_reason}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 pt-1">
                        <span>Matched: {sig.matched_field}</span>
                        <span>•</span>
                        <span className="truncate max-w-[250px]">Value: {sig.matched_value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded-lg border border-slate-800/60">
                  No threat signals triggered. Asset matches legitimate benign parameters.
                </p>
              )}
            </div>

            {/* Missing Evidence / Uncertainty */}
            {selectedCandidate.missing_evidence && selectedCandidate.missing_evidence.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase text-amber-400 tracking-wider flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  Investigation Caveats & Missing Data
                </h3>
                <ul className="list-disc list-inside space-y-1 text-xs text-slate-400 bg-amber-500/5 p-3 rounded-lg border border-amber-500/20">
                  {selectedCandidate.missing_evidence.map((warn, i) => (
                    <li key={i}>{warn}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Description / Content */}
            {selectedCandidate.description && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
                  Store Description
                </h3>
                <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg text-xs text-slate-300 max-h-36 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                  {selectedCandidate.description}
                </div>
              </div>
            )}

            {/* Data Provenance & Audit Trail */}
            <div className="space-y-2 pt-2 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
              <div className="flex justify-between">
                <span>Source Type:</span>
                <span className="text-slate-200">{selectedCandidate.source_type}</span>
              </div>
              <div className="flex justify-between">
                <span>Connector ID:</span>
                <span className="text-slate-200">{selectedCandidate.connector_id || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span>Collection Time:</span>
                <span className="text-slate-200">{selectedCandidate.collected_at || 'N/A'}</span>
              </div>
              {selectedCandidate.image_hash && (
                <div className="flex justify-between">
                  <span>Icon pHash:</span>
                  <span className="text-slate-200">{selectedCandidate.image_hash}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Manual Submission Modal */}
      {isManualModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                Submit Rogue Mobile App
              </h2>
              <button
                onClick={() => setIsManualModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-300 font-medium">App Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. NovaPay Wallet Pro"
                  value={manualForm.app_name}
                  onChange={(e) => setManualForm({ ...manualForm, app_name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">Store Platform</label>
                  <select
                    value={manualForm.store}
                    onChange={(e) => setManualForm({ ...manualForm, store: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-300 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="apple_app_store">Apple App Store (iOS)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">Package / Bundle ID</label>
                  <input
                    type="text"
                    placeholder="com.rogue.novapay"
                    value={manualForm.package_or_bundle_id}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, package_or_bundle_id: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">Developer / Publisher Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Rogue App Studio"
                    value={manualForm.publisher_or_developer}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, publisher_or_developer: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">Developer ID</label>
                  <input
                    type="text"
                    placeholder="e.g. 192837465"
                    value={manualForm.publisher_id}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, publisher_id: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-medium">Store Listing URL</label>
                <input
                  type="url"
                  placeholder="https://apps.apple.com/app/id..."
                  value={manualForm.canonical_listing_url}
                  onChange={(e) =>
                    setManualForm({ ...manualForm, canonical_listing_url: e.target.value })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-medium">App Description / Bio</label>
                <textarea
                  rows={3}
                  placeholder="App store description text..."
                  value={manualForm.description}
                  onChange={(e) => setManualForm({ ...manualForm, description: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsManualModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={manualSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg font-semibold flex items-center gap-2"
                >
                  {manualSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Submit & Analyze
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
