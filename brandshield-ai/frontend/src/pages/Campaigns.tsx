import React, { useEffect, useState } from 'react';
import {
  Network,
  Share2,
  Smartphone,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  X,
  Info,
  ArrowUpRight,
  ShieldCheck,
  List,
  Link as LinkIcon,
  HelpCircle,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchBrands } from '../api/brandClient';
import {
  fetchCampaignGraph,
  seedNovaPayCampaigns,
  CampaignGraphResponse,
  GraphNode,
  GraphEdge,
} from '../api/campaignClient';
import { Brand } from '../types/brand';

export const Campaigns: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');

  const [graphData, setGraphData] = useState<CampaignGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [seeding, setSeeding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  // View mode: 'network' or 'list'
  const [viewMode, setViewMode] = useState<'network' | 'list'>('network');

  // Interactive selection states
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  // Filters
  const [includeOfficial, setIncludeOfficial] = useState<boolean>(false);
  const [indicatorFilter, setIndicatorFilter] = useState<string>('');

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

  const loadGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCampaignGraph(selectedBrandId || undefined, includeOfficial);
      setGraphData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load campaign graph';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [selectedBrandId, includeOfficial]);

  const handleSeedCampaigns = async () => {
    setSeeding(true);
    setError(null);
    try {
      const res = await seedNovaPayCampaigns();
      setFeedback(res.message);
      setTimeout(() => setFeedback(null), 5000);
      // Reload graph
      await loadGraph();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to seed synthetic campaign data';
      setError(msg);
    } finally {
      setSeeding(false);
    }
  };

  // Filtered groups based on indicatorFilter
  const filteredGroups = graphData?.groups.filter((g) => {
    if (!indicatorFilter) return true;
    return g.shared_indicator_types.includes(indicatorFilter);
  }) || [];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 p-6 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20 mb-2">
              <Network className="h-3.5 w-3.5" />
              Signature Feature: Multi-Asset Correlation
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Impersonation Campaign Graph
            </h1>
            <p className="mt-1 text-xs text-slate-300 max-w-2xl leading-relaxed">
              Detects clusters of suspicious social accounts and mobile applications that share
              concrete technical infrastructure (identical external domains, developer IDs, perceptual hashes,
              or contact records).
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleSeedCampaigns}
              disabled={seeding}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3.5 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
              title="Seed repeatable NovaPay synthetic campaign scenario"
            >
              <Sparkles className={`h-3.5 w-3.5 ${seeding ? 'animate-spin' : ''}`} />
              {seeding ? 'Seeding Dataset...' : 'Seed Demo Scenario'}
            </button>
            <button
              onClick={loadGraph}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 px-3 py-2 text-xs font-medium text-slate-200 transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Ethical Disclaimer */}
        <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-950/20 p-3 text-xs text-amber-300/90 flex items-start gap-2.5">
          <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-amber-200">Ethical Attribution Guardrail: </span>
            {graphData?.disclaimer ||
              'Campaign groupings represent POTENTIAL_COORDINATION only based on observable technical overlap. They do not assert confirmed common ownership or criminal conspiracy.'}
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

      {/* Graph Controls Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Brand select */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Brand:</span>
            <select
              value={selectedBrandId}
              onChange={(e) => setSelectedBrandId(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Monitored Brands</option>
              {brands.map((b) => (
                <option key={b.brand_id} value={b.brand_id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          {/* Indicator filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px] font-medium">Indicator:</span>
            <select
              value={indicatorFilter}
              onChange={(e) => setIndicatorFilter(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="">All Shared Indicators</option>
              <option value="exact_normalized_domain">Exact Domain</option>
              <option value="publisher_id">Publisher / Developer ID</option>
              <option value="perceptual_hash">Perceptual Image Hash</option>
              <option value="contact_email">Contact Email</option>
              <option value="contact_phone">Contact Phone</option>
            </select>
          </div>

          {/* Include official toggle */}
          <label className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-300">
            <input
              type="checkbox"
              checked={includeOfficial}
              onChange={(e) => setIncludeOfficial(e.target.checked)}
              className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-0"
            />
            <span className="text-[11px]">Include Excluded Official Assets</span>
          </label>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center rounded-lg border border-slate-800 bg-slate-950 p-1 self-start md:self-auto">
          <button
            onClick={() => setViewMode('network')}
            className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-semibold transition ${
              viewMode === 'network'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="h-3.5 w-3.5" />
            Cluster Network
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-semibold transition ${
              viewMode === 'list'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <List className="h-3.5 w-3.5" />
            Group List
          </button>
        </div>
      </div>

      {/* Summary KPI Pills */}
      {graphData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
            <span className="text-slate-400 text-[11px]">Potential Campaign Groups</span>
            <div className="text-xl font-extrabold text-indigo-300 mt-1">
              {graphData.groups.length}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Clusters sharing concrete indicators
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
            <span className="text-slate-400 text-[11px]">Linked Candidates</span>
            <div className="text-xl font-extrabold text-white mt-1">
              {graphData.nodes.length - graphData.unconnected_candidate_ids.length}
              <span className="text-xs text-slate-500 font-normal"> / {graphData.nodes.length}</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {graphData.unconnected_candidate_ids.length} isolated singletons
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
            <span className="text-slate-400 text-[11px]">Indicator Edges</span>
            <div className="text-xl font-extrabold text-amber-300 mt-1">
              {graphData.edges.length}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Zero name-only links
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
            <span className="text-slate-400 text-[11px]">Non-Edges Documented</span>
            <div className="text-xl font-extrabold text-emerald-400 mt-1">
              {Object.keys(graphData.non_edges_documented.generic_domains_excluded).length +
                Object.keys(graphData.non_edges_documented.official_domain_matches_excluded).length}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Generic / official false-positive exclusions
            </div>
          </div>
        </div>
      )}

      {/* Main Graph Content */}
      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 py-20 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-400" />
          <span>Building correlation graph from MongoDB Atlas records...</span>
        </div>
      ) : !graphData || graphData.groups.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center space-y-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
            <Network className="h-6 w-6" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-bold text-white">No Impersonation Campaigns Detected</h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              No candidates in the current view share concrete indicators (domains, publisher IDs, perceptual
              hashes, or contact records). Click below to seed the repeatable NovaPay demonstration scenario.
            </p>
          </div>
          <button
            onClick={handleSeedCampaigns}
            disabled={seeding}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white transition shadow-lg shadow-indigo-600/20"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Seed NovaPay Campaign Scenario
          </button>
        </div>
      ) : viewMode === 'network' ? (
        /* Visual Network Cluster View */
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredGroups.map((group) => (
              <div
                key={group.group_id}
                onClick={() => setSelectedGroupId(selectedGroupId === group.group_id ? null : group.group_id)}
                className={`rounded-2xl border transition p-5 cursor-pointer ${
                  selectedGroupId === group.group_id
                    ? 'border-indigo-500 bg-slate-900/90 shadow-xl shadow-indigo-500/10'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                {/* Group Header */}
                <div className="flex items-start justify-between gap-3 mb-4 border-b border-slate-800 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-white">{group.group_id}</span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/60 text-amber-400 border border-amber-800/40">
                        {group.label}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {group.group_size} linked assets ({group.candidate_types.join(', ')})
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400">Highest Risk</span>
                    <div className="font-mono text-base font-extrabold text-rose-400">
                      {group.highest_risk}
                      <span className="text-[10px] text-slate-500 font-normal"> / 100</span>
                    </div>
                  </div>
                </div>

                {/* Shared Indicator Badges */}
                <div className="flex flex-wrap items-center gap-1.5 mb-4">
                  <span className="text-[10px] text-slate-500 font-medium">Shared:</span>
                  {group.shared_indicator_types.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1 rounded bg-indigo-950/80 border border-indigo-800/40 px-2 py-0.5 text-[10px] font-semibold text-indigo-300 font-mono"
                    >
                      <LinkIcon className="h-2.5 w-2.5" />
                      {t.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>

                {/* SVG Cluster Layout */}
                <div className="relative rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 h-64 overflow-hidden flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 400 240">
                    {/* Render Links / Edges */}
                    {group.links.map((link) => {
                      const memberCount = group.member_candidate_ids.length;
                      const idxA = group.member_candidate_ids.indexOf(link.source);
                      const idxB = group.member_candidate_ids.indexOf(link.target);
                      if (idxA === -1 || idxB === -1) return null;

                      // Position members in a circle
                      const cx = 200;
                      const cy = 120;
                      const r = 80;
                      const angleA = (idxA / memberCount) * 2 * Math.PI - Math.PI / 2;
                      const angleB = (idxB / memberCount) * 2 * Math.PI - Math.PI / 2;

                      const x1 = cx + r * Math.cos(angleA);
                      const y1 = cy + r * Math.sin(angleA);
                      const x2 = cx + r * Math.cos(angleB);
                      const y2 = cy + r * Math.sin(angleB);

                      return (
                        <g key={link.id} className="cursor-pointer" onClick={() => setSelectedEdge(link)}>
                          <line
                            x1={x1}
                            y1={y1}
                            x2={x2}
                            y2={y2}
                            stroke="#6366f1"
                            strokeWidth="2.5"
                            strokeDasharray="4 2"
                            className="hover:stroke-indigo-300 transition"
                          />
                        </g>
                      );
                    })}

                    {/* Render Nodes */}
                    {group.member_candidate_ids.map((cid, idx) => {
                      const memberCount = group.member_candidate_ids.length;
                      const nodeDoc = graphData.nodes.find((n) => n.id === cid);
                      if (!nodeDoc) return null;

                      const cx = 200;
                      const cy = 120;
                      const r = 80;
                      const angle = (idx / memberCount) * 2 * Math.PI - Math.PI / 2;
                      const nx = cx + r * Math.cos(angle);
                      const ny = cy + r * Math.sin(angle);

                      const isApp = nodeDoc.candidate_type === 'app_listing';
                      const isSelected = selectedNode?.id === cid;

                      return (
                        <g
                          key={cid}
                          className="cursor-pointer transition-transform hover:scale-110"
                          onClick={() => setSelectedNode(nodeDoc)}
                        >
                          <circle
                            cx={nx}
                            cy={ny}
                            r={isSelected ? 18 : 15}
                            fill={isApp ? '#4338ca' : '#0284c7'}
                            stroke={isSelected ? '#38bdf8' : '#e2e8f0'}
                            strokeWidth={isSelected ? 3 : 1.5}
                          />
                          <text
                            x={nx}
                            y={ny + 4}
                            textAnchor="middle"
                            fill="#ffffff"
                            fontSize="9"
                            fontWeight="bold"
                            pointerEvents="none"
                          >
                            {isApp ? 'APP' : 'SOC'}
                          </text>
                          <text
                            x={nx}
                            y={ny > cy ? ny + 26 : ny - 20}
                            textAnchor="middle"
                            fill="#94a3b8"
                            fontSize="8"
                            fontFamily="monospace"
                            pointerEvents="none"
                          >
                            {cid}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>

                {/* Member pills and edge inspector button */}
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {group.member_candidate_ids.map((cid) => {
                      const n = graphData.nodes.find((item) => item.id === cid);
                      return (
                        <button
                          key={cid}
                          onClick={() => n && setSelectedNode(n)}
                          className="inline-flex items-center gap-1 rounded bg-slate-800 hover:bg-slate-700 px-2 py-1 text-[11px] text-slate-300 font-mono transition"
                        >
                          {n?.candidate_type === 'app_listing' ? (
                            <Smartphone className="h-3 w-3 text-indigo-400" />
                          ) : (
                            <Share2 className="h-3 w-3 text-sky-400" />
                          )}
                          {cid}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    onClick={() => {
                      if (group.links.length > 0) {
                        setSelectedEdge(group.links[0]);
                      }
                    }}
                    className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 text-[11px]"
                  >
                    Inspect Shared Indicator ({group.links.length})
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Unconnected Suspicious Candidates */}
          {graphData.unconnected_candidate_ids.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-slate-400" />
                  Isolated Candidates (No Technical Indicator Overlap)
                </h3>
                <span className="text-xs text-slate-500 font-mono">
                  {graphData.unconnected_candidate_ids.length} candidates
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-3 leading-relaxed">
                These candidates are scored individually but do not share any verifiable domains, publisher IDs,
                perceptual image hashes, or contact records. They are deliberately kept unconnected to prevent false campaign associations.
              </p>
              <div className="flex flex-wrap gap-2">
                {graphData.unconnected_candidate_ids.slice(0, 16).map((cid) => {
                  const nodeDoc = graphData.nodes.find((n) => n.id === cid);
                  return (
                    <button
                      key={cid}
                      onClick={() => nodeDoc && setSelectedNode(nodeDoc)}
                      className="rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 px-2.5 py-1 text-xs text-slate-300 font-mono flex items-center gap-1.5 transition"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
                      {nodeDoc?.label || cid}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Documented Non-Edges Audit Section */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-2">
              <HelpCircle className="h-4 w-4 text-emerald-400" />
              Documented False-Positive Suppressions (Non-Edges Audit)
            </h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              To preserve data integrity, the detection engine actively suppresses links for generic hosting providers,
              URL shorteners, and the brand's own victim assets:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 space-y-1.5">
                <div className="font-semibold text-slate-200">
                  Generic Domains Suppressed ({Object.keys(graphData.non_edges_documented.generic_domains_excluded).length})
                </div>
                <div className="text-[11px] text-slate-400 leading-relaxed">
                  Common shorteners or link aggregators (e.g. <code>linkhub.example</code>) that were shared by multiple candidates but prevented from linking.
                </div>
                <div className="flex flex-wrap gap-1 pt-1 font-mono text-[10px] text-amber-300">
                  {Object.keys(graphData.non_edges_documented.generic_domains_excluded).map((d) => (
                    <span key={d} className="rounded bg-slate-900 border border-slate-800 px-1.5 py-0.5">
                      {d}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 space-y-1.5">
                <div className="font-semibold text-slate-200">
                  Official Victim Assets Suppressed ({Object.keys(graphData.non_edges_documented.official_domain_matches_excluded).length + Object.keys(graphData.non_edges_documented.official_logo_matches_excluded).length})
                </div>
                <div className="text-[11px] text-slate-400 leading-relaxed">
                  Candidates linking to the official domain or mimicking the official logo hash are NOT linked together, avoiding false attacker clustering.
                </div>
                <div className="flex flex-wrap gap-1 pt-1 font-mono text-[10px] text-emerald-300">
                  {Object.keys(graphData.non_edges_documented.official_domain_matches_excluded).map((d) => (
                    <span key={d} className="rounded bg-slate-900 border border-slate-800 px-1.5 py-0.5">
                      {d}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Structured List View */
        <div className="space-y-4">
          {filteredGroups.map((group) => (
            <div
              key={group.group_id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4 hover:border-slate-700 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-base font-bold text-white">{group.group_id}</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/60 text-amber-400 border border-amber-800/40">
                    {group.label}
                  </span>
                  <span className="text-xs text-slate-400">
                    ({group.group_size} members)
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  Highest Threat Score:{' '}
                  <span className="font-mono font-bold text-rose-400">{group.highest_risk}/100</span> (
                  <span className="font-semibold text-slate-200">{group.highest_severity}</span>)
                </div>
              </div>

              {/* Members table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3 font-semibold">Type</th>
                      <th className="py-2 px-3 font-semibold">Candidate ID</th>
                      <th className="py-2 px-3 font-semibold">Name</th>
                      <th className="py-2 px-3 font-semibold">Score</th>
                      <th className="py-2 px-3 font-semibold">Classification</th>
                      <th className="py-2 px-3 text-right font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {group.member_candidate_ids.map((cid) => {
                      const nodeDoc = graphData?.nodes.find((n) => n.id === cid);
                      return (
                        <tr key={cid} className="hover:bg-slate-800/20">
                          <td className="py-2 px-3">
                            {nodeDoc?.candidate_type === 'app_listing' ? (
                              <span className="inline-flex items-center gap-1 text-indigo-400">
                                <Smartphone className="h-3.5 w-3.5" /> App
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-sky-400">
                                <Share2 className="h-3.5 w-3.5" /> Social
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-3 font-mono font-semibold text-slate-200">{cid}</td>
                          <td className="py-2 px-3 font-medium text-white">{nodeDoc?.label || cid}</td>
                          <td className="py-2 px-3 font-mono font-bold">{nodeDoc?.score || 0}</td>
                          <td className="py-2 px-3">
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                              {nodeDoc?.classification}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right">
                            <button
                              onClick={() => nodeDoc && setSelectedNode(nodeDoc)}
                              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                            >
                              Inspect Details
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Group Links Explanation */}
              <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/80 space-y-2 text-xs">
                <div className="font-semibold text-slate-300">Qualifying Indicator Links:</div>
                {group.links.map((link) => (
                  <div key={link.id} className="text-[11px] text-slate-400 flex items-start gap-2">
                    <span className="font-mono text-indigo-400 shrink-0">
                      {link.source} &harr; {link.target}:
                    </span>
                    <span className="text-slate-300">{link.explanation}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Selected Node Details Modal */}
      {selectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-mono text-slate-400 uppercase">
                  Candidate Node: {selectedNode.id}
                </span>
                <h3 className="text-lg font-bold text-white mt-0.5">{selectedNode.label}</h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-950/60 rounded p-2.5 border border-slate-800">
                <span className="text-slate-500">Asset Type:</span>
                <div className="font-semibold text-white capitalize mt-0.5">
                  {selectedNode.candidate_type.replace(/_/g, ' ')}
                </div>
              </div>
              <div className="bg-slate-950/60 rounded p-2.5 border border-slate-800">
                <span className="text-slate-500">Platform / Store:</span>
                <div className="font-semibold text-white capitalize mt-0.5">{selectedNode.platform}</div>
              </div>
              <div className="bg-slate-950/60 rounded p-2.5 border border-slate-800">
                <span className="text-slate-500">Threat Score:</span>
                <div className="font-mono font-bold text-rose-400 text-sm mt-0.5">
                  {selectedNode.score}/100 ({selectedNode.severity})
                </div>
              </div>
              <div className="bg-slate-950/60 rounded p-2.5 border border-slate-800">
                <span className="text-slate-500">Classification:</span>
                <div className="font-semibold text-indigo-300 mt-0.5">{selectedNode.classification}</div>
              </div>
            </div>

            {selectedNode.external_identifier && (
              <div className="text-xs bg-slate-950/60 rounded p-2.5 border border-slate-800">
                <span className="text-slate-500">Identifier:</span>
                <div className="font-mono text-slate-200 mt-0.5 break-all">
                  {selectedNode.external_identifier}
                </div>
              </div>
            )}

            {selectedNode.group_id && (
              <div className="text-xs bg-indigo-950/30 rounded p-2.5 border border-indigo-900/40">
                <span className="text-indigo-400 font-semibold">Assigned Campaign Group:</span>
                <div className="font-mono text-white mt-0.5">{selectedNode.group_id} (POTENTIAL_COORDINATION)</div>
              </div>
            )}

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <Link
                to={`/investigations?search=${encodeURIComponent(selectedNode.label || selectedNode.id)}`}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
              >
                Inspect in Investigations <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Selected Edge Rationale Modal */}
      {selectedEdge && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-mono text-indigo-400 uppercase">
                  Indicator Edge Evidence
                </span>
                <h3 className="text-base font-bold text-white mt-0.5">
                  {selectedEdge.source} &harr; {selectedEdge.target}
                </h3>
              </div>
              <button
                onClick={() => setSelectedEdge(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-slate-950/60 rounded p-3 border border-slate-800 space-y-1">
                <span className="text-slate-500 font-medium">Shared Technical Indicator:</span>
                <div className="font-mono font-bold text-indigo-300">
                  {selectedEdge.indicator_type.replace(/_/g, ' ')}
                </div>
              </div>

              <div className="bg-slate-950/60 rounded p-3 border border-slate-800 space-y-1">
                <span className="text-slate-500 font-medium">Matched Value:</span>
                <div className="font-mono text-emerald-400 break-all">
                  {selectedEdge.matched_value}
                </div>
              </div>

              <div className="bg-slate-950/60 rounded p-3 border border-slate-800 space-y-1">
                <span className="text-slate-500 font-medium">Relationship Rationale:</span>
                <p className="text-slate-300 leading-relaxed mt-0.5">{selectedEdge.explanation}</p>
              </div>

              <div className="rounded-lg border border-amber-500/20 bg-amber-950/20 p-2.5 text-[11px] text-amber-300/90 leading-relaxed">
                <span className="font-bold">Attribution Disclaimer: </span>
                This edge indicates potential correlation based on technical indicator overlap only; it does not confirm common ownership.
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedEdge(null)}
                className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-1.5 text-xs font-semibold text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
