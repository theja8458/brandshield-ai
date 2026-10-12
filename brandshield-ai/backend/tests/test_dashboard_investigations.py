import pytest
from fastapi.testclient import TestClient

from app.crud.brand import seed_novapay
from app.database import ping_database
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def require_db():
    is_connected, _ = ping_database()
    if not is_connected:
        pytest.skip("MongoDB Atlas is not reachable for integration tests")


def test_dashboard_metrics_empty_state():
    """Verify dashboard metrics returns valid zero-count structure on empty database."""
    res = client.get("/api/v1/dashboard/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["monitored_brands_count"] == 0
    assert data["total_candidates_analyzed"] == 0
    assert data["candidates_by_type"]["social_profile"] == 0
    assert data["candidates_by_type"]["app_listing"] == 0
    assert data["active_threats_count"] == 0
    assert data["official_assets_excluded"] == 0
    assert data["identity_reviews_required"] == 0
    assert isinstance(data["active_threats_by_severity"], dict)
    assert data["active_threats_by_severity"]["Critical"] == 0
    assert data["investigation_status_distribution"]["new"] == 0
    assert len(data["metric_definitions"]) >= 5
    assert isinstance(data["connector_health"], dict)
    assert data["recent_detections"] == []


def test_dashboard_metrics_and_exclusions_reconciliation():
    """
    Verify dashboard metrics accurately reconcile with Atlas records,
    and official excluded assets are never included in active threat counts.
    """
    # 1. Seed brand NovaPay (comes with official social & app assets)
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # 2. Seed synthetic social candidates (includes 1 official excluded)
    soc_res = client.post(f"/api/v1/social/brands/{brand_id}/seed")
    assert soc_res.status_code == 200

    # 3. Seed synthetic app candidates (includes 1 official excluded)
    app_res = client.post(f"/api/v1/apps/brands/{brand_id}/seed")
    assert app_res.status_code == 200

    # 4. Fetch dashboard metrics
    metrics_res = client.get("/api/v1/dashboard/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()

    # Brand count
    assert metrics["monitored_brands_count"] >= 1

    # Candidates analyzed (25 social + 25 app = 50 from novapay_synthetic_dataset)
    assert metrics["total_candidates_analyzed"] == 50
    assert metrics["candidates_by_type"]["social_profile"] == 25
    assert metrics["candidates_by_type"]["app_listing"] == 25

    # Official excluded assets must be excluded from active threat counts
    assert metrics["official_assets_excluded"] >= 2
    assert metrics["active_threats_count"] <= 48
    assert metrics["active_threats_count"] > 0

    # Provenance
    assert metrics["provenance_breakdown"]["demo"] == 50

    # Recent detections should not contain OFFICIAL_EXCLUDED if threats exist
    recent_classifications = [r["classification"] for r in metrics["recent_detections"]]
    assert "OFFICIAL_EXCLUDED" not in recent_classifications


def test_investigations_unified_listing_and_filtering():
    """Verify unified investigation candidate listing, pagination, and multi-field filters."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    client.post(f"/api/v1/social/brands/{brand_id}/seed")
    client.post(f"/api/v1/apps/brands/{brand_id}/seed")

    # List all candidates (default excludes OFFICIAL_EXCLUDED)
    list_res = client.get("/api/v1/investigations/candidates")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["classification"] != "OFFICIAL_EXCLUDED"

    # With include_official=True
    list_all_res = client.get("/api/v1/investigations/candidates?include_official=true")
    assert list_all_res.status_code == 200
    all_data = list_all_res.json()
    assert all_data["total"] > data["total"]
    has_official = any(item["classification"] == "OFFICIAL_EXCLUDED" for item in all_data["items"])
    assert has_official is True

    # Filter by candidate_type
    app_only_res = client.get("/api/v1/investigations/candidates?candidate_type=app_listing")
    assert app_only_res.status_code == 200
    for item in app_only_res.json()["items"]:
        assert item["candidate_type"] == "app_listing"

    # Search filter
    search_res = client.get("/api/v1/investigations/candidates?search=Rewards")
    assert search_res.status_code == 200
    assert len(search_res.json()["items"]) >= 1


def test_investigation_status_workflow_and_audit_history():
    """
    Verify investigation status transitions, notes, and audit history trail.
    Ensures status transitions are preserved and risk scores are immutable.
    """
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    cand_res = client.post(
        "/api/v1/social/candidates",
        json={
            "brand_id": brand_id,
            "display_name": "NovaPay Support Fake",
            "handle": "novapay-support.bsky.social",
        },
    )
    assert cand_res.status_code == 201
    cand = cand_res.json()
    cand_id = cand["candidate_id"]
    original_score = cand["score"]
    assert cand["investigation_status"] == "new"

    # 1. Transition to INVESTIGATING
    update_1 = client.patch(
        f"/api/v1/investigations/candidates/{cand_id}/status",
        json={"status": "investigating", "notes": "Initial security triage started."},
    )
    assert update_1.status_code == 200
    u1_data = update_1.json()
    assert u1_data["investigation_status"] == "investigating"
    assert u1_data["status_notes"] == "Initial security triage started."
    assert u1_data["score"] == original_score  # Score remains unchanged!
    assert len(u1_data["investigation_history"]) == 1
    assert u1_data["investigation_history"][0]["status"] == "investigating"
    assert u1_data["investigation_history"][0]["notes"] == "Initial security triage started."

    # 2. Transition to RESOLVED
    update_2 = client.patch(
        f"/api/v1/investigations/candidates/{cand_id}/status",
        json={"status": "resolved", "notes": "Takedown notice issued to registrar."},
    )
    assert update_2.status_code == 200
    u2_data = update_2.json()
    assert u2_data["investigation_status"] == "resolved"
    assert u2_data["score"] == original_score
    assert len(u2_data["investigation_history"]) == 2
    assert u2_data["investigation_history"][1]["status"] == "resolved"
    assert u2_data["investigation_history"][1]["notes"] == "Takedown notice issued to registrar."


def test_evidence_trail_retrieval_and_details():
    """Verify /api/v1/evidence/{candidate_id} provides complete explainability and identifiers."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    cand_res = client.post(
        "/api/v1/social/candidates",
        json={
            "brand_id": brand_id,
            "display_name": "NovaPay Helpdesk",
            "handle": "novapay-help.bsky.social",
            "external_links": ["https://novapay-phish.net/login"],
        },
    )
    assert cand_res.status_code == 201
    cand_id = cand_res.json()["candidate_id"]

    # Retrieve evidence via /api/v1/evidence/{id}
    ev_res = client.get(f"/api/v1/evidence/{cand_id}")
    assert ev_res.status_code == 200
    ev = ev_res.json()

    assert ev["candidate_id"] == cand_id
    assert ev["brand_id"] == brand_id
    assert ev["source_type"] == "manual"
    assert ev["score"] > 0
    assert len(ev["signals"]) > 0
    assert isinstance(ev["external_identifiers"], dict)
    assert ev["external_identifiers"]["handle"] == "novapay-help.bsky.social"
    assert "collected_at" in ev
    assert "analyzed_at" in ev
    assert isinstance(ev["missing_evidence"], list)
    assert isinstance(ev["evidence_completeness"], float)

    # Test 404 for nonexistent candidate
    ev_404 = client.get("/api/v1/evidence/NONEXISTENT-ID-1234")
    assert ev_404.status_code == 404
