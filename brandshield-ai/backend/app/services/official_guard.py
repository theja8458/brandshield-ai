from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel


class ExclusionStatus(str, Enum):
    OFFICIAL_EXCLUDED = "OFFICIAL_EXCLUDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SAFE_LISTED = "SAFE_LISTED"
    NOT_OFFICIAL = "NOT_OFFICIAL"


class OfficialEvaluationResult(BaseModel):
    status: ExclusionStatus
    is_excluded_from_scoring: bool
    matched_asset_id: Optional[str] = None
    reason: str
    conflict_details: Optional[str] = None


def normalize_url(url: Optional[str]) -> str:
    """Safely normalize URL for identity comparison."""
    if not url:
        return ""
    u = url.strip()
    try:
        parsed = urlparse(u)
        hostname = (parsed.hostname or "").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        path = parsed.path.rstrip("/")
        return f"{hostname}{path}"
    except Exception:
        return u.lower().rstrip("/")


def normalize_handle(handle: Optional[str]) -> str:
    """Normalize social handle: trim whitespace, strip leading @, lower-case."""
    if not handle:
        return ""
    return handle.strip().lstrip("@").lower()


def evaluate_official_status(
    brand: Dict[str, Any],
    candidate: Dict[str, Any],
) -> OfficialEvaluationResult:
    """
    CRITICAL SAFETY GUARD:
    Evaluate candidate against registered official brand assets BEFORE any scoring.
    
    1. Strong identifiers (canonical URL, stable account ID, package/bundle ID) are matched.
    2. Conflicting identifiers return REVIEW_REQUIRED (IDENTITY_CONFLICT).
    3. Confirmed official matches return OFFICIAL_EXCLUDED.
    4. Exact matches on safe_list return SAFE_LISTED.
    5. Similar names or publisher display names NEVER make an unknown asset official.
    """
    candidate_type = candidate.get("candidate_type", "")
    candidate_name = (candidate.get("candidate_name") or candidate.get("display_name") or candidate.get("app_name") or "").strip()

    # 1. Check Safe-List first (e.g. known legitimate subsidiaries or career accounts)
    safe_list: List[str] = brand.get("safe_list") or []
    for safe_item in safe_list:
        if safe_item.strip().lower() == candidate_name.lower():
            return OfficialEvaluationResult(
                status=ExclusionStatus.SAFE_LISTED,
                is_excluded_from_scoring=True,
                reason=f"Candidate name '{candidate_name}' is registered on brand safe_list ('{safe_item}'). Excluded from threat scoring.",
            )

    # 2. Evaluate Domain / Website Asset Match
    is_domain = (
        candidate_type in {"domain", "website", "domain_listing"}
        or "domain" in candidate
        or "website" in candidate
    )
    if is_domain:
        raw_val = (
            candidate.get("domain")
            or candidate.get("canonical_domain")
            or candidate.get("url")
            or candidate.get("website")
            or ""
        ).strip().lower()
        if "://" in raw_val:
            try:
                parsed = urlparse(raw_val)
                raw_val = parsed.hostname or raw_val
            except Exception:
                pass
        raw_val = raw_val.split("/")[0].split(":")[0]
        if raw_val.startswith("www."):
            raw_val = raw_val[4:]

        official_domains = [
            (d or "").strip().lower().replace("www.", "").split("/")[0].split(":")[0]
            for d in (brand.get("official_domains") or [])
            if d
        ]
        off_site = brand.get("official_website")
        if off_site:
            try:
                parsed_site = urlparse(off_site)
                host = (parsed_site.hostname or "").lower().replace("www.", "")
                if host and host not in official_domains:
                    official_domains.append(host)
            except Exception:
                pass

        if raw_val and raw_val in official_domains:
            return OfficialEvaluationResult(
                status=ExclusionStatus.OFFICIAL_EXCLUDED,
                is_excluded_from_scoring=True,
                reason=f"Matched registered official domain '{raw_val}'.",
            )

    # 3. Evaluate Social Asset Match
    is_social = (
        candidate_type == "social_profile"
        or "handle" in candidate
        or "canonical_profile_url" in candidate
    )
    if is_social:
        cand_platform = (candidate.get("platform") or "").lower()
        cand_handle = normalize_handle(candidate.get("handle"))
        cand_url_norm = normalize_url(candidate.get("canonical_profile_url") or candidate.get("profile_url"))
        cand_stable_id = (candidate.get("stable_account_id") or candidate.get("account_id") or "").strip()

        official_social = brand.get("official_social_assets") or []
        for asset in official_social:
            asset_platform = (asset.get("platform") or "").lower()
            asset_handle = normalize_handle(asset.get("normalized_handle") or asset.get("handle"))
            asset_url_norm = normalize_url(asset.get("canonical_profile_url"))
            asset_stable_id = (asset.get("stable_account_id") or "").strip()
            asset_id = asset.get("asset_id")

            # Check platform match (if both specify platforms)
            platform_matches = not cand_platform or not asset_platform or (cand_platform == asset_platform)
            if not platform_matches:
                continue

            # Check for Stable Account ID match
            stable_id_matches = (
                bool(cand_stable_id)
                and bool(asset_stable_id)
                and (cand_stable_id == asset_stable_id)
            )

            # Check Handle & URL matches
            handle_matches = bool(cand_handle) and (cand_handle == asset_handle)
            url_matches = bool(cand_url_norm) and (cand_url_norm == asset_url_norm)

            # --- CONFLICT DETECTION ---
            # If stable account ID matches official, but handle or URL is completely different:
            if stable_id_matches:
                if (cand_handle and asset_handle and cand_handle != asset_handle) or (
                    cand_url_norm and asset_url_norm and cand_url_norm != asset_url_norm
                ):
                    return OfficialEvaluationResult(
                        status=ExclusionStatus.REVIEW_REQUIRED,
                        is_excluded_from_scoring=False,
                        matched_asset_id=asset_id,
                        reason="IDENTITY_CONFLICT: Candidate shares official stable account ID but has a differing handle or URL.",
                        conflict_details=f"Official ID '{asset_stable_id}' matched, but handle '{cand_handle}' != official '{asset_handle}'.",
                    )
                # Verified match by stable ID
                return OfficialEvaluationResult(
                    status=ExclusionStatus.OFFICIAL_EXCLUDED,
                    is_excluded_from_scoring=True,
                    matched_asset_id=asset_id,
                    reason=f"Matched registered official social account ID '{asset_stable_id}' ({asset_platform}).",
                )

            # Handle + URL match
            if handle_matches and (url_matches or not cand_url_norm or not asset_url_norm):
                # If stable account IDs are both provided but differ:
                if cand_stable_id and asset_stable_id and cand_stable_id != asset_stable_id:
                    return OfficialEvaluationResult(
                        status=ExclusionStatus.REVIEW_REQUIRED,
                        is_excluded_from_scoring=False,
                        matched_asset_id=asset_id,
                        reason="IDENTITY_CONFLICT: Candidate matches official handle but has conflicting platform stable account ID.",
                        conflict_details=f"Handle matches '{asset_handle}', but candidate stable ID '{cand_stable_id}' differs from registered '{asset_stable_id}'.",
                    )
                return OfficialEvaluationResult(
                    status=ExclusionStatus.OFFICIAL_EXCLUDED,
                    is_excluded_from_scoring=True,
                    matched_asset_id=asset_id,
                    reason=f"Matched registered official social handle '@{asset_handle}' ({asset_platform}).",
                )

            # Canonical URL exact match
            if url_matches:
                if cand_handle and asset_handle and cand_handle != asset_handle:
                    return OfficialEvaluationResult(
                        status=ExclusionStatus.REVIEW_REQUIRED,
                        is_excluded_from_scoring=False,
                        matched_asset_id=asset_id,
                        reason="IDENTITY_CONFLICT: Candidate profile URL matches official asset, but handle differs.",
                        conflict_details=f"URL matches '{asset_url_norm}', but candidate handle '{cand_handle}' != official '{asset_handle}'.",
                    )
                return OfficialEvaluationResult(
                    status=ExclusionStatus.OFFICIAL_EXCLUDED,
                    is_excluded_from_scoring=True,
                    matched_asset_id=asset_id,
                    reason=f"Matched registered official canonical profile URL ({asset_platform}).",
                )

    # 3. Evaluate App Asset Match
    is_app = (
        candidate_type == "app_listing"
        or "package_or_bundle_id" in candidate
        or "bundleId" in candidate
        or "trackId" in candidate
    )
    if is_app:
        cand_store = (candidate.get("store") or "").lower()
        cand_bundle_id = (candidate.get("package_or_bundle_id") or candidate.get("bundleId") or "").strip().lower()
        cand_url_norm = normalize_url(candidate.get("canonical_listing_url") or candidate.get("listing_url") or candidate.get("trackViewUrl"))
        cand_pub_id = (candidate.get("publisher_id") or candidate.get("artistId") or "").strip()
        cand_pub_name = (candidate.get("publisher_or_developer") or candidate.get("sellerName") or "").strip().lower()

        official_apps = brand.get("official_app_assets") or []
        for app in official_apps:
            app_store = (app.get("store") or "").lower()
            app_bundle_id = (app.get("package_or_bundle_id") or "").strip().lower()
            app_url_norm = normalize_url(app.get("canonical_listing_url"))
            app_pub_id = (app.get("trusted_publisher_id") or "").strip()
            app_pub_name = (app.get("trusted_publisher_name") or "").strip().lower()
            asset_id = app.get("asset_id")

            store_matches = not cand_store or not app_store or (cand_store == app_store)
            if not store_matches:
                continue

            bundle_matches = bool(cand_bundle_id) and (cand_bundle_id == app_bundle_id)
            url_matches = bool(cand_url_norm) and (cand_url_norm == app_url_norm)

            # If bundle ID or canonical URL matches
            if bundle_matches or url_matches:
                # --- APP CONFLICT DETECTION ---
                # If bundle ID matches official app, but publisher ID is provided and differs:
                if cand_pub_id and app_pub_id and cand_pub_id != app_pub_id:
                    return OfficialEvaluationResult(
                        status=ExclusionStatus.REVIEW_REQUIRED,
                        is_excluded_from_scoring=False,
                        matched_asset_id=asset_id,
                        reason="IDENTITY_CONFLICT: Candidate app matches official package ID but has conflicting publisher ID.",
                        conflict_details=f"Package ID matches '{app_bundle_id}', but publisher ID '{cand_pub_id}' != trusted '{app_pub_id}'.",
                    )

                # If bundle ID matches official app, but publisher name is completely different (and non-empty)
                if cand_pub_name and app_pub_name and cand_pub_name != app_pub_name and not cand_pub_id:
                    return OfficialEvaluationResult(
                        status=ExclusionStatus.REVIEW_REQUIRED,
                        is_excluded_from_scoring=False,
                        matched_asset_id=asset_id,
                        reason="IDENTITY_CONFLICT: Candidate app matches official package ID but has conflicting publisher name.",
                        conflict_details=f"Package ID matches '{app_bundle_id}', but publisher name '{cand_pub_name}' != trusted '{app_pub_name}'.",
                    )

                # Confirmed official match
                return OfficialEvaluationResult(
                    status=ExclusionStatus.OFFICIAL_EXCLUDED,
                    is_excluded_from_scoring=True,
                    matched_asset_id=asset_id,
                    reason=f"Matched registered official app bundle ID '{app_bundle_id}' ({app_store}).",
                )

    # 4. Fallback: Not Official
    return OfficialEvaluationResult(
        status=ExclusionStatus.NOT_OFFICIAL,
        is_excluded_from_scoring=False,
        reason="No match with registered official assets. Candidate subject to suspiciousness evaluation.",
    )
