import { apiFetch } from './apiClient';
import { Candidate, CandidateListResponse } from './socialClient';

export interface AppFilterParams {
  brand_id?: string;
  store?: string;
  severity?: string;
  status?: string;
  source_type?: string;
  search?: string;
  include_official?: boolean;
  page?: number;
  limit?: number;
}

export async function fetchAppCandidates(
  params: AppFilterParams
): Promise<CandidateListResponse> {
  const query = new URLSearchParams();
  if (params.brand_id) query.set('brand_id', params.brand_id);
  if (params.store) query.set('store', params.store);
  if (params.severity) query.set('severity', params.severity);
  if (params.status) query.set('status', params.status);
  if (params.source_type) query.set('source_type', params.source_type);
  if (params.search) query.set('search', params.search);
  if (params.include_official) query.set('include_official', 'true');
  if (params.page) query.set('page', params.page.toString());
  if (params.limit) query.set('limit', params.limit.toString());

  return apiFetch<CandidateListResponse>(`/api/v1/apps/candidates?${query.toString()}`);
}

export async function submitManualAppCandidate(
  brandId: string,
  payload: {
    app_name: string;
    store?: string;
    package_or_bundle_id?: string;
    publisher_or_developer?: string;
    publisher_id?: string;
    canonical_listing_url?: string;
    description?: string;
    external_links?: string[];
  }
): Promise<Candidate> {
  return apiFetch<Candidate>(`/api/v1/apps/brands/${brandId}/manual`, {
    method: 'POST',
    body: JSON.stringify({
      brand_id: brandId,
      store: payload.store || 'apple_app_store',
      app_name: payload.app_name,
      package_or_bundle_id: payload.package_or_bundle_id || null,
      publisher_or_developer: payload.publisher_or_developer || null,
      publisher_id: payload.publisher_id || null,
      canonical_listing_url: payload.canonical_listing_url || null,
      description: payload.description || null,
      external_links: payload.external_links || [],
    }),
  });
}

export async function updateAppInvestigationStatus(
  candidateId: string,
  status: 'new' | 'investigating' | 'resolved' | 'false_positive',
  notes?: string
): Promise<Candidate> {
  return apiFetch<Candidate>(`/api/v1/apps/candidates/${candidateId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, notes }),
  });
}

export async function scanAppStore(brandId: string) {
  return apiFetch(`/api/v1/apps/brands/${brandId}/scan`, {
    method: 'POST',
  });
}

export async function seedAppDemo(brandId: string) {
  return apiFetch(`/api/v1/apps/brands/${brandId}/seed`, {
    method: 'POST',
  });
}
