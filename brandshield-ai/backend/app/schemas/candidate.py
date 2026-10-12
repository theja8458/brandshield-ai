from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InvestigationStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class CandidateType(str, Enum):
    SOCIAL_PROFILE = "social_profile"
    APP_LISTING = "app_listing"


class CandidateManualCreate(BaseModel):
    brand_id: str
    candidate_type: str = "social_profile"
    platform: str = "bluesky"
    display_name: str = Field(..., min_length=1, max_length=100)
    handle: str = Field(..., min_length=1, max_length=100)
    canonical_profile_url: Optional[str] = None
    stable_account_id: Optional[str] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    external_links: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None


class AppManualCreate(BaseModel):
    brand_id: Optional[str] = None
    app_name: str = Field(..., min_length=1, max_length=150)
    store: str = Field(default="apple_app_store")
    package_or_bundle_id: Optional[str] = None
    publisher_or_developer: Optional[str] = None
    publisher_id: Optional[str] = None
    canonical_listing_url: Optional[str] = None
    description: Optional[str] = None
    external_links: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None


class InvestigationHistoryEntry(BaseModel):
    status: str
    timestamp: str
    notes: Optional[str] = ""


class CandidateStatusUpdate(BaseModel):
    status: InvestigationStatus
    notes: Optional[str] = None


class CandidateResponse(BaseModel):
    candidate_id: str
    brand_id: str
    candidate_type: str
    platform: str
    source_type: str  # live_connector, manual, demo
    connector_id: Optional[str] = None
    is_demo_data: bool = False
    is_synthetic: bool = False
    candidate_name: str
    display_name: Optional[str] = None
    handle: Optional[str] = None
    canonical_profile_url: Optional[str] = None
    stable_account_id: Optional[str] = None
    app_name: Optional[str] = None
    package_or_bundle_id: Optional[str] = None
    canonical_listing_url: Optional[str] = None
    store: Optional[str] = None
    publisher_or_developer: Optional[str] = None
    publisher_id: Optional[str] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    external_links: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    image_hash: Optional[str] = None
    score: int
    severity: str
    classification: str
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    missing_evidence: List[str] = Field(default_factory=list)
    evidence_completeness: float = 1.0
    investigation_status: str = "new"
    status_updated_at: Optional[str] = None
    status_notes: Optional[str] = None
    investigation_history: List[InvestigationHistoryEntry] = Field(default_factory=list)
    collected_at: Optional[str] = None
    analyzed_at: Optional[str] = None
    query_used: Optional[str] = None


class CandidateListResponse(BaseModel):
    items: List[CandidateResponse]
    total: int
    page: int
    limit: int
    pages: int


class EvidenceDetailResponse(BaseModel):
    candidate_id: str
    brand_id: str
    candidate_name: str
    candidate_type: str
    platform: str
    source_type: str
    connector_id: Optional[str] = None
    is_demo_data: bool = False
    is_synthetic: bool = False
    collected_at: Optional[str] = None
    analyzed_at: Optional[str] = None
    query_used: Optional[str] = None
    score: int
    severity: str
    classification: str
    classification_reason: Optional[str] = None
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    missing_evidence: List[str] = Field(default_factory=list)
    evidence_completeness: float = 1.0
    official_exclusion_reason: Optional[str] = None
    investigation_status: str = "new"
    status_updated_at: Optional[str] = None
    status_notes: Optional[str] = None
    investigation_history: List[InvestigationHistoryEntry] = Field(default_factory=list)
    external_identifiers: Dict[str, Any] = Field(default_factory=dict)
