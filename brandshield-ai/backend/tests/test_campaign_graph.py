import pytest
from fastapi.testclient import TestClient

from app.campaigns.config import (
    GENERIC_EXCLUDED_DOMAINS,
    INDICATOR_EXACT_DOMAIN,
    INDICATOR_PUBLISHER_ID,
    INDICATOR_PERCEPTUAL_HASH,
    INDICATOR_CONTACT_EMAIL,
    INDICATOR_CONTACT_PHONE,
)
from app.campaigns.graph_builder import build_campaign_graph
from app.crud.brand import seed_novapay
from app.database import ping_database
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def require_db():
    is_connected, _ = ping_database()
    if not is_connected:
        pytest.skip("MongoDB Atlas is not reachable for integration tests")


def test_empty_campaign_graph():
    """Verify campaign graph returns clean empty structure when no candidates exist."""
    res = client.get("/api/v1/campaigns/graph")
    assert res.status_code == 200
    data = res.json()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["groups"] == []
    assert data["unconnected_candidate_ids"] == []
    assert "POTENTIAL_COORDINATION" in data["disclaimer"]


def test_no_edges_from_name_similarity_alone():
    """
    CRITICAL RULE:
    Two candidates with similar names or look-alike names must NEVER produce a campaign edge
    unless they share a concrete, qualifying technical indicator.
    """
    brand = {
        "brand_id": "test-brand-1",
        "name": "NovaPay",
        "official_website": "https://novapay.com",
        "official_domains": ["novapay.com"],
    }
    candidates = [
        {
            "candidate_id": "CAND-NAME-1",
            "candidate_name": "NovaPay Official Support",
            "candidate_type": "social_profile",
            "platform": "bluesky",
            "handle": "novapay-support.bsky.social",
            "external_links": ["https://independent-host-1.net"],
            "score": 45,
            "severity": "Medium",
            "classification": "POTENTIAL_THREAT",
        },
        {
            "candidate_id": "CAND-NAME-2",
            "candidate_name": "NovaPay Official Helpdesk",
            "candidate_type": "social_profile",
            "platform": "bluesky",
            "handle": "novapay-helpdesk.bsky.social",
            "external_links": ["https://completely-different-host-2.org"],
            "score": 45,
            "severity": "Medium",
            "classification": "POTENTIAL_THREAT",
        },
    ]

    graph = build_campaign_graph(candidates, brand=brand)
    assert len(graph.nodes) == 2
    # Zero edges because they share no concrete technical indicator!
    assert len(graph.edges) == 0
    assert len(graph.groups) == 0
    assert len(graph.unconnected_candidate_ids) == 2


def test_generic_domains_excluded_from_creating_edges():
    """
    Verify common hosting, link shorteners, and link aggregators (e.g. linkhub.example, bit.ly)
    are strictly excluded and documented in non_edges_documented, never linking candidates.
    """
    brand = {
        "brand_id": "test-brand-generic",
        "name": "NovaPay",
        "official_website": "https://novapay.com",
    }
    candidates = [
        {
            "candidate_id": "CAND-GENERIC-1",
            "candidate_name": "NovaPay Promo 1",
            "candidate_type": "social_profile",
            "platform": "bluesky",
            "external_links": ["https://linkhub.example/user1"],
            "score": 40,
            "severity": "Medium",
            "classification": "POTENTIAL_THREAT",
        },
        {
            "candidate_id": "CAND-GENERIC-2",
            "candidate_name": "NovaPay Promo 2",
            "candidate_type": "social_profile",
            "platform": "bluesky",
            "external_links": ["https://linkhub.example/user2"],
            "score": 40,
            "severity": "Medium",
            "classification": "POTENTIAL_THREAT",
        },
    ]

    graph = build_campaign_graph(candidates, brand=brand)
    assert len(graph.edges) == 0
    assert len(graph.groups) == 0
    assert "linkhub.example" in graph.non_edges_documented.generic_domains_excluded
    assert "CAND-GENERIC-1" in graph.non_edges_documented.generic_domains_excluded["linkhub.example"]
    assert "CAND-GENERIC-2" in graph.non_edges_documented.generic_domains_excluded["linkhub.example"]


def test_official_asset_excluded_from_campaign_graph_by_default():
    """
    Verify official assets (OFFICIAL_EXCLUDED) are excluded by default from suspicious campaign graph.
    """
    brand = {
        "brand_id": "test-brand-off",
        "name": "NovaPay",
        "official_website": "https://novapay.com",
        "official_domains": ["novapay.com"],
    }
    candidates = [
        {
            "candidate_id": "CAND-OFFICIAL",
            "candidate_name": "NovaPay Official Verified",
            "candidate_type": "social_profile",
            "classification": "OFFICIAL_EXCLUDED",
            "score": 0,
            "severity": "Low",
            "external_links": ["https://shared-phish.net"],
        },
        {
            "candidate_id": "CAND-ROGUE",
            "candidate_name": "NovaPay Impersonator",
            "candidate_type": "social_profile",
            "classification": "POTENTIAL_THREAT",
            "score": 75,
            "severity": "High",
            "external_links": ["https://shared-phish.net"],
        },
    ]

    # By default, include_official=False
    graph = build_campaign_graph(candidates, brand=brand, include_official=False)
    node_ids = [n.id for n in graph.nodes]
    assert "CAND-OFFICIAL" not in node_ids
    assert "CAND-ROGUE" in node_ids
    # An official asset cannot be linked in a suspicious campaign graph
    assert len(graph.edges) == 0


def test_valid_shared_indicator_edges_and_grouping():
    """
    Verify qualifying shared indicators create edges with complete evidence:
    - Shared exact domain across social and app
    - Shared developer ID across apps
    - Shared contact phone across social
    """
    brand = {
        "brand_id": "test-brand-links",
        "name": "NovaPay",
        "official_website": "https://novapay.com",
        "official_domains": ["novapay.com"],
        "official_app_assets": [{"trusted_publisher_id": "trusted-pub-001"}],
    }
    candidates = [
        {
            "candidate_id": "CAND-SOC-1",
            "candidate_name": "NovaPay Rewards Social",
            "candidate_type": "social_profile",
            "platform": "bluesky",
            "external_links": ["https://novapay-phish-rewards.net/claim"],
            "score": 75,
            "severity": "High",
            "classification": "POTENTIAL_THREAT",
            "source_type": "demo",
        },
        {
            "candidate_id": "CAND-APP-1",
            "candidate_name": "NovaPay Rewards Mobile",
            "candidate_type": "app_listing",
            "platform": "apple_app_store",
            "external_links": ["https://novapay-phish-rewards.net/app"],
            "publisher_id": "rogue-dev-888",
            "score": 85,
            "severity": "Critical",
            "classification": "POTENTIAL_THREAT",
            "source_type": "demo",
        },
        {
            "candidate_id": "CAND-APP-2",
            "candidate_name": "NovaPay Token Wallet",
            "candidate_type": "app_listing",
            "platform": "apple_app_store",
            "publisher_id": "rogue-dev-888",
            "score": 60,
            "severity": "Medium",
            "classification": "POTENTIAL_THREAT",
            "source_type": "demo",
        },
        {
            "candidate_id": "CAND-UNRELATED",
            "candidate_name": "NovaPay Unrelated Query",
            "candidate_type": "social_profile",
            "platform": "bluesky",
            "external_links": ["https://some-isolated-site.org"],
            "score": 35,
            "severity": "Low",
            "classification": "LOW_RISK",
            "source_type": "demo",
        },
    ]

    graph = build_campaign_graph(candidates, brand=brand)

    # 4 candidates evaluated, 3 should be connected into a campaign group, 1 unconnected
    assert len(graph.nodes) == 4
    assert "CAND-UNRELATED" in graph.unconnected_candidate_ids

    # Edges should exist
    assert len(graph.edges) >= 2
    # Verify edge details and ethics disclaimer
    domain_edges = [e for e in graph.edges if e.indicator_type == INDICATOR_EXACT_DOMAIN]
    assert len(domain_edges) == 1
    assert domain_edges[0].matched_value == "novapay-phish-rewards.net"
    assert "does not prove common ownership" in domain_edges[0].explanation

    pub_edges = [e for e in graph.edges if e.indicator_type == INDICATOR_PUBLISHER_ID]
    assert len(pub_edges) == 1
    assert pub_edges[0].matched_value == "rogue-dev-888"

    # Groups verification
    assert len(graph.groups) == 1
    cg = graph.groups[0]
    assert cg.label == "POTENTIAL_COORDINATION"
    assert cg.group_size == 3
    assert set(cg.member_candidate_ids) == {"CAND-SOC-1", "CAND-APP-1", "CAND-APP-2"}
    assert cg.highest_risk == 85
    assert cg.highest_severity == "Critical"
    assert set(cg.candidate_types) == {"social_profile", "app_listing"}


def test_review_required_candidate_transparent_handling():
    """Verify REVIEW_REQUIRED candidates can be nodes with distinct classification preserved."""
    brand = {
        "brand_id": "test-brand-rr",
        "name": "NovaPay",
        "official_website": "https://novapay.com",
    }
    candidates = [
        {
            "candidate_id": "CAND-RR-1",
            "candidate_name": "NovaPay Identity Conflict",
            "candidate_type": "social_profile",
            "classification": "REVIEW_REQUIRED",
            "severity": "Review Required",
            "score": 50,
            "external_links": ["https://suspicious-conflict-link.org"],
        },
        {
            "candidate_id": "CAND-RR-2",
            "candidate_name": "NovaPay Second Account",
            "candidate_type": "social_profile",
            "classification": "POTENTIAL_THREAT",
            "severity": "High",
            "score": 70,
            "external_links": ["https://suspicious-conflict-link.org"],
        },
    ]

    graph = build_campaign_graph(candidates, brand=brand)
    rr_node = next((n for n in graph.nodes if n.id == "CAND-RR-1"), None)
    assert rr_node is not None
    assert rr_node.classification == "REVIEW_REQUIRED"
    assert len(graph.groups) == 1


def test_novapay_synthetic_campaign_seed_and_api():
    """
    Test live API endpoint /api/v1/campaigns/seed/novapay and /api/v1/campaigns/graph.
    Verifies that the synthetic dataset produces expected groups (e.g. publisher-linked and domain-linked).
    """
    # 1. Trigger synthetic seed
    res = client.post("/api/v1/campaigns/seed/novapay")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    brand_id = data["brand_id"]
    assert data["campaign_groups_detected"] >= 3

    # 2. Query full graph API
    graph_res = client.get(f"/api/v1/campaigns/graph?brand_id={brand_id}")
    assert graph_res.status_code == 200
    graph = graph_res.json()

    assert graph["is_synthetic"] is True
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
    assert len(graph["groups"]) >= 3
    assert len(graph["unconnected_candidate_ids"]) > 0

    # Verify edge disclaimer
    for edge in graph["edges"]:
        assert "does not prove common ownership" in edge["explanation"]
        assert edge["indicator_type"] in [
            INDICATOR_EXACT_DOMAIN,
            INDICATOR_PUBLISHER_ID,
            INDICATOR_PERCEPTUAL_HASH,
            INDICATOR_CONTACT_EMAIL,
            INDICATOR_CONTACT_PHONE,
        ]

    # Verify group endpoint
    groups_res = client.get(f"/api/v1/campaigns/groups?brand_id={brand_id}")
    assert groups_res.status_code == 200
    groups_list = groups_res.json()
    assert len(groups_list) == len(graph["groups"])

    # Verify single group endpoint
    first_group_id = groups_list[0]["group_id"]
    single_res = client.get(f"/api/v1/campaigns/groups/{first_group_id}?brand_id={brand_id}")
    assert single_res.status_code == 200
    assert single_res.json()["group_id"] == first_group_id
