import { API_BASE_URL } from '../config';
import { Candidate } from './socialClient';

export interface MetricDefinition {
  name: string;
  description: string;
  calculation: string;
  integrity_rule: string;
}

export interface ConnectorHealthItem {
  connector_id: string;
  display_name: string;
  platform: string;
  mode: string;
  state: 'available' | 'degraded' | 'unavailable';
  last_checked?: string;
  last_success_at?: string;
  error_message?: string;
}

export interface DashboardMetrics {
  monitored_brands_count: number;
  total_candidates_analyzed: number;
  candidates_by_type: {
    social_profile: number;
    app_listing: number;
  };
  active_threats_count: number;
  active_threats_by_severity: {
    Critical: number;
    High: number;
    Medium: number;
    Low: number;
    'Review Required': number;
  };
  official_assets_excluded: number;
  identity_reviews_required: number;
  investigation_status_distribution: {
    new: number;
    investigating: number;
    resolved: number;
    false_positive: number;
  };
  provenance_breakdown: {
    live_connector: number;
    manual: number;
    demo: number;
  };
  potential_campaign_groups: number;
  connector_health: {
    total: number;
    connectors: ConnectorHealthItem[];
  };
  recent_detections: Candidate[];
  metric_definitions: MetricDefinition[];
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const res = await fetch(`${API_BASE_URL}/api/v1/dashboard/metrics`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch dashboard metrics (${res.status})`);
  }
  return res.json();
}
