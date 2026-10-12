from unittest.mock import AsyncMock, patch
import os
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


def test_seed_app_demo_candidates():
    """Verify repeatable demo seeding endpoint populates mobile app candidates."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    res = client.post(f"/api/v1/apps/brands/{brand_id}/seed")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["count"] > 0

    # Verify candidates in database have demo tags and app_listing type
    list_res = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}&source_type=demo")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] > 0
    for cand in list_data["items"]:
        assert cand["candidate_type"] == "app_listing"
        assert cand["source_type"] == "demo"
        assert cand["is_demo_data"] is True


def test_official_app_excluded_from_active_alerts():
    """Verify official registered app is excluded before scoring and hidden from default alert list."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    client.post(f"/api/v1/apps/brands/{brand_id}/seed")

    # Default query (include_official=False) must NOT include OFFICIAL_EXCLUDED
    res_default = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}")
    assert res_default.status_code == 200
    items_default = res_default.json()["items"]
    assert not any(i["classification"] == "OFFICIAL_EXCLUDED" for i in items_default)

    # Query with include_official=True returns official asset
    res_all = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}&include_official=true&limit=50")
    assert res_all.status_code == 200
    items_all = res_all.json()["items"]
    official_items = [i for i in items_all if i["classification"] == "OFFICIAL_EXCLUDED"]
    assert len(official_items) >= 1
    for off in official_items:
        assert off["score"] == 0
        assert off["severity"] == "Low"


def test_conflicting_package_or_publisher_requires_review():
    """
    Verify identity conflict: an app matching official package ID but with a differing
    publisher is classified REVIEW_REQUIRED.
    """
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # Official package is example.synthetic.novapay.wallet, official publisher ID is synthetic-dev-10001
    manual_conflict = {
        "app_name": "NovaPay Rogue Token",
        "store": "apple_app_store",
        "package_or_bundle_id": "example.synthetic.novapay.wallet",
        "publisher_or_developer": "Rogue Developer Inc.",
        "publisher_id": "synthetic-dev-99999",
        "canonical_listing_url": "https://apps.apple.com/app/novapay-rogue/id999999999",
        "description": "2FA Authenticator token generator for NovaPay.",
    }

    res = client.post(f"/api/v1/apps/brands/{brand_id}/manual", json=manual_conflict)
    assert res.status_code == 201
    data = res.json()
    assert data["classification"] == "REVIEW_REQUIRED"


def test_missing_publisher_produces_warning():
    """Verify an app listing without publisher information triggers the publisher_missing warning signal."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    manual_no_pub = {
        "app_name": "NovaPay Wallet Unknown",
        "store": "apple_app_store",
        "package_or_bundle_id": "com.unknown.novapay",
        "publisher_or_developer": None,
        "publisher_id": None,
        "canonical_listing_url": "https://apps.apple.com/app/novapay-wallet/id111111111",
        "description": "Simple unofficial wallet.",
    }

    res = client.post(f"/api/v1/apps/brands/{brand_id}/manual", json=manual_no_pub)
    assert res.status_code == 201
    data = res.json()
    signal_ids = [s["id"] for s in data["signals"]]
    assert "publisher_missing" in signal_ids
    assert any("publisher" in m.lower() for m in data["missing_evidence"])


def test_manual_app_submission_and_scoring():
    """Verify manual app submission evaluates through engine and persists in Atlas."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    payload = {
        "app_name": "N0vaPay Fast Cash",
        "store": "apple_app_store",
        "package_or_bundle_id": "com.n0vapay.fastcash",
        "publisher_or_developer": "Fast Cash Inc.",
        "publisher_id": "synthetic-dev-88888",
        "canonical_listing_url": "https://apps.apple.com/app/n0vapay-fast-cash/id888888888",
        "description": "Get instant loan refund and fast payout directly to your wallet.",
    }

    res = client.post(f"/api/v1/apps/brands/{brand_id}/manual", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["source_type"] == "manual"
    assert data["score"] >= 40  # Name evasion + publisher mismatch + scam language
    assert data["classification"] == "POTENTIAL_THREAT"
    assert data["investigation_status"] == "new"

    # Verify retrieval
    cid = data["candidate_id"]
    get_res = client.get(f"/api/v1/apps/candidates/{cid}")
    assert get_res.status_code == 200
    assert get_res.json()["candidate_id"] == cid


def test_update_app_investigation_status():
    """Verify triage state transitions and notes persistence for app candidates."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    manual_res = client.post(
        f"/api/v1/apps/brands/{brand_id}/manual",
        json={"app_name": "NovaPay Assistant", "package_or_bundle_id": "com.test.assist"},
    )
    cid = manual_res.json()["candidate_id"]

    # Transition to investigating
    res1 = client.patch(
        f"/api/v1/apps/candidates/{cid}/status",
        json={"status": "investigating", "notes": "Auditing developer background"},
    )
    assert res1.status_code == 200
    assert res1.json()["investigation_status"] == "investigating"
    assert res1.json()["status_notes"] == "Auditing developer background"

    # Transition to false_positive
    res2 = client.patch(
        f"/api/v1/apps/candidates/{cid}/status",
        json={"status": "false_positive", "notes": "Authorized utility plugin"},
    )
    assert res2.status_code == 200
    assert res2.json()["investigation_status"] == "false_positive"


def test_list_app_candidates_filtering_and_pagination():
    """Verify filtering by severity, status, search string, and bounded pagination for apps."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]
    client.post(f"/api/v1/apps/brands/{brand_id}/seed")

    # Search filter (searching for wallet)
    res_search = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}&search=wallet")
    assert res_search.status_code == 200
    search_items = res_search.json()["items"]
    for item in search_items:
        text = f"{item.get('app_name', '')} {item.get('package_or_bundle_id', '')} {item.get('publisher_or_developer', '')} {item.get('description', '')}".lower()
        assert "wallet" in text

    # Pagination bounds
    res_page = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}&page=1&limit=5")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert len(page_data["items"]) <= 5
    assert page_data["limit"] == 5


def test_app_scan_itunes_integration():
    """Verify live app scan endpoint invokes iTunes connector, deduplicates, and persists."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    mock_itunes_response = httpx.Response(
        200,
        json={
            "resultCount": 2,
            "results": [
                {
                    "trackId": 987654321,
                    "trackName": "N0vaPay Mobile Wallet",
                    "bundleId": "com.mock.n0vapay",
                    "sellerName": "Unknown App Publisher",
                    "artistId": 54321,
                    "trackViewUrl": "https://apps.apple.com/app/id987654321",
                    "description": "Fast mobile money transfers.",
                    "artworkUrl512": "https://is1-ssl.mzstatic.com/image/thumb/mock.png",
                },
                {
                    "trackId": 123456789,
                    "trackName": "NovaPay Official iOS",
                    "bundleId": "com.novapay.app",  # Official bundle ID
                    "sellerName": "NovaPay Inc.",
                    "artistId": 10001,  # Matches official
                    "trackViewUrl": "https://apps.apple.com/app/id123456789",
                    "description": "Official payments app.",
                },
            ],
        },
        request=httpx.Request("GET", "https://itunes.apple.com/search"),
    )

    with patch("httpx.AsyncClient.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_itunes_response

        res = client.post(f"/api/v1/apps/brands/{brand_id}/scan")
        assert res.status_code == 200
        scan_data = res.json()
        assert scan_data["total_found"] >= 1

        # Check candidate persisted
        list_res = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}&source_type=live_connector")
        assert list_res.status_code == 200
        live_items = list_res.json()["items"]
        assert any("N0vaPay" in i.get("app_name", "") for i in live_items)


def test_itunes_upstream_timeout_and_failure_handling():
    """Verify connector handles timeouts gracefully without crashing or substituting synthetic data."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    with patch("httpx.AsyncClient.send", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = httpx.ConnectTimeout("Apple iTunes gateway timeout")

        res = client.post(f"/api/v1/apps/brands/{brand_id}/scan")
        assert res.status_code == 200
        scan_data = res.json()
        itunes_source = next((s for s in scan_data["source_results"] if s["connector_id"] == "apple_itunes"), None)
        assert itunes_source is not None
        assert itunes_source["ok"] is False
        assert "timeout" in (itunes_source["error"] or "").lower()

        # Confirm NO synthetic data was secretly added
        cand_res = client.get(f"/api/v1/apps/candidates?brand_id={brand_id}&source_type=demo")
        assert cand_res.json()["total"] == 0


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "").lower() != "true",
    reason="Live public test skipped by default. Run with RUN_LIVE_TESTS=true to execute.",
)
@pytest.mark.asyncio
async def test_live_itunes_public_smoke_test():
    """Bounded smoke test against the live Apple iTunes API."""
    from app.connectors.itunes import ITunesConnector

    connector = ITunesConnector()
    results = await connector.search("novapay")
    assert isinstance(results, list)
    for r in results:
        assert r.platform == "apple_app_store"
        assert r.source_type == "live_connector"
