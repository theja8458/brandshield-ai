import { API_BASE_URL } from '../config';
import { Candidate, CandidateListResponse } from './socialClient';

export interface InvestigationHistoryEntry {
  status: string;
  timestamp: string;
  notes?: string;
}

export interface EvidenceDetail {
  candidate_id: string;
  brand_id: string;
  candidate_name: string;
  candidate_type: string;
  platform: string;
  source_type: 'live_connector' | 'manual' | 'demo';
  connector_id?: string;
  is_demo_data: boolean;
  is_synthetic: boolean;
  collected_at?: string;
  analyzed_at?: string;
  query_used?: string;
  score: number;
  severity: 'Critical' | 'High' | 'Medium' | 'Low' | 'Review Required';
  classification: string;
  classification_reason?: string;
  signals: Array<{
    id: string;
    family: string;
    points: number;
    max_points: number;
    matched_field: string;
    matched_value: string;
    human_readable_reason: string;
  }>;
  evidence: Record<string, unknown>;
  missing_evidence: string[];
  evidence_completeness: number;
  official_exclusion_reason?: string;
  investigation_status: 'new' | 'investigating' | 'resolved' | 'false_positive';
  status_updated_at?: string;
  status_notes?: string;
  investigation_history: InvestigationHistoryEntry[];
  external_identifiers: Record<string, string>;
}

export interface InvestigationFilterParams {
  brand_id?: string;
  candidate_type?: string;
  platform?: string;
  severity?: string;
  status?: string;
  source_type?: string;
  search?: string;
  include_official?: boolean;
  page?: number;
  limit?: number;
}

export async function fetchInvestigationCandidates(
  params: InvestigationFilterParams = {}
): Promise<CandidateListResponse> {
  const query = new URLSearchParams();
  if (params.brand_id) query.set('brand_id', params.brand_id);
  if (params.candidate_type) query.set('candidate_type', params.candidate_type);
  if (params.platform) query.set('platform', params.platform);
  if (params.severity) query.set('severity', params.severity);
  if (params.status) query.set('status', params.status);
  if (params.source_type) query.set('source_type', params.source_type);
  if (params.search) query.set('search', params.search);
  if (params.include_official) query.set('include_official', 'true');
  if (params.page) query.set('page', params.page.toString());
  if (params.limit) query.set('limit', params.limit.toString());

  const res = await fetch(`${API_BASE_URL}/api/v1/investigations/candidates?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch candidates (${res.status})`);
  }
  return res.json();
}

export async function fetchCandidateEvidence(candidateId: string): Promise<EvidenceDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/evidence/${candidateId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch evidence for ${candidateId} (${res.status})`);
  }
  return res.json();
}

export async function updateCandidateStatus(
  candidateId: string,
  status: 'new' | 'investigating' | 'resolved' | 'false_positive',
  notes?: string
): Promise<Candidate> {
  const res = await fetch(`${API_BASE_URL}/api/v1/investigations/candidates/${candidateId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, notes: notes || '' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update investigation status (${res.status})`);
  }
  return res.json();
}
