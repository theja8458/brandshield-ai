import { apiFetch } from './apiClient';

export interface DetectionSignal {
  id: string;
  family: string;
  points: number;
  max_points: number;
  matched_field: string;
  matched_value: string;
  human_readable_reason: string;
}

export interface Candidate {
  candidate_id: string;
  brand_id: string;
  candidate_type: string;
  platform: string;
  source_type: 'live_connector' | 'manual' | 'demo';
  connector_id?: string;
  is_demo_data: boolean;
  is_synthetic: boolean;
  candidate_name: string;
  display_name?: string;
  handle?: string;
  canonical_profile_url?: string;
  stable_account_id?: string;
  app_name?: string;
  package_or_bundle_id?: string;
  canonical_listing_url?: string;
  store?: string;
  publisher_or_developer?: string;
  publisher_id?: string;
  bio?: string;
  description?: string;
  external_links: string[];
  image_url?: string;
  image_hash?: string;
  score: number;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  classification: 'OFFICIAL_EXCLUDED' | 'REVIEW_REQUIRED' | 'POTENTIAL_THREAT' | 'LOW_RISK';
  signals: DetectionSignal[];
  evidence: Record<string, unknown>;
  missing_evidence: string[];
  evidence_completeness: number;
  investigation_status: 'new' | 'investigating' | 'resolved' | 'false_positive';
  status_updated_at?: string;
  status_notes?: string;
  investigation_history?: Array<{
    status: string;
    timestamp: string;
    notes?: string;
  }>;
  collected_at?: string;
  analyzed_at?: string;
  query_used?: string;
}

export interface CandidateListResponse {
  items: Candidate[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export async function fetchSocialCandidates(params: {
  brand_id?: string;
  severity?: string;
  status?: string;
  source_type?: string;
  search?: string;
  include_official?: boolean;
  page?: number;
  limit?: number;
}): Promise<CandidateListResponse> {
  const query = new URLSearchParams();
  if (params.brand_id) query.set('brand_id', params.brand_id);
  if (params.severity) query.set('severity', params.severity);
  if (params.status) query.set('status', params.status);
  if (params.source_type) query.set('source_type', params.source_type);
  if (params.search) query.set('search', params.search);
  if (params.include_official) query.set('include_official', 'true');
  if (params.page) query.set('page', params.page.toString());
  if (params.limit) query.set('limit', params.limit.toString());

  return apiFetch<CandidateListResponse>(`/api/v1/social/candidates?${query.toString()}`);
}

export async function submitManualCandidate(payload: {
  brand_id: string;
  display_name: string;
  handle: string;
  canonical_profile_url?: string;
  bio?: string;
  external_links?: string[];
}): Promise<Candidate> {
  return apiFetch<Candidate>('/api/v1/social/candidates', {
    method: 'POST',
    body: JSON.stringify({
      ...payload,
      candidate_type: 'social_profile',
      platform: 'bluesky',
    }),
  });
}

export async function updateCandidateInvestigationStatus(
  candidateId: string,
  status: 'new' | 'investigating' | 'resolved' | 'false_positive',
  notes?: string
): Promise<Candidate> {
  return apiFetch<Candidate>(`/api/v1/social/candidates/${candidateId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, notes }),
  });
}

export async function scanSocialMedia(brandId: string) {
  return apiFetch(`/api/v1/social/brands/${brandId}/scan`, {
    method: 'POST',
  });
}

export async function seedSocialDemo(brandId: string) {
  return apiFetch(`/api/v1/social/brands/${brandId}/seed`, {
    method: 'POST',
  });
}
