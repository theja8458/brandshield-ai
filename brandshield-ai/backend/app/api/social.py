import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.connectors.manager import BrandScanResponse, connector_manager
from app.crud.candidate import (
    create_manual_candidate,
    get_candidate,
    list_candidates,
    seed_social_demo_candidates,
    update_candidate_status,
)
from app.schemas.candidate import (
    CandidateListResponse,
    CandidateManualCreate,
    CandidateResponse,
    CandidateStatusUpdate,
)

router = APIRouter(prefix="/api/v1/social", tags=["Social Media Monitoring"])


@router.get("/candidates", response_model=CandidateListResponse)
def api_list_social_candidates(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    severity: Optional[str] = Query(None, description="Critical, High, Medium, Low"),
    status: Optional[str] = Query(None, description="new, investigating, resolved, false_positive"),
    source_type: Optional[str] = Query(None, description="live_connector, manual, demo"),
    search: Optional[str] = Query(None, description="Search handle or name"),
    include_official: bool = Query(False, description="Include excluded official assets in result"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    """
    List social media candidates with bounded pagination and multi-dimensional filters.
    Official excluded assets are filtered out of active alerts by default.
    """
    items, total = list_candidates(
        brand_id=brand_id,
        candidate_type="social_profile",
        severity=severity,
        status=status,
        source_type=source_type,
        search=search,
        include_official=include_official,
        page=page,
        limit=limit,
    )

    pages = math.ceil(total / limit) if total > 0 else 1
    return CandidateListResponse(
        items=[CandidateResponse(**item) for item in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def api_get_social_candidate(candidate_id: str):
    """Retrieve full details, signal breakdown, and evidence for a social candidate."""
    cand = get_candidate(candidate_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    return CandidateResponse(**cand)


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def api_create_manual_candidate(payload: CandidateManualCreate):
    """
    Submit a manual social media candidate.
    Evaluates against official guard and shared detection engine before persisting.
    """
    try:
        created = create_manual_candidate(payload.brand_id, payload)
        return CandidateResponse(**created)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.patch("/candidates/{candidate_id}/status", response_model=CandidateResponse)
def api_update_candidate_status(candidate_id: str, payload: CandidateStatusUpdate):
    """Update investigation status (new, investigating, resolved, false_positive)."""
    updated = update_candidate_status(candidate_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    return CandidateResponse(**updated)


@router.post("/brands/{brand_id}/scan", response_model=BrandScanResponse)
async def api_scan_social_brand(brand_id: str):
    """
    Execute live public social scan on Bluesky.
    Deduplicates by stable account ID, excludes official accounts, and scores threats.
    """
    try:
        res = await connector_manager.scan_brand(brand_id, target_connectors=["bluesky"])
        return res
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Social scan failed: {str(err)}",
        )


@router.post("/brands/{brand_id}/seed")
def api_seed_social_demo_candidates(brand_id: str):
    """
    Explicit separate endpoint to seed repeatable synthetic demo candidates for testing.
    All records are clearly tagged with source_type='demo' and is_demo_data=True.
    """
    try:
        count = seed_social_demo_candidates(brand_id)
        return {
            "status": "success",
            "brand_id": brand_id,
            "seeded_count": count,
            "message": f"Seeded {count} repeatable social demo candidates into MongoDB Atlas.",
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
