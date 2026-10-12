from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.connectors.base import ConnectorStatus
from app.connectors.manager import BrandScanResponse, connector_manager

router = APIRouter(tags=["Sources & Connectors"])


@router.get("/api/v1/sources", response_model=List[ConnectorStatus])
async def api_list_sources():
    """
    Retrieve telemetry status for all public and prototype connectors.
    Shows availability, error details, and last check timestamps.
    """
    statuses = await connector_manager.get_all_statuses()
    return statuses


@router.post("/api/v1/sources/{connector_id}/test", response_model=ConnectorStatus)
async def api_test_source(connector_id: str):
    """Trigger an immediate health check on a specific connector."""
    conn = connector_manager.get_connector(connector_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{connector_id}' not found.",
        )
    result = await conn.health_check()
    return result


@router.post("/api/v1/brands/{brand_id}/scan", response_model=BrandScanResponse)
async def api_scan_brand(
    brand_id: str,
    sources: Optional[str] = Query(
        default=None,
        description="Comma-separated connector IDs to run (e.g. apple_itunes,bluesky). Defaults to all live connectors.",
    ),
):
    """
    Execute a live scan across public connectors for the specified brand.
    Extracts candidates, deducts official assets, scores via the shared engine,
    and returns per-source audit summaries with graceful degradation.
    """
    target_list = None
    if sources:
        target_list = [s.strip() for s in sources.split(",") if s.strip()]

    try:
        scan_result = await connector_manager.scan_brand(brand_id, target_connectors=target_list)
        return scan_result
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan execution error: {str(err)}",
        )
