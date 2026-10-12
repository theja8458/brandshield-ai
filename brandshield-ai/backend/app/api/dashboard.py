from fastapi import APIRouter
from app.crud.dashboard import get_dashboard_metrics
from app.schemas.dashboard import DashboardMetricsResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def api_get_dashboard_metrics():
    """
    Retrieve real-time metrics aggregated from MongoDB Atlas collections.
    Includes active threats, severity distributions, exclusion counts, connector health,
    recent detections, and metric definitions.
    """
    metrics = await get_dashboard_metrics()
    return DashboardMetricsResponse(**metrics)
