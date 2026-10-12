from typing import Any, Dict, List
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.crud.brand import (
    create_brand,
    delete_brand,
    get_brand,
    list_brands,
    seed_novapay,
    update_brand,
)
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate, OfficialLogo
from app.services.image_hasher import compute_image_phash
from app.services.official_guard import OfficialEvaluationResult, evaluate_official_status

router = APIRouter(prefix="/api/v1/brands", tags=["Brands"])


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def api_create_brand(brand_in: BrandCreate):
    """Register a new monitored brand with official assets."""
    # Check for name conflict
    existing = get_brand(brand_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Brand with name '{brand_in.name}' is already registered.",
        )
    created = create_brand(brand_in)
    return created


@router.get("", response_model=List[BrandResponse])
def api_list_brands():
    """List all registered brand profiles."""
    return list_brands()


@router.post("/seed/novapay", response_model=BrandResponse)
def api_seed_novapay():
    """Explicit repeatable seed endpoint for fictional brand NovaPay."""
    seeded = seed_novapay()
    return seeded


@router.get("/{brand_id}", response_model=BrandResponse)
def api_get_brand(brand_id: str):
    """Retrieve details for a specific brand profile."""
    brand = get_brand(brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{brand_id}' not found.",
        )
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
def api_update_brand(brand_id: str, update_in: BrandUpdate):
    """Update brand profile fields and registered assets."""
    updated = update_brand(brand_id, update_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{brand_id}' not found.",
        )
    return updated


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_brand(brand_id: str):
    """Delete a brand profile."""
    ok = delete_brand(brand_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{brand_id}' not found.",
        )
    return None


@router.post("/{brand_id}/logo", response_model=BrandResponse)
async def api_upload_brand_logo(brand_id: str, file: UploadFile = File(...)):
    """
    Upload an official brand logo. Computes and stores perceptual hash (pHash).
    Restricted to PNG, JPEG, WEBP and size < 2MB.
    """
    brand = get_brand(brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{brand_id}' not found.",
        )

    file_bytes = await file.read()
    try:
        phash_str, fmt = compute_image_phash(file_bytes)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    logo_obj = OfficialLogo(
        image_reference=f"uploaded_{brand_id}_logo.{fmt.lower()}",
        image_hash=phash_str,
        hash_algorithm="imagehash.phash(hash_size=8)",
    )

    updated = update_brand(brand_id, BrandUpdate(official_logo=logo_obj))
    return updated


@router.post("/{brand_id}/evaluate-asset", response_model=OfficialEvaluationResult)
def api_evaluate_asset(brand_id: str, candidate_payload: Dict[str, Any]):
    """
    CRITICAL SAFETY GUARD ENDPOINT:
    Test candidate asset against official brand assets BEFORE scoring.
    Returns OFFICIAL_EXCLUDED, REVIEW_REQUIRED, SAFE_LISTED, or NOT_OFFICIAL.
    """
    brand = get_brand(brand_id)
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand '{brand_id}' not found.",
        )

    result = evaluate_official_status(brand, candidate_payload)
    return result
