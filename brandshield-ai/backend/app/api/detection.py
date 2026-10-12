from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.crud.brand import get_brand
from app.detection.engine import (
    DetectionEvaluationResult,
    evaluate_candidate,
)

router = APIRouter(prefix="/api/v1/detection", tags=["Detection Engine"])


class EvaluateCandidateRequest(BaseModel):
    brand_id: str = Field(..., description="Target brand identifier")
    candidate: Dict[str, Any] = Field(..., description="Candidate telemetry record")


@router.post("/evaluate", response_model=DetectionEvaluationResult)
def api_evaluate_candidate(request: EvaluateCandidateRequest):
    """
    Run the deterministic BrandShield AI detection engine on a candidate record.
    Evaluates official safety guards, name similarity, lookalike domains,
    publisher mismatch, scam phrasing, description similarity, and logo pHash.
    """
    brand = get_brand(request.brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{request.brand_id}' not found in database.",
        )

    result = evaluate_candidate(brand, request.candidate)
    return result
