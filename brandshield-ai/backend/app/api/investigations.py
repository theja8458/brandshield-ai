from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.crud.candidate import (
    get_candidate,
    get_candidate_evidence,
    list_candidates,
    update_candidate_status,
)
from app.schemas.candidate import (
    CandidateListResponse,
    CandidateResponse,
    CandidateStatusUpdate,
    EvidenceDetailResponse,
)

router = APIRouter(tags=["Investigations & Evidence"])


@router.get("/api/v1/investigations/candidates", response_model=CandidateListResponse)
def api_list_investigation_candidates(
    brand_id: Optional[str] = Query(None, description="Filter by brand UUID"),
    candidate_type: Optional[str] = Query(None, description="social_profile or app_listing"),
    platform: Optional[str] = Query(None, description="Platform or store identifier"),
    severity: Optional[str] = Query(None, description="Critical, High, Medium, Low, Review Required"),
    status: Optional[str] = Query(None, description="new, investigating, resolved, false_positive"),
    source_type: Optional[str] = Query(None, description="live_connector, manual, demo"),
    search: Optional[str] = Query(None, description="Search term for name/handle/bundle"),
    include_official: bool = Query(False, description="Include excluded official assets"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Unified investigation listing across both social profiles and mobile app candidates.
    Supports bounded pagination and full triage filtering.
    """
    items, total = list_candidates(
        brand_id=brand_id,
        candidate_type=candidate_type,
        platform=platform,
        severity=severity,
        status=status,
        source_type=source_type,
        search=search,
        include_official=include_official,
        page=page,
        limit=limit,
    )
    pages = (total + limit - 1) // limit if total > 0 else 1
    return CandidateListResponse(
        items=[CandidateResponse(**item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/api/v1/investigations/candidates/{candidate_id}", response_model=CandidateResponse)
def api_get_investigation_candidate(candidate_id: str):
    """Retrieve single candidate details for investigation triage."""
    cand = get_candidate(candidate_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    return CandidateResponse(**cand)


@router.get("/api/v1/investigations/candidates/{candidate_id}/evidence", response_model=EvidenceDetailResponse)
@router.get("/api/v1/evidence/{candidate_id}", response_model=EvidenceDetailResponse)
def api_get_candidate_evidence(candidate_id: str):
    """
    Retrieve comprehensive evidentiary trail, scoring breakdown, and audit history.
    Includes timestamps, source connector attribution, observed signals, and uncertainty metrics.
    """
    evidence = get_candidate_evidence(candidate_id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate or evidence for '{candidate_id}' not found.",
        )
    return EvidenceDetailResponse(**evidence)


@router.patch("/api/v1/investigations/candidates/{candidate_id}/status", response_model=CandidateResponse)
def api_update_investigation_status(candidate_id: str, payload: CandidateStatusUpdate):
    """
    Transition investigation status (new -> investigating -> resolved / false_positive).
    Records audit history entry with timestamp and notes.
    """
    updated = update_candidate_status(candidate_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    return CandidateResponse(**updated)
