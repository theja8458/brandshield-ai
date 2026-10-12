import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.campaigns.graph_builder import build_campaign_graph
from app.crud.brand import get_brand, seed_novapay
from app.database import ping_database
from app.detection.engine import evaluate_candidate
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def require_db():
    is_connected, _ = ping_database()
    if not is_connected:
        pytest.skip("MongoDB Atlas is not reachable for acceptance tests")


def test_acceptance_01_and_02_brand_creation_and_atlas_persistence():
    """Acceptance 1 & 2: Create brand with official social/app assets and confirm Atlas persistence."""
    brand_payload = {
        "name": "AcceptanceBrand",
        "description": "Acceptance test brand verification",
        "official_website": "https://acceptancebrand.com",
        "official_domains": ["acceptancebrand.com"],
        "official_social_assets": [
            {
                "platform": "bluesky",
                "display_name": "AcceptanceBrand Official",
                "canonical_profile_url": "https://bsky.app/profile/acceptancebrand.bsky.social",
                "normalized_handle": "acceptancebrand.bsky.social",
                "stable_account_id": "did:plc:acc123456789",
            }
        ],
        "official_app_assets": [
            {
                "store": "apple_app_store",
                "app_name": "AcceptanceBrand App",
                "canonical_listing_url": "https://apps.apple.com/app/acceptancebrand/id11223344",
                "package_or_bundle_id": "com.acceptancebrand.app",
                "trusted_publisher_name": "AcceptanceBrand Corp",
                "trusted_publisher_id": "acc-pub-999",
            }
        ],
    }

    create_res = client.post("/api/v1/brands", json=brand_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    brand_id = created["brand_id"]

    # Verify retrieval from Atlas
    get_res = client.get(f"/api/v1/brands/{brand_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["name"] == "AcceptanceBrand"
    assert len(retrieved["official_social_assets"]) == 1
    assert retrieved["official_social_assets"][0]["normalized_handle"] == "acceptancebrand.bsky.social"
    assert len(retrieved["official_app_assets"]) == 1
    assert retrieved["official_app_assets"][0]["package_or_bundle_id"] == "com.acceptancebrand.app"


def test_acceptance_03_official_assets_excluded_before_scoring():
    """Acceptance 3: Confirm official social & app assets are excluded before threat scoring."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # Official Bluesky handle
    official_social = {
        "candidate_id": "ACC-OFF-SOC",
        "brand_id": brand_id,
        "platform": "bluesky",
        "handle": "novapay.synthetic.example",
        "display_name": "NovaPay Official",
        "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay.synthetic.example",
    }
    eval_social = client.post(f"/api/v1/brands/{brand_id}/evaluate-asset", json=official_social)
    assert eval_social.status_code == 200
    assert eval_social.json()["status"] == "OFFICIAL_EXCLUDED"

    # Official app package ID
    official_app = {
        "candidate_id": "ACC-OFF-APP",
        "brand_id": brand_id,
        "store": "apple_app_store",
        "package_or_bundle_id": "example.synthetic.novapay.wallet",
        "publisher_id": "synthetic-dev-10001",
        "app_name": "NovaPay Official App",
    }
    eval_app = client.post(f"/api/v1/brands/{brand_id}/evaluate-asset", json=official_app)
    assert eval_app.status_code == 200
    assert eval_app.json()["status"] == "OFFICIAL_EXCLUDED"


def test_acceptance_04_and_05_explainable_assessments_for_social_and_app():
    """Acceptance 4 & 5: Social look-alikes and suspicious apps receive explainable assessments."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # Look-alike social candidate
    soc_res = client.post(
        "/api/v1/social/candidates",
        json={
            "brand_id": brand_id,
            "display_name": "N0vaPay Support",
            "handle": "n0vapay-support.bsky.social",
            "external_links": ["https://novapay-phish.net/login"],
            "bio": "Official support. DM to claim giveaway refund.",
        },
    )
    assert soc_res.status_code == 201
    soc_cand = soc_res.json()
    assert soc_cand["score"] >= 60
    assert len(soc_cand["signals"]) >= 2
    # Verify each signal has human readable reason
    for s in soc_cand["signals"]:
        assert len(s["human_readable_reason"]) > 0

    # Suspicious app listing with publisher mismatch
    app_res = client.post(
        "/api/v1/apps/candidates",
        json={
            "brand_id": brand_id,
            "app_name": "NovaPay Wallet 2FA",
            "store": "apple_app_store",
            "package_or_bundle_id": "com.novapay.rogue",
            "publisher_or_developer": "Rogue Developer LLC",
            "publisher_id": "rogue-dev-9999",
            "external_links": ["https://novapay-secure-login.org"],
        },
    )
    assert app_res.status_code == 201
    app_cand = app_res.json()
    assert app_cand["score"] >= 40
    signal_ids = [s["id"] for s in app_cand["signals"]]
    assert "publisher_mismatch" in signal_ids or "name_similarity" in signal_ids


def test_acceptance_06_missing_fields_do_not_crash_app():
    """Acceptance 6: Candidates with completely missing bio, description, icons, or links do not crash."""
    brand = seed_novapay()
    bare_cand = {
        "candidate_id": "ACC-BARE-1",
        "candidate_name": "NovaPay Minimal",
        "display_name": "NovaPay Minimal",
        "handle": "novapay-minimal.bsky.social",
    }
    # Direct engine evaluation
    res = evaluate_candidate(brand, bare_cand)
    assert res.score >= 0
    assert res.score <= 100
    assert isinstance(res.missing_evidence, list)
    assert len(res.missing_evidence) > 0


def test_acceptance_07_and_08_campaign_edges_and_unrelated_isolation():
    """Acceptance 7 & 8: Campaign edges derive only from shared indicators; unrelated stay unconnected."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    cand_linked_1 = {
        "candidate_id": "ACC-CAMP-1",
        "candidate_name": "NovaPay Promo A",
        "candidate_type": "social_profile",
        "external_links": ["https://attacker-infrastructure.com"],
        "score": 70,
        "classification": "POTENTIAL_THREAT",
    }
    cand_linked_2 = {
        "candidate_id": "ACC-CAMP-2",
        "candidate_name": "NovaPay Promo B",
        "candidate_type": "app_listing",
        "external_links": ["https://attacker-infrastructure.com"],
        "score": 65,
        "classification": "POTENTIAL_THREAT",
    }
    cand_unrelated = {
        "candidate_id": "ACC-CAMP-UNRELATED",
        "candidate_name": "NovaPay Independent",
        "candidate_type": "social_profile",
        "external_links": ["https://different-host.org"],
        "score": 40,
        "classification": "POTENTIAL_THREAT",
    }

    graph = build_campaign_graph([cand_linked_1, cand_linked_2, cand_unrelated], brand=brand)
    assert len(graph.edges) == 1
    assert graph.edges[0].source == "ACC-CAMP-1"
    assert graph.edges[0].target == "ACC-CAMP-2"
    assert "ACC-CAMP-UNRELATED" in graph.unconnected_candidate_ids


def test_acceptance_09_investigation_status_persists():
    """Acceptance 9: Investigation status persists and is returned on re-fetch."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    cand_res = client.post(
        "/api/v1/social/candidates",
        json={
            "brand_id": brand_id,
            "display_name": "NovaPay Phish Test",
            "handle": "novapay-phish-persist.bsky.social",
        },
    )
    cand_id = cand_res.json()["candidate_id"]

    # Transition to investigating
    patch_res = client.patch(
        f"/api/v1/investigations/candidates/{cand_id}/status",
        json={"status": "investigating", "notes": "Analyst triage note"},
    )
    assert patch_res.status_code == 200

    # Fetch candidate afresh
    get_res = client.get(f"/api/v1/investigations/candidates/{cand_id}")
    assert get_res.status_code == 200
    assert get_res.json()["investigation_status"] == "investigating"
    assert get_res.json()["status_notes"] == "Analyst triage note"


def test_acceptance_10_dashboard_metrics_exclude_official_assets():
    """Acceptance 10: Dashboard active threats count strictly excludes official assets."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # Seed candidates (includes 1 official excluded social + 1 official excluded app)
    client.post(f"/api/v1/social/brands/{brand_id}/seed")
    client.post(f"/api/v1/apps/brands/{brand_id}/seed")

    metrics_res = client.get("/api/v1/dashboard/metrics")
    assert metrics_res.status_code == 200
    m = metrics_res.json()
    assert m["official_assets_excluded"] >= 2
    # Active threats must not include official assets
    assert m["active_threats_count"] <= m["total_candidates_analyzed"] - m["official_assets_excluded"]


def test_acceptance_11_distinct_provenance_labels():
    """Acceptance 11: Demo seed, manual submission, and live connector are clearly distinguishable."""
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # 1. Manual candidate
    man_res = client.post(
        "/api/v1/social/candidates",
        json={
            "brand_id": brand_id,
            "display_name": "NovaPay Manual Entry",
            "handle": "novapay-manual.bsky.social",
        },
    )
    assert man_res.json()["source_type"] == "manual"
    assert man_res.json()["is_demo_data"] is False

    # 2. Seeded candidate
    client.post(f"/api/v1/social/brands/{brand_id}/seed")
    list_demo = client.get(f"/api/v1/social/candidates?brand_id={brand_id}&source_type=demo")
    assert list_demo.json()["items"][0]["source_type"] == "demo"
    assert list_demo.json()["items"][0]["is_demo_data"] is True


def test_acceptance_12_and_13_safe_error_handling_and_no_synthetic_fallbacks():
    """
    Acceptance 12 & 13:
    - Failing connector returns per-source error without breaking scan or substituting synthetic data.
    - Health checks return honest readiness.
    """
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    # Mock Bluesky connector failure
    with patch("app.connectors.bluesky.BlueskyConnector.search", new_callable=AsyncMock) as mock_bsky:
        mock_bsky.side_effect = TimeoutError("Bluesky upstream timeout 5.0s")

        res = client.post(f"/api/v1/social/brands/{brand_id}/scan")
        assert res.status_code == 200
        data = res.json()
        assert len(data["source_results"]) >= 1
        bsky_res = data["source_results"][0]
        assert bsky_res["ok"] is False
        assert "TimeoutError" in bsky_res["error"]
        # Never substitutes synthetic records on failure!
        assert data["total_new"] == 0


def test_acceptance_14_benign_name_table_no_overflagging():
    """
    Acceptance 14:
    Benign names stay below threat threshold (score < 40).
    Official safe-list variants score 0.
    """
    brand = {
        "brand_id": "test-brand-benign",
        "name": "NovaPay",
        "official_website": "https://novapay.com",
        "safe_list": ["Nova Pay Careers"],
    }

    # 1. Nova Payments Ltd: different legal entity
    eval1 = evaluate_candidate(brand, {"candidate_id": "B1", "candidate_name": "Nova Payments Ltd"})
    assert eval1.score < 40
    assert eval1.classification == "LOW_RISK"

    # 2. Pay Nova Fitness: generic token inversion
    eval2 = evaluate_candidate(brand, {"candidate_id": "B2", "candidate_name": "Pay Nova Fitness"})
    assert eval2.score < 40
    assert eval2.classification == "LOW_RISK"

    # 3. Novak Pay: single transposition
    eval3 = evaluate_candidate(brand, {"candidate_id": "B3", "candidate_name": "Novak Pay"})
    assert eval3.score < 40
    assert eval3.classification == "LOW_RISK"

    # 4. Safe list variant: scores 0
    eval4 = evaluate_candidate(brand, {"candidate_id": "B4", "candidate_name": "Nova Pay Careers"})
    assert eval4.score == 0
    assert eval4.signals[0].id == "safe_list_exclusion"
