import React, { useEffect, useState } from 'react';
import {
  Building2,
  ShieldCheck,
  Globe,
  Share2,
  Smartphone,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Plus,
  RefreshCw,
  ExternalLink,
  Tag,
  FileCheck,
  Copy,
  Info,
  X,
} from 'lucide-react';
import {
  fetchBrands,
  seedNovaPayBrand,
  createBrand,
  uploadBrandLogo,
  evaluateAssetSafety,
} from '../api/brandClient';
import { Brand, OfficialEvaluationResult } from '../types/brand';

export const BrandProfile: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<Brand | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [seeding, setSeeding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Logo upload state
  const [uploadingLogo, setUploadingLogo] = useState<boolean>(false);

  // Safety Guard Tester state
  const [testerType, setTesterType] = useState<'domain' | 'social_profile' | 'app_listing'>('domain');
  const [testerHandle, setTesterHandle] = useState<string>('novapay.synthetic.example');
  const [testerUrl, setTesterUrl] = useState<string>('paypal.com');
  const [testerAccountOrPubId, setTesterAccountOrPubId] = useState<string>('did:synthetic:novapay-official-0001');
  const [testerBundleId, setTesterBundleId] = useState<string>('example.synthetic.novapay.wallet');
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evalResult, setEvalResult] = useState<OfficialEvaluationResult | null>(null);

  // New Brand Modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newBrandName, setNewBrandName] = useState<string>('');
  const [newBrandDesc, setNewBrandDesc] = useState<string>('');
  const [newBrandWebsite, setNewBrandWebsite] = useState<string>('https://');
  const [newBrandDomains, setNewBrandDomains] = useState<string>('');
  const [creating, setCreating] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Synthetic URL Preview Modal state
  const [previewModal, setPreviewModal] = useState<{
    title: string;
    url: string;
    type: 'social' | 'app' | 'website';
    identifierLabel?: string;
    identifierValue?: string;
    handleOrBundle?: string;
    platformOrStore?: string;
  } | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false);

  const handleOpenUrl = (
    e: React.MouseEvent,
    data: {
      title: string;
      url: string;
      type: 'social' | 'app' | 'website';
      identifierLabel?: string;
      identifierValue?: string;
      handleOrBundle?: string;
      platformOrStore?: string;
    }
  ) => {
    // If it's a synthetic RFC-2606 .example domain, intercept to show sandbox preview instead of browser DNS error
    if (data.url.includes('.example')) {
      e.preventDefault();
      setCopiedUrl(false);
      setPreviewModal(data);
    }
  };

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedUrl(true);
    setSuccessMsg('URL copied to clipboard!');
    setTimeout(() => {
      setCopiedUrl(false);
      setSuccessMsg(null);
    }, 2500);
  };

  const handleTestInSafetyGuard = (data: {
    title: string;
    url: string;
    type: 'social' | 'app' | 'website';
    identifierLabel?: string;
    identifierValue?: string;
    handleOrBundle?: string;
    platformOrStore?: string;
  }) => {
    if (data.type === 'social') {
      setTesterType('social_profile');
      if (data.handleOrBundle) setTesterHandle(data.handleOrBundle);
      setTesterUrl(data.url);
      if (data.identifierValue) setTesterAccountOrPubId(data.identifierValue);
    } else if (data.type === 'app') {
      setTesterType('app_listing');
      if (data.handleOrBundle) setTesterBundleId(data.handleOrBundle);
      setTesterUrl(data.url);
      if (data.identifierValue) setTesterAccountOrPubId(data.identifierValue);
    }
    setPreviewModal(null);
    setTimeout(() => {
      handleRunSafetyTest();
    }, 100);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBrands();
      setBrands(data);
      if (data.length > 0) {
        setSelectedBrand(data[0]);
      } else {
        setSelectedBrand(null);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to backend';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSeedNovaPay = async () => {
    setSeeding(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const seeded = await seedNovaPayBrand();
      setSuccessMsg('Successfully seeded fictional brand NovaPay into MongoDB Atlas!');
      await loadData();
      setSelectedBrand(seeded);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Seeding failed';
      setError(message);
    } finally {
      setSeeding(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedBrand || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploadingLogo(true);
    setError(null);
    try {
      const updated = await uploadBrandLogo(selectedBrand.brand_id, file);
      setSelectedBrand(updated);
      setSuccessMsg('Official logo uploaded and perceptual hash (pHash) computed successfully!');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Logo upload failed';
      setError(message);
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleRunSafetyTest = async () => {
    if (!selectedBrand) return;
    setEvaluating(true);
    setEvalResult(null);

    const payload =
      testerType === 'domain'
        ? {
            candidate_type: 'domain',
            domain: testerUrl.trim(),
            url: testerUrl.trim(),
          }
        : testerType === 'social_profile'
        ? {
            candidate_type: 'social_profile',
            platform: 'bluesky',
            handle: testerHandle,
            canonical_profile_url: testerUrl,
            stable_account_id: testerAccountOrPubId,
          }
        : {
            candidate_type: 'app_listing',
            store: 'apple_app_store',
            package_or_bundle_id: testerBundleId,
            listing_url: testerUrl,
            publisher_id: testerAccountOrPubId,
          };

    try {
      const res = await evaluateAssetSafety(selectedBrand.brand_id, payload);
      setEvalResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Safety check failed';
      setError(message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleCreateBrand = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setFormError(null);

    try {
      let domains = newBrandDomains
        .split(',')
        .map((d) => d.trim().toLowerCase())
        .filter(Boolean);

      if (domains.length === 0 && newBrandWebsite.trim()) {
        try {
          const parsed = new URL(newBrandWebsite.trim());
          const host = parsed.hostname.replace(/^www\./, '').toLowerCase();
          if (host) domains = [host];
        } catch {
          // fallback
        }
      }

      const created = await createBrand({
        name: newBrandName.trim(),
        description: newBrandDesc.trim(),
        official_website: newBrandWebsite.trim(),
        official_domains: domains,
        aliases: [],
        keywords: [newBrandName.toLowerCase()],
        safe_list: [],
        official_social_assets: [],
        official_app_assets: [],
      });

      setShowCreateModal(false);
      setNewBrandName('');
      setNewBrandDesc('');
      setNewBrandWebsite('https://');
      setNewBrandDomains('');
      setSuccessMsg(`Brand '${created.name}' registered successfully!`);
      await loadData();
      setSelectedBrand(created);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create brand';
      setFormError(message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Building2 className="h-6 w-6 text-indigo-400" />
            Brand Profile & Official Asset Guard
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Registered legitimate brand assets, safe-lists, and backend-enforced official-asset exclusion rules.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleSeedNovaPay}
            disabled={seeding}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${seeding ? 'animate-spin' : ''}`} />
            {seeding ? 'Seeding NovaPay...' : 'Seed NovaPay Demo'}
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            New Brand
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
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

      {loading ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-400 text-sm">
          <RefreshCw className="mx-auto h-6 w-6 animate-spin text-indigo-400 mb-2" />
          Loading brand profiles from MongoDB Atlas...
        </div>
      ) : brands.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-10 text-center">
          <Building2 className="mx-auto h-10 w-10 text-slate-600 mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No Brands Registered in Atlas</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-5">
            Click <strong>Seed NovaPay</strong> to populate the canonical fictional benchmark brand or create a custom brand profile.
          </p>
          <button
            onClick={handleSeedNovaPay}
            disabled={seeding}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${seeding ? 'animate-spin' : ''}`} />
            Seed Fictional Brand NovaPay
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Brand Switcher Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-xs font-medium text-slate-400">Select Brand:</span>
            {brands.map((b) => (
              <button
                key={b.brand_id}
                onClick={() => setSelectedBrand(b)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  selectedBrand?.brand_id === b.brand_id
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {b.name}
                {b.is_synthetic && (
                  <span className="ml-1.5 text-[10px] bg-indigo-950 text-indigo-300 px-1 py-0.2 rounded border border-indigo-700/50">
                    DEMO
                  </span>
                )}
              </button>
            ))}
          </div>

          {selectedBrand && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-w-0">
              {/* Left Column: Brand Metadata & Core Properties */}
              <div className="lg:col-span-1 space-y-4 min-w-0">
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4 min-w-0 overflow-hidden">
                  <div className="flex items-start justify-between min-w-0 gap-2">
                    <div className="min-w-0 flex-1">
                      <h2 className="text-lg font-bold text-white truncate" title={selectedBrand.name}>{selectedBrand.name}</h2>
                      <div className="text-[11px] font-mono text-slate-400 truncate" title={selectedBrand.brand_id}>{selectedBrand.brand_id}</div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400 border border-emerald-500/20 shrink-0">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                      {selectedBrand.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed break-words">
                    {selectedBrand.description}
                  </p>

                  <div className="space-y-2.5 pt-2 border-t border-slate-800 text-xs min-w-0">
                    <div className="min-w-0">
                      <span className="text-slate-400 block text-[11px] uppercase tracking-wider mb-1">
                        Official Website
                      </span>
                      <div className="flex items-center gap-1.5 rounded-lg bg-slate-950 p-2 border border-slate-800 min-w-0">
                        <Globe className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                        <a
                          href={selectedBrand.official_website}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) =>
                            handleOpenUrl(e, {
                              title: `${selectedBrand.name} Official Website`,
                              url: selectedBrand.official_website,
                              type: 'website',
                              identifierLabel: 'Validated Domains',
                              identifierValue: selectedBrand.official_domains.join(', '),
                            })
                          }
                          className="text-indigo-400 hover:underline font-mono text-[11px] truncate flex-1 min-w-0"
                          title={selectedBrand.official_website}
                        >
                          {selectedBrand.official_website}
                        </a>
                        <button
                          type="button"
                          onClick={() => handleCopyUrl(selectedBrand.official_website)}
                          title="Copy Website URL"
                          className="rounded p-1 text-slate-400 hover:text-white hover:bg-slate-800 shrink-0 transition-colors"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                        <a
                          href={selectedBrand.official_website}
                          target="_blank"
                          rel="noreferrer"
                          title="Open Website in new tab"
                          className="rounded p-1 text-slate-400 hover:text-indigo-300 hover:bg-slate-800 shrink-0 transition-colors"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[11px] uppercase tracking-wider mb-1">
                        Official Domains (Validated)
                      </span>
                      {selectedBrand.official_domains && selectedBrand.official_domains.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedBrand.official_domains.map((dom, idx) => (
                            <span
                              key={idx}
                              className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[11px] text-slate-200 border border-slate-700/60"
                            >
                              {dom}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {(() => {
                            try {
                              const host = new URL(selectedBrand.official_website).hostname.replace(/^www\./, '').toLowerCase();
                              if (host && !host.includes('.example')) {
                                return (
                                  <span className="rounded bg-indigo-950/50 px-2 py-0.5 font-mono text-[11px] text-indigo-300 border border-indigo-800/40">
                                    {host} (auto-detected)
                                  </span>
                                );
                              }
                            } catch {}
                            return <span className="text-slate-500 text-[11px] italic">None configured</span>;
                          })()}
                        </div>
                      )}
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[11px] uppercase tracking-wider mb-1">
                        Brand Aliases & Keywords
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {selectedBrand.keywords.concat(selectedBrand.aliases).map((kw, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-0.5 rounded bg-indigo-950/40 px-1.5 py-0.5 text-[10px] text-indigo-300 border border-indigo-800/40"
                          >
                            <Tag className="h-2.5 w-2.5" />
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[11px] uppercase tracking-wider mb-1">
                        Safe-List (Exempt from Threat Scoring)
                      </span>
                      {selectedBrand.safe_list.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedBrand.safe_list.map((sl, idx) => (
                            <span
                              key={idx}
                              className="rounded bg-emerald-950/40 px-2 py-0.5 text-[11px] text-emerald-300 border border-emerald-800/40 inline-flex items-center gap-1"
                            >
                              <FileCheck className="h-3 w-3" />
                              {sl}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-500 text-[11px] italic">None configured</span>
                      )}
                    </div>

                    {/* Official Logo Section */}
                    <div className="pt-2 border-t border-slate-800">
                      <span className="text-slate-400 block text-[11px] uppercase tracking-wider mb-1.5">
                        Official Logo & Perceptual Hash
                      </span>
                      {selectedBrand.official_logo ? (
                        <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800 space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-400">pHash (64-bit):</span>
                            <span className="font-mono text-indigo-300 font-bold">
                              {selectedBrand.official_logo.image_hash}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {selectedBrand.official_logo.hash_algorithm || 'imagehash.phash(hash_size=8)'}
                          </div>
                        </div>
                      ) : (
                        <div className="text-[11px] text-slate-500 italic mb-2">No logo hash uploaded</div>
                      )}

                      <label className="mt-2 inline-flex items-center gap-1.5 cursor-pointer rounded bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700 transition-colors border border-slate-700">
                        <Upload className="h-3 w-3" />
                        {uploadingLogo ? 'Computing Hash...' : 'Upload Logo for pHash'}
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/webp"
                          className="hidden"
                          onChange={handleLogoUpload}
                          disabled={uploadingLogo}
                        />
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Middle & Right: Official Assets & Safety Guard Tester */}
              <div className="lg:col-span-2 space-y-6 min-w-0">
                {/* Official Social Assets */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Share2 className="h-4 w-4 text-indigo-400" />
                      Registered Official Social Accounts ({selectedBrand.official_social_assets.length})
                    </h3>
                  </div>

                  {selectedBrand.official_social_assets.length === 0 ? (
                    <div className="text-xs text-slate-500 italic py-2">No social assets registered.</div>
                  ) : (
                    <div className="space-y-2">
                      {selectedBrand.official_social_assets.map((asset, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs"
                        >
                          <div>
                            <div className="font-semibold text-white flex items-center gap-2">
                              <span>@{asset.normalized_handle}</span>
                              <span className="rounded bg-indigo-500/20 px-1.5 py-0.2 text-[10px] text-indigo-300 font-mono uppercase">
                                {asset.platform}
                              </span>
                            </div>
                            <div className="text-slate-400 text-[11px] mt-0.5">
                              Display: <span className="text-slate-200">{asset.display_name}</span>
                            </div>
                            {asset.stable_account_id && (
                              <div className="text-slate-500 font-mono text-[10px] mt-0.5">
                                Stable ID: {asset.stable_account_id}
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              type="button"
                              onClick={() => handleCopyUrl(asset.canonical_profile_url)}
                              title="Copy Profile URL"
                              className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                            <a
                              href={asset.canonical_profile_url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) =>
                                handleOpenUrl(e, {
                                  title: `${asset.display_name} Official Profile`,
                                  url: asset.canonical_profile_url,
                                  type: 'social',
                                  handleOrBundle: asset.normalized_handle,
                                  platformOrStore: asset.platform,
                                  identifierLabel: 'Stable Account DID',
                                  identifierValue: asset.stable_account_id,
                                })
                              }
                              className="rounded border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-indigo-300 hover:bg-indigo-500/20 hover:text-indigo-200 font-mono text-[11px] inline-flex items-center gap-1.5 transition-colors cursor-pointer"
                            >
                              Profile URL <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Official Mobile Apps */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Smartphone className="h-4 w-4 text-indigo-400" />
                      Registered Official Mobile Apps ({selectedBrand.official_app_assets.length})
                    </h3>
                  </div>

                  {selectedBrand.official_app_assets.length === 0 ? (
                    <div className="text-xs text-slate-500 italic py-2">No app assets registered.</div>
                  ) : (
                    <div className="space-y-2">
                      {selectedBrand.official_app_assets.map((app, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs"
                        >
                          <div>
                            <div className="font-semibold text-white flex items-center gap-2">
                              <span>{app.app_name}</span>
                              <span className="rounded bg-indigo-500/20 px-1.5 py-0.2 text-[10px] text-indigo-300 font-mono uppercase">
                                {app.store}
                              </span>
                            </div>
                            <div className="font-mono text-slate-300 text-[11px] mt-0.5">
                              Bundle: <span className="text-indigo-300">{app.package_or_bundle_id}</span>
                            </div>
                            <div className="text-slate-400 text-[11px] mt-0.5">
                              Publisher: <span className="text-slate-200">{app.trusted_publisher_name}</span>
                              {app.trusted_publisher_id && (
                                <span className="text-slate-500 font-mono text-[10px] ml-1">
                                  ({app.trusted_publisher_id})
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              type="button"
                              onClick={() => handleCopyUrl(app.canonical_listing_url)}
                              title="Copy Listing URL"
                              className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                            <a
                              href={app.canonical_listing_url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) =>
                                handleOpenUrl(e, {
                                  title: `${app.app_name} Official App Listing`,
                                  url: app.canonical_listing_url,
                                  type: 'app',
                                  handleOrBundle: app.package_or_bundle_id,
                                  platformOrStore: app.store,
                                  identifierLabel: 'Trusted Publisher ID',
                                  identifierValue: app.trusted_publisher_id,
                                })
                              }
                              className="rounded border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-indigo-300 hover:bg-indigo-500/20 hover:text-indigo-200 font-mono text-[11px] inline-flex items-center gap-1.5 transition-colors cursor-pointer"
                            >
                              Listing URL <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Interactive Official Safety Guard Tester */}
                <div className="rounded-xl border border-indigo-500/30 bg-slate-900/60 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-emerald-400" />
                        Official-Asset Exclusion Safety Guard Tester
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Test candidate metadata against the backend safety guard. Official assets are excluded before threat scoring.
                      </p>
                    </div>
                  </div>

                  {/* Tester Form */}
                  <div className="space-y-3 text-xs">
                    <div className="flex items-center gap-3">
                      <label className="text-slate-400 text-[11px] font-semibold uppercase">Candidate Type:</label>
                      <button
                        type="button"
                        onClick={() => {
                          setTesterType('domain');
                          setTesterUrl('paypal.com');
                        }}
                        className={`px-2.5 py-1 rounded text-xs font-semibold ${
                          testerType === 'domain'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        Domain / URL
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setTesterType('social_profile');
                          setTesterUrl('https://bsky.synthetic.example/profile/novapay.synthetic.example');
                        }}
                        className={`px-2.5 py-1 rounded text-xs font-semibold ${
                          testerType === 'social_profile'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        Social Profile
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setTesterType('app_listing');
                          setTesterBundleId('com.yourcompany.PPClient');
                          setTesterAccountOrPubId('283646712');
                        }}
                        className={`px-2.5 py-1 rounded text-xs font-semibold ${
                          testerType === 'app_listing'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        App Listing
                      </button>
                    </div>

                    {testerType === 'domain' ? (
                      <div>
                        <label className="block text-slate-400 text-[11px] mb-1">Domain or URL to Test</label>
                        <input
                          type="text"
                          value={testerUrl}
                          onChange={(e) => setTesterUrl(e.target.value)}
                          placeholder="e.g. paypal.com or paypal.com.phishing-example.test"
                          className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none font-mono"
                        />
                      </div>
                    ) : testerType === 'social_profile' ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-slate-400 text-[11px] mb-1">Handle</label>
                          <input
                            type="text"
                            value={testerHandle}
                            onChange={(e) => setTesterHandle(e.target.value)}
                            className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-slate-400 text-[11px] mb-1">Stable Account ID (DID)</label>
                          <input
                            type="text"
                            value={testerAccountOrPubId}
                            onChange={(e) => setTesterAccountOrPubId(e.target.value)}
                            className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                          />
                        </div>
                        <div className="sm:col-span-2">
                          <label className="block text-slate-400 text-[11px] mb-1">Canonical Profile URL</label>
                          <input
                            type="text"
                            value={testerUrl}
                            onChange={(e) => setTesterUrl(e.target.value)}
                            className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-slate-400 text-[11px] mb-1">Package/Bundle ID</label>
                          <input
                            type="text"
                            value={testerBundleId}
                            onChange={(e) => setTesterBundleId(e.target.value)}
                            className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-slate-400 text-[11px] mb-1">Publisher/Developer ID</label>
                          <input
                            type="text"
                            value={testerAccountOrPubId}
                            onChange={(e) => setTesterAccountOrPubId(e.target.value)}
                            className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                          />
                        </div>
                      </div>
                    )}

                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={handleRunSafetyTest}
                        disabled={evaluating}
                        className="inline-flex items-center gap-1.5 rounded bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors shadow-sm"
                      >
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {evaluating ? 'Evaluating Guard...' : 'Evaluate Against Guard'}
                      </button>
                    </div>

                    {/* Result Card */}
                    {evalResult && (
                      <div
                        className={`mt-3 rounded-lg border p-4 text-xs space-y-1.5 ${
                          evalResult.status === 'OFFICIAL_EXCLUDED'
                            ? 'border-emerald-500/40 bg-emerald-950/30'
                            : evalResult.status === 'REVIEW_REQUIRED'
                            ? 'border-amber-500/40 bg-amber-950/30'
                            : evalResult.status === 'SAFE_LISTED'
                            ? 'border-blue-500/40 bg-blue-950/30'
                            : 'border-slate-700 bg-slate-950/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300">Guard Decision:</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-bold font-mono ${
                              evalResult.status === 'OFFICIAL_EXCLUDED'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                : evalResult.status === 'REVIEW_REQUIRED'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : evalResult.status === 'SAFE_LISTED'
                                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                                : 'bg-slate-800 text-slate-300 border border-slate-700'
                            }`}
                          >
                            {evalResult.status}
                          </span>
                        </div>
                        <div className="text-slate-200">
                          <strong>Reason:</strong> {evalResult.reason}
                        </div>
                        {evalResult.conflict_details && (
                          <div className="text-amber-300 text-[11px]">
                            <strong>Conflict Details:</strong> {evalResult.conflict_details}
                          </div>
                        )}
                        <div className="text-[11px] text-slate-400">
                          Excluded from threat alerts:{' '}
                          <span className={evalResult.is_excluded_from_scoring ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                            {evalResult.is_excluded_from_scoring ? 'YES (Safe)' : 'NO (Scored by Engine)'}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* New Brand Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="h-4 w-4 text-indigo-400" />
                Register New Monitored Brand
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="rounded bg-rose-950/50 border border-rose-500/30 p-2.5 text-xs text-rose-300">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateBrand} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">Brand Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ApexPay"
                  value={newBrandName}
                  onChange={(e) => setNewBrandName(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Description *</label>
                <textarea
                  required
                  rows={2}
                  placeholder="Brand description and domain context"
                  value={newBrandDesc}
                  onChange={(e) => setNewBrandDesc(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Official Website *</label>
                <input
                  type="url"
                  required
                  placeholder="https://www.example.com"
                  value={newBrandWebsite}
                  onChange={(e) => setNewBrandWebsite(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Official Domains (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="example.com, example.net"
                  value={newBrandDomains}
                  onChange={(e) => setNewBrandDomains(e.target.value)}
                  className="w-full rounded bg-slate-950 border border-slate-800 p-2 text-white focus:border-indigo-500 focus:outline-none"
                />
                <span className="text-[10px] text-slate-500">
                  Domains will be normalized and validated automatically.
                </span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  {creating ? 'Saving...' : 'Register Brand'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Synthetic URL Sandbox Preview Modal */}
      {previewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {previewModal.type === 'social' ? (
                    <Share2 className="h-5 w-5" />
                  ) : previewModal.type === 'app' ? (
                    <Smartphone className="h-5 w-5" />
                  ) : (
                    <Globe className="h-5 w-5" />
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">{previewModal.title}</h3>
                  <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Verified Official Asset • Simulated Benchmark Domain
                  </span>
                </div>
              </div>

              <button
                onClick={() => setPreviewModal(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* RFC 2606 Explanatory Alert */}
            <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/30 p-3.5 text-xs text-slate-300 space-y-1">
              <div className="font-semibold text-indigo-300 flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5 text-indigo-400" />
                RFC 2606 Synthetic Namespace Notice
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                NovaPay is an isolated benchmark brand. In compliance with IETF RFC 2606, benchmark URLs use reserved
                <code className="text-indigo-300 bg-slate-950 px-1 py-0.5 rounded mx-1">.example</code>
                domains to guarantee that offline testing never routes live traffic or disrupts public services.
              </p>
            </div>

            {/* Registered URL with Copy Button */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Registered Canonical URL
              </label>
              <div className="flex items-center gap-2 rounded-lg bg-slate-950 p-2.5 border border-slate-800">
                <code className="text-xs text-indigo-300 font-mono flex-1 break-all select-all">
                  {previewModal.url}
                </code>
                <button
                  type="button"
                  onClick={() => handleCopyUrl(previewModal.url)}
                  className="inline-flex items-center gap-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 text-xs font-medium shrink-0 transition-colors border border-slate-700"
                >
                  {copiedUrl ? (
                    <>
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400 font-semibold">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy URL</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Metadata Details */}
            <div className="rounded-lg bg-slate-950/60 p-3.5 border border-slate-800 text-xs space-y-2">
              {previewModal.handleOrBundle && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">{previewModal.type === 'social' ? 'Normalized Handle' : 'App Bundle ID'}:</span>
                  <span className="font-mono text-white font-medium">{previewModal.handleOrBundle}</span>
                </div>
              )}
              {previewModal.platformOrStore && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Platform / Store:</span>
                  <span className="uppercase text-indigo-300 font-mono text-[11px] bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-800/40">
                    {previewModal.platformOrStore}
                  </span>
                </div>
              )}
              {previewModal.identifierLabel && previewModal.identifierValue && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">{previewModal.identifierLabel}:</span>
                  <span className="font-mono text-slate-200 text-[11px]">{previewModal.identifierValue}</span>
                </div>
              )}
              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <span className="text-slate-400">Pre-Scoring Safety Guard:</span>
                <span className="text-emerald-400 font-semibold font-mono text-[11px]">
                  OFFICIAL_EXCLUDED (0 Threat Score)
                </span>
              </div>
            </div>

            {/* Action Footer */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-2 border-t border-slate-800/80">
              {previewModal.type !== 'website' ? (
                <button
                  type="button"
                  onClick={() => handleTestInSafetyGuard(previewModal)}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-2 text-xs font-semibold shadow-sm transition-colors"
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Test in Safety Guard Tester
                </button>
              ) : (
                <div />
              )}

              <div className="flex items-center justify-end gap-2">
                <a
                  href={previewModal.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-slate-400 hover:text-slate-200 underline inline-flex items-center gap-1"
                >
                  Open in browser <ExternalLink className="h-3 w-3" />
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewModal(null)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
