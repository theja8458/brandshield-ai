import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from rapidfuzz.distance import OSA, DamerauLevenshtein

from app.detection.config import (
    DOMAIN_LOOKALIKE_SIMILARITY_THRESHOLD,
    EVASION_BONUS_ADDED_SCAM_WORD,
    EVASION_BONUS_HOMOGLYPH_LEETSPEAK,
    EVASION_BONUS_SPACING_ONLY,
    MAX_DESCRIPTION_SIMILARITY,
    MAX_IMAGE_SIMILARITY,
    MAX_LOOKALIKE_DOMAIN,
    MAX_NAME_SIMILARITY,
    MAX_PUBLISHER_MISMATCH,
    MAX_SCAM_LANGUAGE,
    NAME_FAMILY_CAP,
    POTENTIAL_THREAT_THRESHOLD,
    PUBLISHER_MISSING_POINTS,
    SCAM_LANGUAGE_KEYWORDS,
    SIMILARITY_BAND_EXACT_COMPACT,
    SIMILARITY_BAND_HIGH,
    SIMILARITY_BAND_LOW_TOKEN,
    SIMILARITY_BAND_MEDIUM,
    SIMILARITY_BAND_NONE,
    THRESHOLD_CRITICAL,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    TOTAL_SCORE_CAP,
)
from app.detection.normalizer import (
    normalize_candidate_name,
    strip_punctuation_and_whitespace,
)
from app.services.official_guard import (
    ExclusionStatus,
    evaluate_official_status,
)


class DetectionSignal(BaseModel):
    id: str
    family: str
    points: int
    max_points: int
    matched_field: str
    matched_value: str
    human_readable_reason: str


class DetectionEvaluationResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    severity: str
    classification: str
    signals: List[DetectionSignal]
    missing_evidence: List[str]
    evidence_completeness: float
    analysis_time: str
    reason: str


def compute_phash_hamming_distance(hash1_hex: str, hash2_hex: str) -> Optional[int]:
    """Compute bitwise Hamming distance between two 64-bit hexadecimal hashes."""
    if not hash1_hex or not hash2_hex:
        return None
    try:
        val1 = int(hash1_hex, 16)
        val2 = int(hash2_hex, 16)
        return bin(val1 ^ val2).count("1")
    except ValueError:
        return None


def extract_domain(url_or_domain: str) -> str:
    """Extract lowercased clean domain without protocol, path, or www."""
    if not url_or_domain:
        return ""
    text = url_or_domain.strip().lower()
    if "://" in text:
        try:
            parsed = urlparse(text)
            text = parsed.hostname or text
        except Exception:
            pass
    text = text.split("/")[0].split(":")[0]
    if text.startswith("www."):
        text = text[4:]
    return text


def evaluate_candidate(
    brand: Dict[str, Any],
    candidate: Dict[str, Any],
) -> DetectionEvaluationResult:
    """
    CRITICAL SCORING ENGINE:
    Evaluates candidate against brand metadata with deterministic, explainable scoring.
    
    1. Runs Official Safety Guard first.
       - Confirmed official matches return OFFICIAL_EXCLUDED (score = 0).
       - Confirmed safe-list variants return SAFE_LISTED (score = 0, LOW_RISK).
       - Identity conflicts override classification to REVIEW_REQUIRED.
    2. Calculates independent signal families:
       - Name family (name similarity + largest evasion bonus, capped at 40).
       - Lookalike domain (max 25, 0 for exact official domain).
       - App publisher mismatch (max 20).
       - Scam language (max 15).
       - Image pHash similarity (max 15, only if real hashes exist).
       - Description similarity (max 10).
    3. Enforces Name-Only ceiling (cannot exceed 40 without corroborating evidence).
    4. Calculates final classification, severity, and granular audit signals.
    """
    now = datetime.now(timezone.utc).isoformat()
    signals: List[DetectionSignal] = []
    missing_evidence: List[str] = []

    # -------------------------------------------------------------
    # STEP 1: OFFICIAL GUARD CHECK (BEFORE ANY SCORING)
    # -------------------------------------------------------------
    official_eval = evaluate_official_status(brand, candidate)

    if official_eval.status == ExclusionStatus.OFFICIAL_EXCLUDED:
        signals.append(
            DetectionSignal(
                id="official_asset_excluded",
                family="official_guard",
                points=0,
                max_points=0,
                matched_field="official_asset",
                matched_value=official_eval.matched_asset_id or "verified_identifier",
                human_readable_reason=official_eval.reason,
            )
        )
        return DetectionEvaluationResult(
            score=0,
            severity="Low",
            classification="OFFICIAL_EXCLUDED",
            signals=signals,
            missing_evidence=[],
            evidence_completeness=1.0,
            analysis_time=now,
            reason=official_eval.reason,
        )

    if official_eval.status == ExclusionStatus.SAFE_LISTED:
        signals.append(
            DetectionSignal(
                id="safe_list_exclusion",
                family="safe_list",
                points=0,
                max_points=0,
                matched_field="safe_list",
                matched_value=candidate.get("candidate_name") or "",
                human_readable_reason=official_eval.reason,
            )
        )
        return DetectionEvaluationResult(
            score=0,
            severity="Low",
            classification="LOW_RISK",
            signals=signals,
            missing_evidence=[],
            evidence_completeness=1.0,
            analysis_time=now,
            reason=official_eval.reason,
        )

    is_identity_conflict = official_eval.status == ExclusionStatus.REVIEW_REQUIRED

    # -------------------------------------------------------------
    # STEP 2: NAME FAMILY EVALUATION
    # -------------------------------------------------------------
    brand_name = brand.get("name", "")
    brand_compact = strip_punctuation_and_whitespace(brand_name.casefold())
    brand_aliases = [strip_punctuation_and_whitespace(a.casefold()) for a in brand.get("aliases", []) if a]

    cand_raw_name = (
        candidate.get("candidate_name")
        or candidate.get("display_name")
        or candidate.get("app_name")
        or candidate.get("handle")
        or ""
    ).strip()

    # Run full normalization
    norm_res = normalize_candidate_name(cand_raw_name, brand_name)

    name_sim_points = 0
    name_matched_reason = "No significant name similarity"

    # Check aliases first: exact match to an alias scores 0 name similarity
    if norm_res.core_compact in brand_aliases:
        name_sim_points = 0
        name_matched_reason = "Matches registered brand alias (scored 0 points)"
    elif norm_res.core_compact == brand_compact:
        # Exact compact match to brand name, but NOT registered official asset
        name_sim_points = SIMILARITY_BAND_EXACT_COMPACT  # 35
        name_matched_reason = f"Exact normalized compact match to brand name '{brand_name}'"
    else:
        # Use transposition-aware RapidFuzz metric (OSA or Damerau-Levenshtein)
        osa_sim = OSA.normalized_similarity(norm_res.core_compact, brand_compact)
        dam_sim = DamerauLevenshtein.normalized_similarity(norm_res.core_compact, brand_compact)
        token_ratio = fuzz.token_set_ratio(cand_raw_name, brand_name) / 100.0

        # Best effective similarity
        best_sim = max(osa_sim, dam_sim)

        # Check token containment: does the candidate contain the brand name as a distinct word?
        brand_token_contained = any(t == brand_compact for t in norm_res.tokens)

        if best_sim >= 0.90:
            name_sim_points = SIMILARITY_BAND_HIGH  # 30
            name_matched_reason = f"High transposition-aware similarity ({best_sim:.2f} >= 0.90)"
        elif best_sim >= 0.80:
            name_sim_points = SIMILARITY_BAND_MEDIUM  # 20
            name_matched_reason = f"Moderate name similarity ({best_sim:.2f} in 0.80-0.89 band)"
        elif best_sim >= 0.70 and (brand_token_contained or token_ratio >= 0.75):
            name_sim_points = SIMILARITY_BAND_LOW_TOKEN  # 8
            name_matched_reason = f"Borderline name similarity ({best_sim:.2f}) with brand token containment"
        else:
            name_sim_points = SIMILARITY_BAND_NONE  # 0
            name_matched_reason = f"Name similarity below detection threshold ({best_sim:.2f} < 0.70)"

    # Evasion bonuses: take the LARGEST applicable bonus, do NOT sum
    applicable_bonuses = []

    if norm_res.has_homoglyph_or_leetspeak:
        applicable_bonuses.append((EVASION_BONUS_HOMOGLYPH_LEETSPEAK, "Homoglyph or leetspeak character substitution detected (+8)"))
    if norm_res.has_added_generic_words:
        words_str = ", ".join(norm_res.detected_generic_words)
        applicable_bonuses.append((EVASION_BONUS_ADDED_SCAM_WORD, f"Added impersonation/scam words ({words_str}) (+6)"))
    if norm_res.has_spacing_change:
        applicable_bonuses.append((EVASION_BONUS_SPACING_ONLY, "Spacing-only variation of brand name detected (+3)"))

    evasion_bonus_points = 0
    evasion_bonus_reason = "No evasion patterns detected"
    if applicable_bonuses:
        # Sort by points descending to take the LARGEST
        applicable_bonuses.sort(key=lambda x: x[0], reverse=True)
        evasion_bonus_points = applicable_bonuses[0][0]
        evasion_bonus_reason = applicable_bonuses[0][1]

    # Combine name family and apply the 40-point Name Family Cap
    raw_name_family_total = name_sim_points + evasion_bonus_points
    name_family_points = min(raw_name_family_total, NAME_FAMILY_CAP)

    if name_sim_points > 0:
        signals.append(
            DetectionSignal(
                id="name_similarity",
                family="name",
                points=name_sim_points,
                max_points=MAX_NAME_SIMILARITY,
                matched_field="candidate_name",
                matched_value=cand_raw_name,
                human_readable_reason=name_matched_reason,
            )
        )

    if evasion_bonus_points > 0:
        signals.append(
            DetectionSignal(
                id="evasion_bonus",
                family="name",
                points=evasion_bonus_points,
                max_points=10,
                matched_field="candidate_name",
                matched_value=cand_raw_name,
                human_readable_reason=f"Largest evasion bonus applied: {evasion_bonus_reason}",
            )
        )

    # -------------------------------------------------------------
    # STEP 3: LOOKALIKE DOMAIN EVALUATION
    # -------------------------------------------------------------
    official_domains = [extract_domain(d) for d in brand.get("official_domains", []) if d]
    cand_links = candidate.get("external_links") or []
    if isinstance(cand_links, str):
        cand_links = [cand_links]

    # Also check bio/description for embedded links
    bio_text = candidate.get("bio") or candidate.get("description") or ""

    domain_points = 0
    domain_signal_created = False

    for link in cand_links:
        if not link:
            continue
        c_dom = extract_domain(link)
        if not c_dom:
            continue

        # Exact match to official domain: Positive signal, 0 points
        if c_dom in official_domains:
            domain_points = 0
            domain_signal_created = True
            signals.append(
                DetectionSignal(
                    id="official_domain_link",
                    family="domain",
                    points=0,
                    max_points=MAX_LOOKALIKE_DOMAIN,
                    matched_field="external_links",
                    matched_value=c_dom,
                    human_readable_reason=f"Link targets exact verified official domain '{c_dom}' (0 risk points).",
                )
            )
            break

        # Check lookalike domain against each official domain
        for off_dom in official_domains:
            # RapidFuzz similarity between domain strings
            dom_sim = OSA.normalized_similarity(c_dom, off_dom)
            contains_brand_token = brand_compact in c_dom

            if (dom_sim >= DOMAIN_LOOKALIKE_SIMILARITY_THRESHOLD or contains_brand_token) and c_dom != off_dom:
                domain_points = MAX_LOOKALIKE_DOMAIN  # 25
                domain_signal_created = True
                signals.append(
                    DetectionSignal(
                        id="lookalike_domain",
                        family="domain",
                        points=MAX_LOOKALIKE_DOMAIN,
                        max_points=MAX_LOOKALIKE_DOMAIN,
                        matched_field="external_links",
                        matched_value=c_dom,
                        human_readable_reason=f"External link domain '{c_dom}' is similar to official domain '{off_dom}', but not owned by it.",
                    )
                )
                break
        if domain_points > 0:
            break

    # -------------------------------------------------------------
    # STEP 4: APP PUBLISHER MISMATCH EVALUATION (FOR APPS)
    # -------------------------------------------------------------
    publisher_points = 0
    candidate_type = candidate.get("candidate_type", "")
    is_app = (
        candidate_type == "app_listing"
        or "package_or_bundle_id" in candidate
        or "store" in candidate
    )

    if is_app:
        official_apps = brand.get("official_app_assets") or []
        trusted_pub_id = ""
        trusted_pub_name = ""
        if official_apps:
            trusted_pub_id = (official_apps[0].get("trusted_publisher_id") or "").strip()
            trusted_pub_name = (official_apps[0].get("trusted_publisher_name") or "").strip()

        cand_pub_id = (candidate.get("publisher_id") or candidate.get("artistId") or "").strip()
        cand_pub_name = (candidate.get("publisher_or_developer") or candidate.get("sellerName") or "").strip()

        if trusted_pub_id and cand_pub_id:
            if cand_pub_id != trusted_pub_id:
                publisher_points = MAX_PUBLISHER_MISMATCH  # 20
                signals.append(
                    DetectionSignal(
                        id="publisher_mismatch",
                        family="publisher",
                        points=MAX_PUBLISHER_MISMATCH,
                        max_points=MAX_PUBLISHER_MISMATCH,
                        matched_field="publisher_id",
                        matched_value=cand_pub_id,
                        human_readable_reason=f"App developer/publisher ID '{cand_pub_id}' does not match trusted publisher ID '{trusted_pub_id}'.",
                    )
                )
            else:
                publisher_points = 0
        elif not cand_pub_id and not cand_pub_name:
            publisher_points = PUBLISHER_MISSING_POINTS  # 8
            missing_evidence.append("App publisher/developer identifier is completely missing from listing.")
            signals.append(
                DetectionSignal(
                    id="publisher_missing",
                    family="publisher",
                    points=PUBLISHER_MISSING_POINTS,
                    max_points=MAX_PUBLISHER_MISMATCH,
                    matched_field="publisher_or_developer",
                    matched_value="[missing]",
                    human_readable_reason="App listing is missing developer and publisher identity details.",
                )
            )

    # -------------------------------------------------------------
    # STEP 5: SCAM LANGUAGE EVALUATION
    # -------------------------------------------------------------
    scam_lang_points = 0
    combined_text = f"{candidate.get('bio', '')} {candidate.get('description', '')}".lower()
    matched_scam_keywords = []

    for kw in SCAM_LANGUAGE_KEYWORDS:
        if kw in combined_text:
            matched_scam_keywords.append(kw)

    if matched_scam_keywords:
        scam_lang_points = MAX_SCAM_LANGUAGE  # 15
        kw_display = ", ".join(matched_scam_keywords[:3])
        signals.append(
            DetectionSignal(
                id="scam_language",
                family="language",
                points=MAX_SCAM_LANGUAGE,
                max_points=MAX_SCAM_LANGUAGE,
                matched_field="description",
                matched_value=kw_display,
                human_readable_reason=f"Suspicious phrasing detected in bio/description: '{kw_display}'.",
            )
        )

    # -------------------------------------------------------------
    # STEP 6: DESCRIPTION SIMILARITY EVALUATION
    # -------------------------------------------------------------
    desc_points = 0
    brand_desc = brand.get("description", "")
    cand_desc = candidate.get("description") or candidate.get("bio") or ""

    if brand_desc and cand_desc and len(cand_desc) > 15:
        desc_ratio = fuzz.token_set_ratio(cand_desc, brand_desc)
        if desc_ratio >= 80:
            desc_points = MAX_DESCRIPTION_SIMILARITY  # 10
            signals.append(
                DetectionSignal(
                    id="description_similarity",
                    family="description",
                    points=MAX_DESCRIPTION_SIMILARITY,
                    max_points=MAX_DESCRIPTION_SIMILARITY,
                    matched_field="description",
                    matched_value=f"Token similarity: {desc_ratio:.0f}%",
                    human_readable_reason=f"Candidate description strongly mirrors official brand description ({desc_ratio:.0f}% similarity).",
                )
            )
        elif desc_ratio >= 60:
            desc_points = 5
            signals.append(
                DetectionSignal(
                    id="description_similarity",
                    family="description",
                    points=5,
                    max_points=MAX_DESCRIPTION_SIMILARITY,
                    matched_field="description",
                    matched_value=f"Token similarity: {desc_ratio:.0f}%",
                    human_readable_reason=f"Candidate description shares phrases with official brand description ({desc_ratio:.0f}% similarity).",
                )
            )

    # -------------------------------------------------------------
    # STEP 7: IMAGE PERCEPTUAL HASH SIMILARITY EVALUATION
    # -------------------------------------------------------------
    image_points = 0
    brand_logo = brand.get("official_logo") or {}
    brand_logo_hash = brand_logo.get("image_hash")
    cand_image_hash = candidate.get("image_hash")

    cand_evidence = candidate.get("evidence") or {}
    image_status = cand_evidence.get("image_status")

    if image_status == "unavailable_fetch_failed":
        missing_evidence.append("Image fetch failed during collection; image comparison signal unavailable.")
    elif not cand_image_hash:
        missing_evidence.append("No avatar/icon image hash provided.")
    elif cand_image_hash and brand_logo_hash:
        dist = compute_phash_hamming_distance(cand_image_hash, brand_logo_hash)
        if dist is not None:
            if dist <= 6:
                # <= 6 bits difference on a 64-bit pHash is >= 90% visual similarity
                image_points = MAX_IMAGE_SIMILARITY  # 15
                signals.append(
                    DetectionSignal(
                        id="image_hash_match",
                        family="image",
                        points=MAX_IMAGE_SIMILARITY,
                        max_points=MAX_IMAGE_SIMILARITY,
                        matched_field="image_hash",
                        matched_value=f"Hamming distance: {dist}/64",
                        human_readable_reason=f"Avatar/icon visual perceptual hash strongly matches official brand logo (Hamming distance {dist} <= 6).",
                    )
                )
            elif dist <= 10:
                image_points = 8
                signals.append(
                    DetectionSignal(
                        id="image_hash_moderate",
                        family="image",
                        points=8,
                        max_points=MAX_IMAGE_SIMILARITY,
                        matched_field="image_hash",
                        matched_value=f"Hamming distance: {dist}/64",
                        human_readable_reason=f"Avatar/icon visual perceptual hash shows moderate resemblance to official logo (Hamming distance {dist}).",
                    )
                )

    # -------------------------------------------------------------
    # STEP 8: SCORE AGGREGATION & SEVERITY
    # -------------------------------------------------------------
    # Independent families:
    # 1. Name family (name similarity + largest evasion bonus, capped at 40)
    # 2. Lookalike domain (max 25)
    # 3. Publisher mismatch (max 20)
    # 4. Scam language (max 15)
    # 5. Image similarity (max 15)
    # 6. Description similarity (max 10)
    total_score = (
        name_family_points
        + domain_points
        + publisher_points
        + scam_lang_points
        + desc_points
        + image_points
    )

    total_score = min(total_score, TOTAL_SCORE_CAP)

    # Calculate evidence completeness
    total_possible_signals = 6
    provided_signal_families = sum(
        [
            1 if name_sim_points > 0 or evasion_bonus_points > 0 else 0,
            1 if domain_points > 0 or len(cand_links) > 0 else 0,
            1 if publisher_points > 0 or (is_app and candidate.get("publisher_id")) else 0,
            1 if scam_lang_points > 0 else 0,
            1 if cand_image_hash else 0,
            1 if cand_desc else 0,
        ]
    )
    completeness = round(min(1.0, provided_signal_families / total_possible_signals), 2)

    # Determine severity
    if total_score >= THRESHOLD_CRITICAL:
        severity = "Critical"
    elif total_score >= THRESHOLD_HIGH:
        severity = "High"
    elif total_score >= THRESHOLD_MEDIUM:
        severity = "Medium"
    else:
        severity = "Low"

    # Determine classification
    if is_identity_conflict:
        classification = "REVIEW_REQUIRED"
        reason = f"IDENTITY_CONFLICT detected: {official_eval.conflict_details or official_eval.reason}"
    elif total_score >= POTENTIAL_THREAT_THRESHOLD:
        classification = "POTENTIAL_THREAT"
        reason = f"Candidate accumulated risk score of {total_score}/100 across observable signal families."
    else:
        classification = "LOW_RISK"
        reason = f"Candidate risk score of {total_score}/100 falls below potential threat threshold."

    return DetectionEvaluationResult(
        score=total_score,
        severity=severity,
        classification=classification,
        signals=signals,
        missing_evidence=missing_evidence,
        evidence_completeness=completeness,
        analysis_time=now,
        reason=reason,
    )
