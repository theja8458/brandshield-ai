from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.campaigns.config import CAMPAIGN_DISCLAIMER


class GraphNode(BaseModel):
    id: str  # candidate_id
    label: str  # candidate_name
    brand_id: str
    candidate_type: str  # social_profile or app_listing
    platform: str
    score: int
    severity: str
    classification: str
    investigation_status: str
    is_demo_data: bool = False
    is_synthetic: bool = False
    source_type: str  # live_connector, manual, demo
    external_identifier: Optional[str] = None
    group_id: Optional[str] = None


class GraphEdge(BaseModel):
    id: str
    source: str  # source candidate_id
    target: str  # target candidate_id
    indicator_type: str
    matched_value: str
    explanation: str
    source_provenance: str = "demo"


class CampaignGroup(BaseModel):
    group_id: str
    label: str = "POTENTIAL_COORDINATION"
    member_candidate_ids: List[str]
    shared_indicator_types: List[str]
    links: List[GraphEdge] = Field(default_factory=list)
    group_size: int
    highest_risk: int
    highest_severity: str
    candidate_types: List[str]
    evidence_completeness: float = 1.0


class NonEdgesAudit(BaseModel):
    generic_domains_excluded: Dict[str, List[str]] = Field(default_factory=dict)
    official_domain_matches_excluded: Dict[str, List[str]] = Field(default_factory=dict)
    official_logo_matches_excluded: Dict[str, List[str]] = Field(default_factory=dict)
    official_publisher_matches_excluded: Dict[str, List[str]] = Field(default_factory=dict)


class CampaignGraphResponse(BaseModel):
    dataset_id: Optional[str] = None
    brand_id: Optional[str] = None
    is_synthetic: bool = False
    disclaimer: str = CAMPAIGN_DISCLAIMER
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    groups: List[CampaignGroup]
    unconnected_candidate_ids: List[str]
    non_edges_documented: NonEdgesAudit
