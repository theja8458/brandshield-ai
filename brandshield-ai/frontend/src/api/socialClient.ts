import { API_BASE_URL } from '../config';

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
  limit: number;
  pages: number;
}

export interface SocialFilterParams {
  brand_id?: string;
  severity?: string;
  status?: string;
  source_type?: string;
  search?: string;
  include_official?: boolean;
  page?: number;
  limit?: number;
}

export async function fetchSocialCandidates(
  params: SocialFilterParams
): Promise<CandidateListResponse> {
  const query = new URLSearchParams();
  if (params.brand_id) query.set('brand_id', params.brand_id);
  if (params.severity) query.set('severity', params.severity);
  if (params.status) query.set('status', params.status);
  if (params.source_type) query.set('source_type', params.source_type);
  if (params.search) query.set('search', params.search);
  if (params.include_official) query.set('include_official', 'true');
  if (params.page) query.set('page', params.page.toString());
  if (params.limit) query.set('limit', params.limit.toString());

  const res = await fetch(`${API_BASE_URL}/api/v1/social/candidates?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch social candidates (${res.status})`);
  }
  return res.json();
}

export async function submitManualCandidate(payload: {
  brand_id: string;
  display_name: string;
  handle: string;
  canonical_profile_url?: string;
  bio?: string;
  external_links?: string[];
}): Promise<Candidate> {
  const res = await fetch(`${API_BASE_URL}/api/v1/social/candidates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      candidate_type: 'social_profile',
      platform: 'bluesky',
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Submission failed (${res.status})`);
  }
  return res.json();
}

export async function updateCandidateInvestigationStatus(
  candidateId: string,
  status: 'new' | 'investigating' | 'resolved' | 'false_positive',
  notes?: string
): Promise<Candidate> {
  const res = await fetch(`${API_BASE_URL}/api/v1/social/candidates/${candidateId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Status update failed (${res.status})`);
  }
  return res.json();
}

export async function scanSocialMedia(brandId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/social/brands/${brandId}/scan`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Social scan failed (${res.status})`);
  }
  return res.json();
}

export async function seedSocialDemo(brandId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/social/brands/${brandId}/seed`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Seeding demo failed (${res.status})`);
  }
  return res.json();
}
