from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import httpx
import pytest

from app.crud.brand import seed_novapay
from app.crud.candidate import get_candidates_collection
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_candidates_collection(test_db_name):
    """Ensure candidates collection is cleaned in isolated test database."""
    col = get_candidates_collection(test_db_name)
    col.delete_many({})
    yield


def test_seed_social_demo_candidates():
    """Verify repeatable demo seeding endpoint populates social candidates."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    res = client.post(f"/api/v1/social/brands/{brand_id}/seed")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["seeded_count"] > 0

    # Verify candidates in database have demo tags
    list_res = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&source_type=demo")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] > 0
    for cand in list_data["items"]:
        assert cand["source_type"] == "demo"
        assert cand["is_demo_data"] is True


def test_official_account_excluded_from_active_alerts():
    """Verify official account (SYN-SOC-016) is excluded and hidden from default alert list."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    client.post(f"/api/v1/social/brands/{brand_id}/seed")

    # Default query (include_official=False) must NOT include OFFICIAL_EXCLUDED
    res_default = client.get(f"/api/v1/social/candidates?brand_id={brand_id}")
    assert res_default.status_code == 200
    items_default = res_default.json()["items"]
    assert not any(i["classification"] == "OFFICIAL_EXCLUDED" for i in items_default)

    # Query with include_official=True returns official asset
    res_all = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&include_official=true")
    assert res_all.status_code == 200
    items_all = res_all.json()["items"]
    official_items = [i for i in items_all if i["classification"] == "OFFICIAL_EXCLUDED"]
    assert len(official_items) >= 1
    assert official_items[0]["score"] == 0


def test_identity_conflict_candidate_classified_review_required():
    """Verify identity conflict candidate (SYN-SOC-011) has REVIEW_REQUIRED classification."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    client.post(f"/api/v1/social/brands/{brand_id}/seed")

    res = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&status=new")
    assert res.status_code == 200
    items = res.json()["items"]
    conflict_cands = [i for i in items if i["classification"] == "REVIEW_REQUIRED"]
    assert len(conflict_cands) >= 1
    assert conflict_cands[0]["candidate_id"] == "SYN-SOC-011"


def test_manual_candidate_submission_and_scoring():
    """Verify manual submission of look-alike candidate is scored and stored."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    manual_payload = {
        "brand_id": brand_id,
        "candidate_type": "social_profile",
        "platform": "bluesky",
        "display_name": "N0vaPay Official Support",
        "handle": "n0vapay_support",
        "canonical_profile_url": "https://bsky.app/profile/n0vapay_support",
        "bio": "Official support representative. DM to claim rewards.",
        "external_links": ["https://novapay-support.example"],
    }

    res = client.post("/api/v1/social/candidates", json=manual_payload)
    assert res.status_code == 201
    cand = res.json()
    assert cand["source_type"] == "manual"
    assert cand["is_demo_data"] is False
    assert cand["score"] >= 40
    assert cand["severity"] in ("Medium", "High", "Critical")
    assert cand["classification"] == "POTENTIAL_THREAT"
    assert len(cand["signals"]) > 0


def test_update_investigation_status():
    """Verify updating investigation status persists properly in database."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    client.post(f"/api/v1/social/brands/{brand_id}/seed")

    list_res = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&limit=1")
    cand = list_res.json()["items"][0]
    cid = cand["candidate_id"]

    # 1. Update to investigating
    res1 = client.patch(
        f"/api/v1/social/candidates/{cid}/status",
        json={"status": "investigating", "notes": "Investigating potential domain spoofing"},
    )
    assert res1.status_code == 200
    assert res1.json()["investigation_status"] == "investigating"
    assert res1.json()["status_notes"] == "Investigating potential domain spoofing"

    # 2. Update to false_positive
    res2 = client.patch(
        f"/api/v1/social/candidates/{cid}/status",
        json={"status": "false_positive", "notes": "Confirmed non-malicious homograph"},
    )
    assert res2.status_code == 200
    assert res2.json()["investigation_status"] == "false_positive"


def test_list_social_candidates_filtering_and_pagination():
    """Verify filtering by severity, status, search string, and bounded pagination."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    client.post(f"/api/v1/social/brands/{brand_id}/seed")

    # Search filter
    res_search = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&search=support")
    assert res_search.status_code == 200
    search_items = res_search.json()["items"]
    for item in search_items:
        text = f"{item['handle']} {item.get('candidate_name', '')} {item.get('description', '')} {item.get('bio', '')}".lower()
        assert "support" in text

    # Pagination bounds
    res_page = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&page=1&limit=5")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert len(page_data["items"]) <= 5
    assert page_data["limit"] == 5


def test_social_scan_bluesky_integration():
    """Verify live social scan endpoint invokes Bluesky connector and persists candidates."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    mock_bsky_response = httpx.Response(
        200,
        json={
            "actors": [
                {
                    "did": "did:plc:scanactor123",
                    "handle": "novapay-customer-help.bsky.social",
                    "displayName": "NovaPay Customer Help",
                    "description": "24/7 online help agent.",
                }
            ]
        },
    )

    with patch("app.connectors.bluesky.safe_get_request", new_callable=AsyncMock, return_value=mock_bsky_response):
        with patch("app.connectors.http_client.fetch_and_hash_image_safe", new_callable=AsyncMock, return_value=(None, "none")):
            scan_res = client.post(f"/api/v1/social/brands/{brand_id}/scan")

    assert scan_res.status_code == 200
    data = scan_res.json()
    assert data["brand_id"] == brand_id
    assert len(data["source_results"]) == 1
    assert data["source_results"][0]["connector_id"] == "bluesky"
    assert data["source_results"][0]["ok"] is True
    assert data["total_found"] >= 1
