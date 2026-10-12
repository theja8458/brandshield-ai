import pytest
from app.detection.config import (
    EVASION_BONUS_HOMOGLYPH_LEETSPEAK,
    NAME_FAMILY_CAP,
    POTENTIAL_THREAT_THRESHOLD,
    THRESHOLD_CRITICAL,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
)
from app.detection.engine import evaluate_candidate
from app.detection.normalizer import normalize_candidate_name


BRAND_NOVAPAY = {
    "brand_id": "brand-novapay-synthetic",
    "name": "NovaPay",
    "description": "NovaPay is a fictional digital wallet and peer-to-peer payments service used only for software testing.",
    "official_website": "https://www.novapay.example",
    "official_domains": ["novapay.example"],
    "aliases": ["NovaPay Technologies"],
    "keywords": ["novapay", "nova pay", "wallet", "peer-to-peer payments"],
    "safe_list": ["Nova Pay Careers"],
    "official_logo": {
        "image_reference": "image_fixtures/official_novapay_logo.png",
        "image_hash": "be6ce19394469639",
    },
    "official_social_assets": [
        {
            "asset_id": "asset-novapay-social-001",
            "platform": "bluesky",
            "display_name": "NovaPay",
            "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay.synthetic.example",
            "normalized_handle": "novapay.synthetic.example",
            "stable_account_id": "did:synthetic:novapay-official-0001",
        }
    ],
    "official_app_assets": [
        {
            "asset_id": "asset-novapay-app-001",
            "store": "apple_app_store",
            "app_name": "NovaPay Wallet",
            "canonical_listing_url": "https://appstore.synthetic.example/app/novapay-wallet/id9000000001",
            "package_or_bundle_id": "example.synthetic.novapay.wallet",
            "trusted_publisher_name": "NovaPay Technologies Ltd",
            "trusted_publisher_id": "synthetic-dev-10001",
            "icon_hash": "9ea4295bea4eea11",
        }
    ],
}


def test_normalization_order_and_homoglyphs():
    """Verify NFKC -> casefold -> homoglyph mapping -> compact form."""
    res = normalize_candidate_name("N0vaPay   Support", "NovaPay")
    assert res.has_homoglyph_or_leetspeak is True
    assert res.has_added_generic_words is True
    assert "support" in res.detected_generic_words
    assert res.core_compact == "novapay"
    assert res.compact_full == "novapaysupport"

    # Digraph mapping: 'rn' -> 'm'
    digraph_res = normalize_candidate_name("Novaparn", "NovaPay")
    assert digraph_res.compact_full == "novapam"


def test_deterministic_example_n0vapay_support():
    """
    Test: 'N0vaPay Support' -> normalized core name 'novapay',
    exact-name points 35 + homoglyph/evasion bonus +8, capped at 40.
    Must reach score >= 40 (Medium / POTENTIAL_THREAT).
    """
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "N0vaPay Support",
        "handle": "n0vapay_support",
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.score == 40
    assert result.severity == "Medium"
    assert result.classification == "POTENTIAL_THREAT"

    # Verify signals include both name_similarity and evasion_bonus
    signal_ids = [s.id for s in result.signals]
    assert "name_similarity" in signal_ids
    assert "evasion_bonus" in signal_ids


def test_deterministic_example_nova_pay_official():
    """
    Test: 'Nova Pay Official' -> normalized core name 'novapay',
    exact-name points 35 + added-word bonus +6, capped at 40.
    Largest bonus rule applies (takes +6 over spacing-only +3).
    """
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "Nova Pay Official",
        "handle": "nova_pay_official",
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.score == 40
    assert result.severity == "Medium"
    assert result.classification == "POTENTIAL_THREAT"


@pytest.mark.parametrize(
    "name,expected_max_score,description",
    [
        ("Nova Payments Ltd", 39, "Unrelated company; name similarity < 0.70"),
        ("Nova Pay Careers", 0, "Registered on brand safe_list; excluded from scoring"),
        ("Novak Pay", 39, "One transposition away; 20 points, stays below 40"),
        ("Pay Nova Fitness", 39, "Unrelated business; tokens do not match core brand"),
    ],
)
def test_benign_regression_cases_stay_below_40(name, expected_max_score, description):
    """
    REGRESSION MATRIX: Benign names must never be over-flagged and MUST stay below 40.
    """
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": name,
        "handle": name.lower().replace(" ", "_"),
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.score <= expected_max_score, f"Failed for '{name}': score {result.score} > {expected_max_score}"
    assert result.classification in ("LOW_RISK", "OFFICIAL_EXCLUDED", "SAFE_LISTED")


@pytest.mark.parametrize(
    "candidate,expected_min_score,expected_class",
    [
        (
            {"candidate_type": "social_profile", "candidate_name": "N0vaPay Support"},
            40,
            "POTENTIAL_THREAT",
        ),
        (
            {"candidate_type": "social_profile", "candidate_name": "Nova Pay Official"},
            40,
            "POTENTIAL_THREAT",
        ),
        (
            {
                "candidate_type": "social_profile",
                "candidate_name": "NovaPay",
                "external_links": ["https://novapay-login.example"],
            },
            60,  # 35 name + 25 lookalike domain
            "POTENTIAL_THREAT",
        ),
    ],
)
def test_malicious_regression_cases_flagged_at_least_40(candidate, expected_min_score, expected_class):
    """
    REGRESSION MATRIX: Suspicious look-alikes must be flagged (score >= 40).
    """
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.score >= expected_min_score
    assert result.classification == expected_class


def test_name_only_score_ceiling():
    """
    CRITICAL RULE:
    Name family is capped at 40 points.
    A candidate with ONLY name similarity (even exact match + multiple evasion patterns)
    can NEVER reach High (>= 70) or Critical (>= 85) severity.
    """
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "N0vaPay Official Support Help Care",
        "handle": "n0vapay_official_support",
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.score <= NAME_FAMILY_CAP
    assert result.score == 40
    assert result.severity == "Medium"  # Never High or Critical


def test_official_asset_excluded_before_scoring():
    """Verify official assets score 0 and return OFFICIAL_EXCLUDED."""
    candidate = {
        "candidate_type": "social_profile",
        "platform": "bluesky",
        "handle": "@novapay.synthetic.example",
        "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay.synthetic.example",
        "stable_account_id": "did:synthetic:novapay-official-0001",
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.score == 0
    assert result.classification == "OFFICIAL_EXCLUDED"


def test_identity_conflict_overrides_to_review_required():
    """Verify conflicting identifiers override classification to REVIEW_REQUIRED."""
    candidate = {
        "candidate_type": "app_listing",
        "store": "apple_app_store",
        "package_or_bundle_id": "example.synthetic.novapay.wallet",  # Official bundle ID
        "publisher_id": "conflicting-rogue-publisher-9999",         # Differing publisher ID
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    assert result.classification == "REVIEW_REQUIRED"
    assert "IDENTITY_CONFLICT" in result.reason


def test_exact_official_domain_scores_zero_risk():
    """Verify linking to exact official domain scores 0 (positive signal)."""
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "Some User",
        "external_links": ["https://www.novapay.example"],
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    domain_signals = [s for s in result.signals if s.family == "domain"]
    assert len(domain_signals) == 1
    assert domain_signals[0].points == 0
    assert "exact verified official domain" in domain_signals[0].human_readable_reason


def test_lookalike_domain_scores_25_points():
    """Verify lookalike domain scores 25 points."""
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "Unrelated User",
        "external_links": ["https://novapay-claim-refund.example"],
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    domain_signals = [s for s in result.signals if s.id == "lookalike_domain"]
    assert len(domain_signals) == 1
    assert domain_signals[0].points == 25


def test_publisher_mismatch_scores_20_points():
    """Verify publisher mismatch for app listing scores 20 points."""
    candidate = {
        "candidate_type": "app_listing",
        "store": "apple_app_store",
        "app_name": "Unrelated App",
        "package_or_bundle_id": "com.unrelated.app",
        "publisher_id": "synthetic-dev-99999",  # Differs from official synthetic-dev-10001
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    pub_signals = [s for s in result.signals if s.id == "publisher_mismatch"]
    assert len(pub_signals) == 1
    assert pub_signals[0].points == 20


def test_missing_publisher_scores_8_points_with_warning():
    """Verify missing publisher scores 8 points and records missing evidence warning."""
    candidate = {
        "candidate_type": "app_listing",
        "store": "apple_app_store",
        "app_name": "Unrelated App",
        "package_or_bundle_id": "com.unrelated.app",
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    pub_signals = [s for s in result.signals if s.id == "publisher_missing"]
    assert len(pub_signals) == 1
    assert pub_signals[0].points == 8
    assert any("missing" in w.lower() for w in result.missing_evidence)


def test_image_perceptual_hash_similarity():
    """Verify perceptual hash match scores 15 points when identical/close."""
    # Official logo hash is 'be6ce19394469639'
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "User",
        "image_hash": "be6ce19394469639",  # Exact match (0 bits difference)
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    img_signals = [s for s in result.signals if s.id == "image_hash_match"]
    assert len(img_signals) == 1
    assert img_signals[0].points == 15


def test_image_fetch_failure_handled_gracefully():
    """Verify image fetch failure does not crash and records missing evidence warning."""
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "User",
        "evidence": {"image_status": "unavailable_fetch_failed"},
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    img_signals = [s for s in result.signals if s.family == "image"]
    assert len(img_signals) == 0
    assert any("image fetch failed" in w.lower() for w in result.missing_evidence)


def test_scam_language_scores_15_points():
    """Verify scam language keywords in bio score 15 points."""
    candidate = {
        "candidate_type": "social_profile",
        "candidate_name": "Random User",
        "bio": "Official support agent here! DM to claim your refund and free money.",
    }
    result = evaluate_candidate(BRAND_NOVAPAY, candidate)
    scam_signals = [s for s in result.signals if s.id == "scam_language"]
    assert len(scam_signals) == 1
    assert scam_signals[0].points == 15
