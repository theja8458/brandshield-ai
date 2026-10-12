import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from app.campaigns.config import (
    CAMPAIGN_DISCLAIMER,
    GENERIC_EXCLUDED_DOMAINS,
    INDICATOR_CONTACT_EMAIL,
    INDICATOR_CONTACT_PHONE,
    INDICATOR_EXACT_DOMAIN,
    INDICATOR_PERCEPTUAL_HASH,
    INDICATOR_PUBLISHER_ID,
)
from app.crud.brand import get_brand
from app.crud.candidate import get_candidates_collection
from app.schemas.brand import normalize_domain
from app.schemas.campaign import (
    CampaignGraphResponse,
    CampaignGroup,
    GraphEdge,
    GraphNode,
    NonEdgesAudit,
)

logger = logging.getLogger("brandshield.campaigns.graph_builder")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\+?[0-9]{10,15}")


def extract_candidate_indicators(
    candidate: Dict[str, Any],
    brand: Optional[Dict[str, Any]],
    non_edges: NonEdgesAudit,
) -> Set[Tuple[str, str]]:
    """
    Extract concrete, verifiable technical indicators from a single candidate.
    Applies strict exclusions for generic domains, official brand domains,
    official publisher accounts, and official victim logo hashes.
    """
    indicators: Set[Tuple[str, str]] = set()
    cand_id = candidate.get("candidate_id", "")

    # Retrieve official brand exclusions if available
    official_domains = set()
    official_publisher_ids = set()
    official_logo_hash = None

    if brand:
        if brand.get("official_website"):
            official_domains.add(normalize_domain(brand["official_website"]))
        for dom in brand.get("official_domains", []):
            official_domains.add(normalize_domain(dom))
        for app in brand.get("official_app_assets", []):
            if app.get("trusted_publisher_id"):
                official_publisher_ids.add(app["trusted_publisher_id"].strip().lower())
        logo_obj = brand.get("official_logo") or {}
        if logo_obj.get("image_hash"):
            official_logo_hash = logo_obj["image_hash"].strip().lower()

    # 1. EXTERNAL DOMAINS
    links = candidate.get("external_links") or []
    for link in links:
        if not link or not isinstance(link, str):
            continue
        dom = normalize_domain(link)
        if not dom:
            continue

        # Check if generic domain
        if dom in GENERIC_EXCLUDED_DOMAINS:
            if dom not in non_edges.generic_domains_excluded:
                non_edges.generic_domains_excluded[dom] = []
            if cand_id not in non_edges.generic_domains_excluded[dom]:
                non_edges.generic_domains_excluded[dom].append(cand_id)
            continue

        # Check if official brand domain
        if dom in official_domains:
            if dom not in non_edges.official_domain_matches_excluded:
                non_edges.official_domain_matches_excluded[dom] = []
            if cand_id not in non_edges.official_domain_matches_excluded[dom]:
                non_edges.official_domain_matches_excluded[dom].append(cand_id)
            continue

        indicators.add((INDICATOR_EXACT_DOMAIN, dom))

    # 2. PUBLISHER ID (Apps)
    pub_id = (candidate.get("publisher_id") or "").strip()
    if pub_id and pub_id.lower() not in {"[missing]", "unknown", "none"}:
        if pub_id.lower() in official_publisher_ids:
            if pub_id not in non_edges.official_publisher_matches_excluded:
                non_edges.official_publisher_matches_excluded[pub_id] = []
            if cand_id not in non_edges.official_publisher_matches_excluded[pub_id]:
                non_edges.official_publisher_matches_excluded[pub_id].append(cand_id)
        else:
            indicators.add((INDICATOR_PUBLISHER_ID, pub_id))

    # 3. PERCEPTUAL IMAGE HASH
    img_hash = (candidate.get("image_hash") or "").strip().lower()
    if img_hash and len(img_hash) >= 8:
        if official_logo_hash and img_hash == official_logo_hash:
            if img_hash not in non_edges.official_logo_matches_excluded:
                non_edges.official_logo_matches_excluded[img_hash] = []
            if cand_id not in non_edges.official_logo_matches_excluded[img_hash]:
                non_edges.official_logo_matches_excluded[img_hash].append(cand_id)
        else:
            indicators.add((INDICATOR_PERCEPTUAL_HASH, img_hash))

    # 4. CONTACT EMAIL & PHONE
    text_corpus = f"{candidate.get('bio', '')} {candidate.get('description', '')}"
    ext_ids = candidate.get("external_identifiers") or {}
    for v in ext_ids.values():
        if isinstance(v, str):
            text_corpus += f" {v}"

    emails = EMAIL_REGEX.findall(text_corpus)
    for em in emails:
        clean_email = em.strip().lower()
        # Avoid generic/placeholder domains in emails
        email_domain = clean_email.split("@")[-1]
        if email_domain not in official_domains:
            indicators.add((INDICATOR_CONTACT_EMAIL, clean_email))

    phones = PHONE_REGEX.findall(text_corpus)
    for ph in phones:
        clean_phone = ph.strip()
        if len(clean_phone) >= 10:
            indicators.add((INDICATOR_CONTACT_PHONE, clean_phone))

    return indicators


def format_edge_explanation(indicator_type: str, matched_value: str) -> str:
    """Standardized ethical explanation preserving potential coordination label."""
    if indicator_type == INDICATOR_EXACT_DOMAIN:
        return (
            f"Both candidates list the exact normalized external domain '{matched_value}', "
            f"which is not an official or generic/shared domain. This is a potential relationship only; "
            f"it does not prove common ownership."
        )
    elif indicator_type == INDICATOR_PUBLISHER_ID:
        return (
            f"Both app listings carry the identical publisher/developer identifier '{matched_value}', "
            f"which is not the trusted publisher. This is a potential relationship only; "
            f"it does not prove common ownership."
        )
    elif indicator_type == INDICATOR_PERCEPTUAL_HASH:
        return (
            f"Both candidates have the identical perceptual hash '{matched_value}', "
            f"computed from retrieved image files (not the official logo hash). This is a potential "
            f"relationship only; it does not prove common ownership."
        )
    elif indicator_type == INDICATOR_CONTACT_EMAIL:
        return (
            f"Both candidates supply the identical contact email '{matched_value}' in their metadata. "
            f"This is a potential relationship only; it does not prove common ownership."
        )
    elif indicator_type == INDICATOR_CONTACT_PHONE:
        return (
            f"Both candidates supply the identical contact phone number '{matched_value}' in their metadata. "
            f"This is a potential relationship only; it does not prove common ownership."
        )
    return (
        f"Candidates share concrete indicator '{indicator_type}' with value '{matched_value}'. "
        f"This is a potential relationship only; it does not prove common ownership."
    )


def build_campaign_graph(
    candidates: List[Dict[str, Any]],
    brand: Optional[Dict[str, Any]] = None,
    include_official: bool = False,
) -> CampaignGraphResponse:
    """
    Constructs an explainable Impersonation Campaign Graph directly from MongoDB Atlas records.
    - Excludes OFFICIAL_EXCLUDED assets by default.
    - Connects candidates ONLY if they share concrete, verifiable technical indicators.
    - Never creates edges based on name similarity alone.
    - Grouping is labeled POTENTIAL_COORDINATION.
    """
    non_edges = NonEdgesAudit()

    # Filter candidate nodes
    filtered_candidates: List[Dict[str, Any]] = []
    for c in candidates:
        if not include_official and c.get("classification") == "OFFICIAL_EXCLUDED":
            continue
        filtered_candidates.append(c)

    # Map candidate IDs to indicators
    cand_indicators: Dict[str, Set[Tuple[str, str]]] = {}
    for c in filtered_candidates:
        cid = c["candidate_id"]
        cand_indicators[cid] = extract_candidate_indicators(c, brand, non_edges)

    # Invert mapping: (indicator_type, value) -> list of candidate IDs
    indicator_to_cands: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for cid, ind_set in cand_indicators.items():
        for ind in ind_set:
            indicator_to_cands[ind].append(cid)

    # Build unique edges
    edges: List[GraphEdge] = []
    seen_edge_keys = set()
    adjacency: Dict[str, Set[str]] = defaultdict(set)

    for (ind_type, matched_val), c_ids in indicator_to_cands.items():
        if len(c_ids) < 2:
            continue
        sorted_ids = sorted(c_ids)
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                src_id = sorted_ids[i]
                tgt_id = sorted_ids[j]
                edge_key = (src_id, tgt_id, ind_type, matched_val)
                if edge_key in seen_edge_keys:
                    continue
                seen_edge_keys.add(edge_key)

                edge_id = f"EDGE-{src_id}-{tgt_id}-{ind_type}"
                expl = format_edge_explanation(ind_type, matched_val)

                # Determine provenance
                cand_src = next((c for c in filtered_candidates if c["candidate_id"] == src_id), {})
                cand_tgt = next((c for c in filtered_candidates if c["candidate_id"] == tgt_id), {})
                prov = "demo"
                if cand_src.get("source_type") == "live_connector" and cand_tgt.get("source_type") == "live_connector":
                    prov = "live_connector"
                elif cand_src.get("source_type") == "manual" or cand_tgt.get("source_type") == "manual":
                    prov = "manual"

                edges.append(
                    GraphEdge(
                        id=edge_id,
                        source=src_id,
                        target=tgt_id,
                        indicator_type=ind_type,
                        matched_value=matched_val,
                        explanation=expl,
                        source_provenance=prov,
                    )
                )
                adjacency[src_id].add(tgt_id)
                adjacency[tgt_id].add(src_id)

    # Compute connected components (Campaign Groups)
    visited = set()
    groups: List[CampaignGroup] = []
    cand_to_group_id: Dict[str, str] = {}
    group_counter = 1

    for c in filtered_candidates:
        cid = c["candidate_id"]
        if cid in visited or cid not in adjacency:
            continue

        # BFS component
        component = []
        queue = [cid]
        visited.add(cid)
        while queue:
            curr = queue.pop(0)
            component.append(curr)
            for neighbor in adjacency[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(component) >= 2:
            group_id = f"CG-{group_counter:03d}"
            group_counter += 1

            member_set = set(component)
            group_links = [
                e for e in edges
                if e.source in member_set and e.target in member_set
            ]
            shared_types = sorted(list({e.indicator_type for e in group_links}))

            comp_docs = [c for c in filtered_candidates if c["candidate_id"] in member_set]
            highest_risk = max((d.get("score", 0) for d in comp_docs), default=0)
            highest_sev = "Low"
            for sev in ["Critical", "High", "Medium", "Review Required"]:
                if any(d.get("severity") == sev or d.get("classification") == sev for d in comp_docs):
                    highest_sev = sev
                    break

            cand_types = sorted(list({d.get("candidate_type", "social_profile") for d in comp_docs}))
            avg_comp = round(
                sum((d.get("evidence_completeness", 1.0) for d in comp_docs)) / len(comp_docs),
                2,
            )

            for member_id in component:
                cand_to_group_id[member_id] = group_id

            groups.append(
                CampaignGroup(
                    group_id=group_id,
                    label="POTENTIAL_COORDINATION",
                    member_candidate_ids=sorted(component),
                    shared_indicator_types=shared_types,
                    links=group_links,
                    group_size=len(component),
                    highest_risk=highest_risk,
                    highest_severity=highest_sev,
                    candidate_types=cand_types,
                    evidence_completeness=avg_comp,
                )
            )

    # Identify unconnected candidates
    connected_ids = set()
    for g in groups:
        connected_ids.update(g.member_candidate_ids)

    unconnected_ids = [
        c["candidate_id"] for c in filtered_candidates if c["candidate_id"] not in connected_ids
    ]

    # Build GraphNode list
    nodes: List[GraphNode] = []
    for c in filtered_candidates:
        cid = c["candidate_id"]
        nodes.append(
            GraphNode(
                id=cid,
                label=c.get("candidate_name") or c.get("app_name") or c.get("display_name") or cid,
                brand_id=c.get("brand_id", ""),
                candidate_type=c.get("candidate_type", "social_profile"),
                platform=c.get("platform") or c.get("store") or "bluesky",
                score=c.get("score", 0),
                severity=c.get("severity", "Low"),
                classification=c.get("classification", "LOW_RISK"),
                investigation_status=c.get("investigation_status", "new"),
                is_demo_data=c.get("is_demo_data", False),
                is_synthetic=c.get("is_synthetic", False),
                source_type=c.get("source_type", "demo"),
                external_identifier=c.get("handle") or c.get("package_or_bundle_id"),
                group_id=cand_to_group_id.get(cid),
            )
        )

    # Sort groups by size descending, then highest risk descending
    groups.sort(key=lambda g: (g.group_size, g.highest_risk), reverse=True)

    is_any_synthetic = any(c.get("is_synthetic", False) for c in filtered_candidates)

    return CampaignGraphResponse(
        dataset_id=candidates[0].get("dataset_id") if candidates else None,
        brand_id=brand.get("brand_id") if brand else None,
        is_synthetic=is_any_synthetic,
        disclaimer=CAMPAIGN_DISCLAIMER,
        nodes=nodes,
        edges=edges,
        groups=groups,
        unconnected_candidate_ids=unconnected_ids,
        non_edges_documented=non_edges,
    )


def get_brand_campaign_graph(
    brand_id: Optional[str] = None,
    db_name: Optional[str] = None,
    include_official: bool = False,
) -> CampaignGraphResponse:
    """Fetch stored candidates for a brand and compute the live Campaign Graph."""
    col = get_candidates_collection(db_name)
    query: Dict[str, Any] = {}
    if brand_id:
        query["brand_id"] = brand_id

    candidates = list(col.find(query, {"_id": 0}))
    brand = get_brand(brand_id, db_name=db_name) if brand_id else None

    return build_campaign_graph(candidates, brand=brand, include_official=include_official)
