import { apiFetch } from './apiClient';

export interface GraphNode {
  id: string; // candidate_id
  label: string; // candidate_name
  brand_id: string;
  candidate_type: 'social_profile' | 'app_listing';
  platform: string;
  score: number;
  severity: 'Critical' | 'High' | 'Medium' | 'Low' | 'Review Required';
  classification: string;
  investigation_status: string;
  is_demo_data: boolean;
  is_synthetic: boolean;
  source_type: 'live_connector' | 'manual' | 'demo';
  external_identifier?: string;
  group_id?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  indicator_type: string;
  matched_value: string;
  explanation: string;
  source_provenance: string;
}

export interface CampaignGroup {
  group_id: string;
  label: string; // "POTENTIAL_COORDINATION"
  member_candidate_ids: string[];
  shared_indicator_types: string[];
  links: GraphEdge[];
  group_size: number;
  highest_risk: number;
  highest_severity: string;
  candidate_types: string[];
  evidence_completeness: number;
}

export interface NonEdgesAudit {
  generic_domains_excluded: Record<string, string[]>;
  official_domain_matches_excluded: Record<string, string[]>;
  official_logo_matches_excluded: Record<string, string[]>;
  official_publisher_matches_excluded: Record<string, string[]>;
}

export interface CampaignGraphResponse {
  dataset_id?: string;
  brand_id?: string;
  is_synthetic: boolean;
  disclaimer: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  groups: CampaignGroup[];
  unconnected_candidate_ids: string[];
  non_edges_documented: NonEdgesAudit;
}

export async function fetchCampaignGraph(
  brandId?: string,
  includeOfficial: boolean = false
): Promise<CampaignGraphResponse> {
  const query = new URLSearchParams();
  if (brandId) query.set('brand_id', brandId);
  if (includeOfficial) query.set('include_official', 'true');

  return apiFetch<CampaignGraphResponse>(`/api/v1/campaigns/graph?${query.toString()}`);
}

export async function fetchCampaignGroups(brandId?: string): Promise<CampaignGroup[]> {
  const query = new URLSearchParams();
  if (brandId) query.set('brand_id', brandId);

  return apiFetch<CampaignGroup[]>(`/api/v1/campaigns/groups?${query.toString()}`);
}

export async function seedNovaPayCampaigns(): Promise<{
  status: string;
  brand_id: string;
  campaign_groups_detected: number;
  total_edges: number;
  message: string;
}> {
  return apiFetch('/api/v1/campaigns/seed/novapay', {
    method: 'POST',
  });
}
