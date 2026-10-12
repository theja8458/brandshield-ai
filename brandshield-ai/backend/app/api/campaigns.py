from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.campaigns.graph_builder import get_brand_campaign_graph
from app.crud.brand import get_brand, seed_novapay
from app.crud.candidate import seed_app_demo_candidates, seed_social_demo_candidates
from app.schemas.campaign import CampaignGraphResponse, CampaignGroup

router = APIRouter(prefix="/api/v1/campaigns", tags=["Impersonation Campaign Graph"])


@router.get("/graph", response_model=CampaignGraphResponse)
def api_get_campaign_graph(
    brand_id: Optional[str] = Query(None, description="Optional brand UUID to filter graph"),
    include_official: bool = Query(False, description="Include excluded official assets"),
):
    """
    Retrieve live Impersonation Campaign Graph derived from MongoDB Atlas candidate records.
    Constructs nodes, qualifying indicator edges, and POTENTIAL_COORDINATION groups.
    """
    if brand_id:
        brand = get_brand(brand_id)
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand '{brand_id}' not found.",
            )

    graph_res = get_brand_campaign_graph(
        brand_id=brand_id,
        include_official=include_official,
    )
    return graph_res


@router.get("/groups", response_model=List[CampaignGroup])
def api_list_campaign_groups(
    brand_id: Optional[str] = Query(None, description="Optional brand UUID"),
):
    """List summary of all potential campaign groups derived from shared concrete indicators."""
    graph_res = get_brand_campaign_graph(brand_id=brand_id)
    return graph_res.groups


@router.get("/groups/{group_id}", response_model=CampaignGroup)
def api_get_campaign_group(
    group_id: str,
    brand_id: Optional[str] = Query(None, description="Optional brand UUID"),
):
    """Retrieve details for a single campaign group."""
    graph_res = get_brand_campaign_graph(brand_id=brand_id)
    group = next((g for g in graph_res.groups if g.group_id == group_id), None)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign group '{group_id}' not found.",
        )
    return group


@router.post("/seed/novapay", status_code=status.HTTP_200_OK)
def api_seed_novapay_campaigns():
    """
    Explicit endpoint to seed the repeatable NovaPay synthetic demonstration scenario.
    Seeds the NovaPay brand, social candidates, and mobile app candidates into Atlas,
    yielding auditable campaign groups and documented non-edges.
    """
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    social_count = seed_social_demo_candidates(brand_id)
    app_count = seed_app_demo_candidates(brand_id)

    graph = get_brand_campaign_graph(brand_id=brand_id)

    return {
        "status": "success",
        "brand_id": brand_id,
        "social_candidates_seeded": social_count,
        "app_candidates_seeded": app_count,
        "campaign_groups_detected": len(graph.groups),
        "total_edges": len(graph.edges),
        "message": (
            f"Seeded NovaPay synthetic dataset. Detected {len(graph.groups)} potential coordination "
            f"groups across {len(graph.edges)} indicator-backed edges."
        ),
    }
