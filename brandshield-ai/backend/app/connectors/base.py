import abc
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConnectorState(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ConnectorStatus(BaseModel):
    connector_id: str
    display_name: str
    platform: str
    mode: str = "live"  # live, demo, manual
    state: ConnectorState
    last_checked: Optional[str] = None
    last_error_message: Optional[str] = None
    last_success_at: Optional[str] = None


class RawCandidate(BaseModel):
    candidate_id: str
    brand_id: Optional[str] = None
    candidate_type: str  # "social_profile" or "app_listing"
    platform: str        # "bluesky", "apple_app_store", etc.
    source_type: str = "live_connector"
    connector_id: str
    is_demo_data: bool = False
    is_synthetic: bool = False
    candidate_name: str
    description: Optional[str] = None
    bio: Optional[str] = None
    handle: Optional[str] = None
    canonical_profile_url: Optional[str] = None
    stable_account_id: Optional[str] = None
    app_name: Optional[str] = None
    package_or_bundle_id: Optional[str] = None
    canonical_listing_url: Optional[str] = None
    store: Optional[str] = None
    publisher_or_developer: Optional[str] = None
    publisher_id: Optional[str] = None
    external_links: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    image_hash: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    query_used: str = ""
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class BaseConnector(abc.ABC):
    """Abstract connector interface for real public ingestion sources."""

    def __init__(self, connector_id: str, display_name: str, platform: str, mode: str = "live"):
        self.id = connector_id
        self.display_name = display_name
        self.platform = platform
        self.mode = mode
        self._state: ConnectorState = ConnectorState.AVAILABLE
        self._last_checked: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_success: Optional[str] = None

    @abc.abstractmethod
    async def search(self, query: str) -> List[RawCandidate]:
        """Search public API for candidates matching query."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> ConnectorStatus:
        """Probe upstream service health."""
        pass

    def get_status(self) -> ConnectorStatus:
        return ConnectorStatus(
            connector_id=self.id,
            display_name=self.display_name,
            platform=self.platform,
            mode=self.mode,
            state=self._state,
            last_checked=self._last_checked,
            last_error_message=self._last_error,
            last_success_at=self._last_success,
        )

    def record_success(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._state = ConnectorState.AVAILABLE
        self._last_checked = now
        self._last_success = now
        self._last_error = None

    def record_failure(self, error_msg: str, is_degraded: bool = False) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._state = ConnectorState.DEGRADED if is_degraded else ConnectorState.UNAVAILABLE
        self._last_checked = now
        self._last_error = error_msg
