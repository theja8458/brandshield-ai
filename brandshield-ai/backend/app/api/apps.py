import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.connectors.manager import BrandScanResponse, connector_manager
from app.crud.candidate import (
    get_candidate,
    list_candidates,
    seed_app_demo_candidates,
    submit_manual_app_candidate,
    update_candidate_status,
)
from app.schemas.candidate import (
    AppManualCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateStatusUpdate,
)

router = APIRouter(prefix="/api/v1/apps", tags=["Mobile App Monitoring"])


@router.get("/candidates", response_model=CandidateListResponse)
def api_list_app_candidates(
    brand_id: Optional[str] = Query(None, description="Filter by brand ID"),
    store: Optional[str] = Query(None, description="Filter by app store platform"),
    severity: Optional[str] = Query(None, description="Critical, High, Medium, Low"),
    status: Optional[str] = Query(None, description="new, investigating, resolved, false_positive"),
    source_type: Optional[str] = Query(None, description="live_connector, manual, demo"),
    search: Optional[str] = Query(None, description="Search app name, bundle ID, or publisher"),
    include_official: bool = Query(False, description="Include excluded official assets in result"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    """
    List mobile app candidates with bounded pagination and multi-dimensional filters.
    Official excluded assets are filtered out of active alerts by default.
    """
    items, total = list_candidates(
        brand_id=brand_id,
        candidate_type="app_listing",
        platform=store,
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
def api_get_app_candidate(candidate_id: str):
    """Fetch details and full evidence breakdown for a single mobile app candidate."""
    item = get_candidate(candidate_id)
    if not item or item.get("candidate_type") != "app_listing":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App candidate '{candidate_id}' not found.",
        )
    return CandidateResponse(**item)


@router.post("/brands/{brand_id}/manual", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def api_submit_manual_app_candidate(brand_id: str, payload: AppManualCreate):
    """
    Manually submit a mobile app listing for suspiciousness analysis.
    Evaluates official guard before scoring. Labeled source_type='manual'.
    """
    try:
        created = submit_manual_app_candidate(brand_id, payload)
        return CandidateResponse(**created)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def api_create_manual_app_candidate(payload: AppManualCreate):
    """
    Manually submit a mobile app listing for suspiciousness analysis.
    Evaluates official guard before scoring. Labeled source_type='manual'.
    """
    if not payload.brand_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="brand_id is required in request body.",
        )
    try:
        created = submit_manual_app_candidate(payload.brand_id, payload)
        return CandidateResponse(**created)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.patch("/candidates/{candidate_id}/status", response_model=CandidateResponse)
def api_update_app_candidate_status(candidate_id: str, payload: CandidateStatusUpdate):
    """Update investigation status (new, investigating, resolved, false_positive)."""
    updated = update_candidate_status(candidate_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    return CandidateResponse(**updated)


@router.post("/brands/{brand_id}/scan", response_model=BrandScanResponse)
async def api_scan_app_brand(brand_id: str):
    """
    Execute live public app scan on Apple App Store (iTunes API).
    Deduplicates by bundle ID / track ID, excludes official accounts, and scores threats.
    """
    try:
        res = await connector_manager.scan_brand(brand_id, target_connectors=["apple_itunes"])
        return res
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan execution error: {str(err)}",
        )


@router.post("/brands/{brand_id}/seed")
def api_seed_app_demo_candidates(brand_id: str):
    """
    Seed repeatable synthetic mobile app candidates for demonstration and testing.
    All seeded records are explicitly labeled with source_type='demo' and is_synthetic=True.
    """
    try:
        count = seed_app_demo_candidates(brand_id)
        return {
            "status": "success",
            "message": f"Successfully seeded {count} synthetic app candidates for brand '{brand_id}'.",
            "count": count,
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed demo data: {str(err)}",
        )
