import logging
from typing import Any, Dict, List, Optional

from app.campaigns.graph_builder import get_brand_campaign_graph
from app.connectors import connector_manager
from app.crud.brand import get_brands_collection
from app.crud.candidate import get_candidates_collection
from app.schemas.dashboard import (
    CandidateTypeBreakdown,
    InvestigationStatusBreakdown,
    MetricDefinition,
    ProvenanceBreakdown,
)

logger = logging.getLogger("brandshield.crud.dashboard")

METRIC_DEFINITIONS: List[MetricDefinition] = [
    MetricDefinition(
        name="Monitored Brands",
        description="Number of organization brand profiles actively tracked in BrandShield AI.",
        calculation="Total records in the brands collection.",
        integrity_rule="Derived directly from registered brand profiles; zero-count if none registered.",
    ),
    MetricDefinition(
        name="Candidates Analyzed",
        description="Total social accounts and app listings evaluated across all public sources, manual entries, and test seeds.",
        calculation="Total records in the candidates collection across all classifications.",
        integrity_rule="Reflects every evaluated record with an audit timestamp and source attribution.",
    ),
    MetricDefinition(
        name="Active Potential Threats",
        description="External candidates exhibiting look-alike names, deceptive links, or impersonation signals requiring security attention.",
        calculation="Candidates where classification is not OFFICIAL_EXCLUDED and score > 0.",
        integrity_rule="Strict exclusion: Verified official assets are never counted as active threats.",
    ),
    MetricDefinition(
        name="Official Assets Excluded",
        description="Registered official brand handles, profile URLs, package IDs, and developer accounts verified and bypassed prior to scoring.",
        calculation="Candidates where classification equals OFFICIAL_EXCLUDED.",
        integrity_rule="Enforced by backend official_guard.py; these assets receive score 0 and no threat alert.",
    ),
    MetricDefinition(
        name="Identity Reviews Required",
        description="Candidates where identity signals are ambiguous or conflicting (e.g. matching publisher but unknown package, or official handle on untrusted host).",
        calculation="Candidates where classification equals REVIEW_REQUIRED.",
        integrity_rule="Flagged for manual security review; never auto-suppressed nor auto-escalated.",
    ),
    MetricDefinition(
        name="Potential Campaign Groups",
        description="Clusters of suspicious accounts/apps sharing concrete technical indicators (domains, emails, hashes).",
        calculation="Computed from shared indicator graph clustering of candidates sharing concrete observable indicators.",
        integrity_rule="Derived strictly from shared observable indicators; never inferred from name resemblance alone.",
    ),
]


async def get_dashboard_metrics(db_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes all dashboard metrics directly from MongoDB Atlas records.
    Never manufactures synthetic figures or returns ungrounded data.
    """
    brands_col = get_brands_collection(db_name)
    candidates_col = get_candidates_collection(db_name)

    monitored_brands_count = brands_col.count_documents({})
    total_candidates_analyzed = candidates_col.count_documents({})

    # Candidates by type
    social_count = candidates_col.count_documents({"candidate_type": "social_profile"})
    app_count = candidates_col.count_documents({"candidate_type": "app_listing"})

    # Official excluded count
    official_excluded = candidates_col.count_documents({"classification": "OFFICIAL_EXCLUDED"})

    # Identity reviews required
    review_required = candidates_col.count_documents({"classification": "REVIEW_REQUIRED"})

    # Active potential threats (exclude OFFICIAL_EXCLUDED, must have score > 0 or suspicious classification)
    active_threats_query = {
        "classification": {"$nin": ["OFFICIAL_EXCLUDED"]},
        "$or": [
            {"score": {"$gt": 0}},
            {"severity": {"$in": ["Critical", "High", "Medium", "Review Required"]}},
            {"classification": {"$in": ["HIGH_RISK", "SUSPICIOUS", "REVIEW_REQUIRED"]}},
        ],
    }
    active_threats_count = candidates_col.count_documents(active_threats_query)

    # Active threats by severity
    # Note: severity in candidate docs can be Critical, High, Medium, Low, Review Required
    severity_counts = {
        "Critical": candidates_col.count_documents({**active_threats_query, "severity": "Critical"}),
        "High": candidates_col.count_documents({**active_threats_query, "severity": "High"}),
        "Medium": candidates_col.count_documents({**active_threats_query, "severity": "Medium"}),
        "Low": candidates_col.count_documents({**active_threats_query, "severity": "Low"}),
        "Review Required": candidates_col.count_documents({**active_threats_query, "$or": [{"severity": "Review Required"}, {"classification": "REVIEW_REQUIRED"}]}),
    }

    # Investigation status distribution
    inv_statuses = {
        "new": candidates_col.count_documents({"investigation_status": "new"}),
        "investigating": candidates_col.count_documents({"investigation_status": "investigating"}),
        "resolved": candidates_col.count_documents({"investigation_status": "resolved"}),
        "false_positive": candidates_col.count_documents({"investigation_status": "false_positive"}),
    }

    # Provenance breakdown
    provenance = {
        "live_connector": candidates_col.count_documents({"source_type": "live_connector"}),
        "manual": candidates_col.count_documents({"source_type": "manual"}),
        "demo": candidates_col.count_documents({"source_type": "demo"}),
    }

    # Connector health summary
    connector_statuses = await connector_manager.get_all_statuses()
    connector_health = {
        "total": len(connector_statuses),
        "connectors": [s.model_dump() for s in connector_statuses],
    }

    # Recent detections (latest 10, prioritizing active threats)
    recent_cursor = (
        candidates_col.find({"classification": {"$ne": "OFFICIAL_EXCLUDED"}}, {"_id": 0})
        .sort("collected_at", -1)
        .limit(10)
    )
    recent_detections = list(recent_cursor)
    # If no non-official candidates, fallback to any recent
    if not recent_detections and total_candidates_analyzed > 0:
        recent_cursor = candidates_col.find({}, {"_id": 0}).sort("collected_at", -1).limit(10)
        recent_detections = list(recent_cursor)

    # Campaign groups calculation
    campaign_graph = get_brand_campaign_graph(db_name=db_name)
    potential_campaign_groups = len(campaign_graph.groups)

    return {
        "monitored_brands_count": monitored_brands_count,
        "total_candidates_analyzed": total_candidates_analyzed,
        "candidates_by_type": CandidateTypeBreakdown(
            social_profile=social_count,
            app_listing=app_count,
        ).model_dump(),
        "active_threats_count": active_threats_count,
        "active_threats_by_severity": severity_counts,
        "official_assets_excluded": official_excluded,
        "identity_reviews_required": review_required,
        "investigation_status_distribution": InvestigationStatusBreakdown(**inv_statuses).model_dump(),
        "provenance_breakdown": ProvenanceBreakdown(**provenance).model_dump(),
        "potential_campaign_groups": potential_campaign_groups,
        "connector_health": connector_health,
        "recent_detections": recent_detections,
        "metric_definitions": [d.model_dump() for d in METRIC_DEFINITIONS],
    }
