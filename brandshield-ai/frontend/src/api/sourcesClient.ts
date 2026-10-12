import { API_BASE_URL } from '../config';

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
  const res = await fetch(`${API_BASE_URL}/api/v1/sources`);
  if (!res.ok) {
    throw new Error(`Failed to fetch connector statuses (${res.status})`);
  }
  return res.json();
}

export async function testSourceConnection(connectorId: string): Promise<ConnectorStatus> {
  const res = await fetch(`${API_BASE_URL}/api/v1/sources/${connectorId}/test`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to test connector (${res.status})`);
  }
  return res.json();
}

export async function runBrandScan(
  brandId: string,
  sources?: string[]
): Promise<BrandScanResponse> {
  const queryParam = sources && sources.length > 0 ? `?sources=${sources.join(',')}` : '';
  const res = await fetch(`${API_BASE_URL}/api/v1/brands/${brandId}/scan${queryParam}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Scan failed (${res.status})`);
  }
  return res.json();
}
