import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.official_guard import (
    ExclusionStatus,
    evaluate_official_status,
)
from app.services.image_hasher import compute_image_phash
from app.schemas.brand import BrandCreate


client = TestClient(app)


SAMPLE_BRAND = {
    "brand_id": "brand-novapay-test",
    "name": "NovaPay",
    "description": "Fictional digital payments brand",
    "official_website": "https://www.novapay.example",
    "official_domains": ["novapay.example"],
    "aliases": ["NovaPay Technologies"],
    "keywords": ["novapay", "wallet"],
    "safe_list": ["Nova Pay Careers"],
    "official_social_assets": [
        {
            "asset_id": "asset-soc-001",
            "platform": "bluesky",
            "display_name": "NovaPay Official",
            "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay.synthetic.example",
            "normalized_handle": "novapay.synthetic.example",
            "stable_account_id": "did:synthetic:novapay-official-0001",
        }
    ],
    "official_app_assets": [
        {
            "asset_id": "asset-app-001",
            "store": "apple_app_store",
            "app_name": "NovaPay Wallet",
            "canonical_listing_url": "https://appstore.synthetic.example/app/novapay-wallet/id9000000001",
            "package_or_bundle_id": "example.synthetic.novapay.wallet",
            "trusted_publisher_name": "NovaPay Technologies Ltd",
            "trusted_publisher_id": "synthetic-dev-10001",
        }
    ],
}


def test_exact_registered_social_asset_is_excluded():
    """Verify that candidate matching registered social handle and URL returns OFFICIAL_EXCLUDED."""
    candidate = {
        "candidate_type": "social_profile",
        "platform": "bluesky",
        "handle": "@novapay.synthetic.example",
        "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay.synthetic.example",
        "stable_account_id": "did:synthetic:novapay-official-0001",
    }
    result = evaluate_official_status(SAMPLE_BRAND, candidate)
    assert result.status == ExclusionStatus.OFFICIAL_EXCLUDED
    assert result.is_excluded_from_scoring is True
    assert "Matched registered official social" in result.reason


def test_exact_registered_app_bundle_id_is_excluded():
    """Verify that candidate app matching registered bundle ID and publisher returns OFFICIAL_EXCLUDED."""
    candidate = {
        "candidate_type": "app_listing",
        "store": "apple_app_store",
        "package_or_bundle_id": "example.synthetic.novapay.wallet",
        "publisher_id": "synthetic-dev-10001",
        "publisher_or_developer": "NovaPay Technologies Ltd",
    }
    result = evaluate_official_status(SAMPLE_BRAND, candidate)
    assert result.status == ExclusionStatus.OFFICIAL_EXCLUDED
    assert result.is_excluded_from_scoring is True
    assert "Matched registered official app" in result.reason


def test_similar_unregistered_asset_is_not_marked_official():
    """Verify that similar names or lookalikes NEVER get marked as official."""
    # Lookalike handle
    cand_social = {
        "candidate_type": "social_profile",
        "platform": "bluesky",
        "handle": "novapay-support.synthetic.example",
        "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay-support",
        "display_name": "NovaPay Official Support",
    }
    res_social = evaluate_official_status(SAMPLE_BRAND, cand_social)
    assert res_social.status == ExclusionStatus.NOT_OFFICIAL
    assert res_social.is_excluded_from_scoring is False

    # Lookalike app with different bundle ID
    cand_app = {
        "candidate_type": "app_listing",
        "store": "apple_app_store",
        "app_name": "NovaPay Online Wallet",
        "package_or_bundle_id": "com.imposter.novapay.wallet",
        "publisher_or_developer": "NovaPay Technologies Ltd",  # Claimed similar publisher name
    }
    res_app = evaluate_official_status(SAMPLE_BRAND, cand_app)
    assert res_app.status == ExclusionStatus.NOT_OFFICIAL
    assert res_app.is_excluded_from_scoring is False


def test_conflicting_social_identifier_requires_review():
    """Verify that conflicting stable account ID vs handle produces REVIEW_REQUIRED."""
    candidate = {
        "candidate_type": "social_profile",
        "platform": "bluesky",
        "handle": "fake_imposter_handle",
        "stable_account_id": "did:synthetic:novapay-official-0001",  # Same stable ID as official
    }
    result = evaluate_official_status(SAMPLE_BRAND, candidate)
    assert result.status == ExclusionStatus.REVIEW_REQUIRED
    assert result.is_excluded_from_scoring is False
    assert "IDENTITY_CONFLICT" in result.reason


def test_conflicting_app_publisher_requires_review():
    """Verify that official package ID with differing publisher ID produces REVIEW_REQUIRED."""
    candidate = {
        "candidate_type": "app_listing",
        "store": "apple_app_store",
        "package_or_bundle_id": "example.synthetic.novapay.wallet",  # Official bundle ID
        "publisher_id": "unknown-rogue-developer-9999",  # Conflicting developer ID
    }
    result = evaluate_official_status(SAMPLE_BRAND, candidate)
    assert result.status == ExclusionStatus.REVIEW_REQUIRED
    assert result.is_excluded_from_scoring is False
    assert "IDENTITY_CONFLICT" in result.reason


def test_safe_list_variant_is_excluded():
    """Verify that registered safe_list name (e.g. careers) returns SAFE_LISTED."""
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "Nova Pay Careers",
        "handle": "novapay_careers",
    }
    result = evaluate_official_status(SAMPLE_BRAND, candidate)
    assert result.status == ExclusionStatus.SAFE_LISTED
    assert result.is_excluded_from_scoring is True


def test_duplicate_asset_registration_rejected():
    """Verify that Pydantic validation rejects duplicate assets within the same brand."""
    with pytest.raises(ValueError, match="Duplicate official social asset"):
        BrandCreate(
            name="Test Duplicate Brand",
            description="Brand testing duplicates",
            official_website="https://testbrand.example",
            official_social_assets=[
                {
                    "platform": "bluesky",
                    "display_name": "First",
                    "canonical_profile_url": "https://bsky.app/profile/test",
                    "normalized_handle": "test_handle",
                },
                {
                    "platform": "bluesky",
                    "display_name": "Second Duplicate",
                    "canonical_profile_url": "https://bsky.app/profile/test",
                    "normalized_handle": "test_handle",
                },
            ],
        )


def test_invalid_domain_and_url_rejected():
    """Verify that invalid domains or URLs are rejected by validation."""
    with pytest.raises(ValueError, match="Invalid domain format"):
        BrandCreate(
            name="Invalid Domain Brand",
            description="Test",
            official_website="https://valid.example",
            official_domains=["not_a_valid_domain_!@#"],
        )

    with pytest.raises(ValueError, match="must start with http"):
        BrandCreate(
            name="Invalid Website Brand",
            description="Test",
            official_website="invalid-url-without-protocol",
        )


def test_brand_persistence_and_retrieval_in_atlas():
    """Verify brand creation, persistence in test database, retrieval, and deletion."""
    create_payload = {
        "name": "ApexPay Test",
        "description": "Enterprise digital banking service",
        "official_website": "https://www.apexpay.example",
        "official_domains": ["apexpay.example"],
        "aliases": ["ApexPay Global"],
        "keywords": ["apex", "pay"],
        "safe_list": ["ApexPay Support"],
        "official_social_assets": [
            {
                "platform": "x",
                "display_name": "ApexPay",
                "canonical_profile_url": "https://x.com/apexpay",
                "normalized_handle": "apexpay",
            }
        ],
    }

    # 1. Create brand
    res_create = client.post("/api/v1/brands", json=create_payload)
    assert res_create.status_code == 201
    created_data = res_create.json()
    brand_id = created_data["brand_id"]
    assert created_data["name"] == "ApexPay Test"

    # 2. Retrieve brand
    res_get = client.get(f"/api/v1/brands/{brand_id}")
    assert res_get.status_code == 200
    assert res_get.json()["brand_id"] == brand_id

    # 3. Test official evaluation endpoint
    eval_payload = {
        "candidate_type": "social_profile",
        "platform": "x",
        "handle": "@apexpay",
        "canonical_profile_url": "https://x.com/apexpay",
    }
    res_eval = client.post(f"/api/v1/brands/{brand_id}/evaluate-asset", json=eval_payload)
    assert res_eval.status_code == 200
    assert res_eval.json()["status"] == "OFFICIAL_EXCLUDED"

    # 4. Delete brand
    res_del = client.delete(f"/api/v1/brands/{brand_id}")
    assert res_del.status_code == 204


def test_novapay_seed_endpoint():
    """Verify that POST /api/v1/brands/seed/novapay creates/updates NovaPay repeatable seed."""
    res = client.post("/api/v1/brands/seed/novapay")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "NovaPay"
    assert data["is_synthetic"] is True
    assert len(data["official_domains"]) > 0
    assert len(data["official_social_assets"]) > 0
    assert len(data["official_app_assets"]) > 0


def test_logo_phash_upload():
    """Verify that logo image upload computes pHash and saves to brand."""
    # Seed NovaPay first
    client.post("/api/v1/brands/seed/novapay")

    # Generate a small in-memory 100x100 PNG
    img = Image.new("RGB", (100, 100), color=(100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    res = client.post(
        "/api/v1/brands/brand-novapay-synthetic/logo",
        files={"file": ("logo.png", buf.getvalue(), "image/png")},
    )
    assert res.status_code == 200
    brand_data = res.json()
    assert brand_data["official_logo"] is not None
    assert len(brand_data["official_logo"]["image_hash"]) == 16  # 64-bit hex hash


def test_official_domain_exclusion_and_lookalike_rejection():
    """Verify that exact official domain is excluded, while lookalike domain is NOT excluded."""
    # Exact registered domain
    res_exact = evaluate_official_status(SAMPLE_BRAND, {"candidate_type": "domain", "domain": "novapay.example"})
    assert res_exact.status == ExclusionStatus.OFFICIAL_EXCLUDED
    assert res_exact.is_excluded_from_scoring is True

    # Lookalike domain
    res_lookalike = evaluate_official_status(SAMPLE_BRAND, {"candidate_type": "domain", "domain": "novapay.example.phishing-test.xyz"})
    assert res_lookalike.status == ExclusionStatus.NOT_OFFICIAL
    assert res_lookalike.is_excluded_from_scoring is False
