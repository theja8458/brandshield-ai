import { apiFetch } from './apiClient';

export interface ConnectorStatus {
  connector_id: string;
  display_name: string;
  platform: string;
  mode: 'live' | 'demo' | 'manual';
  state: 'available' | 'degraded' | 'unavailable';
  last_checked?: string;
  last_error_message?: string;
  last_success_at?: string;
}

export interface SourceScanResult {
  connector_id: string;
  display_name: string;
  ok: boolean;
  candidates_found: number;
  new_candidates: number;
  excluded_official: number;
  error?: string;
}

export interface BrandScanResponse {
  brand_id: string;
  total_found: number;
  total_new: number;
  total_excluded_official: number;
  source_results: SourceScanResult[];
  scanned_at: string;
}

export async function fetchSources(): Promise<ConnectorStatus[]> {
  return apiFetch<ConnectorStatus[]>('/api/v1/sources');
}

export async function testSourceConnection(connectorId: string): Promise<ConnectorStatus> {
  return apiFetch<ConnectorStatus>(`/api/v1/sources/${connectorId}/test`, {
    method: 'POST',
  });
}

export async function runBrandScan(
  brandId: string,
  sources?: string[]
): Promise<BrandScanResponse> {
  const queryParam = sources && sources.length > 0 ? `?sources=${sources.join(',')}` : '';
  return apiFetch<BrandScanResponse>(`/api/v1/brands/${brandId}/scan${queryParam}`, {
    method: 'POST',
  });
}
