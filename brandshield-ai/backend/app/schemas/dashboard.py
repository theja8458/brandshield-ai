from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.candidate import CandidateResponse


class SeverityBreakdown(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    critical: int = Field(0, alias="Critical")
    high: int = Field(0, alias="High")
    medium: int = Field(0, alias="Medium")
    low: int = Field(0, alias="Low")
    review_required: int = Field(0, alias="Review Required")


class InvestigationStatusBreakdown(BaseModel):
    new: int = 0
    investigating: int = 0
    resolved: int = 0
    false_positive: int = 0


class ProvenanceBreakdown(BaseModel):
    live_connector: int = 0
    manual: int = 0
    demo: int = 0


class CandidateTypeBreakdown(BaseModel):
    social_profile: int = 0
    app_listing: int = 0


class MetricDefinition(BaseModel):
    name: str
    description: str
    calculation: str
    integrity_rule: str


class DashboardMetricsResponse(BaseModel):
    monitored_brands_count: int
    total_candidates_analyzed: int
    candidates_by_type: CandidateTypeBreakdown
    active_threats_count: int
    active_threats_by_severity: Dict[str, int]
    official_assets_excluded: int
    identity_reviews_required: int
    investigation_status_distribution: InvestigationStatusBreakdown
    provenance_breakdown: ProvenanceBreakdown
    potential_campaign_groups: int = 0
    connector_health: Dict[str, Any]
    recent_detections: List[CandidateResponse]
    metric_definitions: List[MetricDefinition]
