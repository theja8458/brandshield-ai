import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pymongo import UpdateOne
from pymongo.collection import Collection

from app.crud.brand import get_brand
from app.database import get_database
from app.detection.engine import evaluate_candidate
from app.schemas.candidate import AppManualCreate, CandidateManualCreate, CandidateStatusUpdate
from app.services.official_guard import ExclusionStatus, evaluate_official_status

logger = logging.getLogger("brandshield.crud.candidate")


def get_candidates_collection(db_name: Optional[str] = None) -> Collection:
    db = get_database(db_name)
    return db["candidates"]


_ensured_candidate_dbs = set()


def ensure_candidate_indexes(db_name: Optional[str] = None) -> None:
    key = db_name or "default"
    if key in _ensured_candidate_dbs:
        return
    col = get_candidates_collection(db_name)
    try:
        col.create_index("candidate_id", unique=True)
        col.create_index("brand_id")
        col.create_index("candidate_type")
        col.create_index("platform")
        col.create_index("severity")
        col.create_index("classification")
        col.create_index("investigation_status")
        col.create_index("source_type")
        col.create_index("collected_at")
        _ensured_candidate_dbs.add(key)
    except Exception as err:
        logger.warning("Failed to ensure candidate indexes: %s", err)


def list_candidates(
    brand_id: Optional[str] = None,
    candidate_type: Optional[str] = None,
    platform: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    search: Optional[str] = None,
    include_official: bool = False,
    page: int = 1,
    limit: int = 50,
    db_name: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    List candidates with bounded pagination and multi-field filtering.
    By default, official excluded assets are filtered out from active alert lists.
    """
    ensure_candidate_indexes(db_name)
    col = get_candidates_collection(db_name)

    query: Dict[str, Any] = {}
    if brand_id:
        query["brand_id"] = brand_id
    if candidate_type:
        query["candidate_type"] = candidate_type
    if severity:
        query["severity"] = severity
    if status:
        query["investigation_status"] = status
    if source_type:
        query["source_type"] = source_type

    if not include_official:
        query["classification"] = {"$ne": "OFFICIAL_EXCLUDED"}

    conditions: List[Dict[str, Any]] = []
    if platform:
        conditions.append({"$or": [{"platform": platform}, {"store": platform}]})

    if search:
        search_rgx = {"$regex": search.strip(), "$options": "i"}
        conditions.append({
            "$or": [
                {"candidate_name": search_rgx},
                {"handle": search_rgx},
                {"display_name": search_rgx},
                {"app_name": search_rgx},
                {"package_or_bundle_id": search_rgx},
                {"publisher_or_developer": search_rgx},
                {"description": search_rgx},
            ]
        })

    if conditions:
        if len(conditions) == 1:
            query.update(conditions[0])
        else:
            query["$and"] = conditions

    # Bounded limits
    safe_limit = max(1, min(limit, 100))
    skip = (max(1, page) - 1) * safe_limit

    total = col.count_documents(query)
    cursor = col.find(query, {"_id": 0}).sort("collected_at", -1).skip(skip).limit(safe_limit)
    items = list(cursor)
    return items, total


def get_candidate(candidate_id: str, db_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    col = get_candidates_collection(db_name)
    doc = col.find_one({"candidate_id": candidate_id}, {"_id": 0})
    return doc


def update_candidate_status(
    candidate_id: str,
    update_in: CandidateStatusUpdate,
    db_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    col = get_candidates_collection(db_name)
    now = datetime.now(timezone.utc).isoformat()

    update_fields: Dict[str, Any] = {
        "investigation_status": update_in.status.value,
        "status_updated_at": now,
    }
    if update_in.notes is not None:
        update_fields["status_notes"] = update_in.notes

    history_entry = {
        "status": update_in.status.value,
        "timestamp": now,
        "notes": update_in.notes or "",
    }

    res = col.find_one_and_update(
        {"candidate_id": candidate_id},
        {
            "$set": update_fields,
            "$push": {"investigation_history": history_entry},
        },
        projection={"_id": 0},
        return_document=True,
    )
    return res


def get_candidate_evidence(candidate_id: str, db_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve comprehensive evidentiary trail and audit history for a candidate."""
    cand = get_candidate(candidate_id, db_name=db_name)
    if not cand:
        return None

    # Compile external identifiers
    ext_ids = {}
    if cand.get("handle"):
        ext_ids["handle"] = cand["handle"]
    if cand.get("stable_account_id"):
        ext_ids["stable_account_id"] = cand["stable_account_id"]
    if cand.get("canonical_profile_url"):
        ext_ids["canonical_profile_url"] = cand["canonical_profile_url"]
    if cand.get("package_or_bundle_id"):
        ext_ids["package_or_bundle_id"] = cand["package_or_bundle_id"]
    if cand.get("publisher_id"):
        ext_ids["publisher_id"] = cand["publisher_id"]
    if cand.get("publisher_or_developer"):
        ext_ids["publisher_or_developer"] = cand["publisher_or_developer"]
    if cand.get("canonical_listing_url"):
        ext_ids["canonical_listing_url"] = cand["canonical_listing_url"]

    off_reason = None
    if cand.get("classification") == "OFFICIAL_EXCLUDED":
        off_reason = cand.get("evidence", {}).get("provenance_note") or "Excluded prior to threat scoring as registered official asset."

    return {
        "candidate_id": cand["candidate_id"],
        "brand_id": cand.get("brand_id", ""),
        "candidate_name": cand.get("candidate_name") or cand.get("app_name") or cand.get("display_name") or "",
        "candidate_type": cand.get("candidate_type", "social_profile"),
        "platform": cand.get("platform") or cand.get("store") or "bluesky",
        "source_type": cand.get("source_type", "demo"),
        "connector_id": cand.get("connector_id"),
        "is_demo_data": cand.get("is_demo_data", False),
        "is_synthetic": cand.get("is_synthetic", False),
        "collected_at": cand.get("collected_at"),
        "analyzed_at": cand.get("analyzed_at"),
        "query_used": cand.get("query_used"),
        "score": cand.get("score", 0),
        "severity": cand.get("severity", "Low"),
        "classification": cand.get("classification", "LOW_RISK"),
        "classification_reason": cand.get("evidence", {}).get("reason") or f"Assessed as {cand.get('classification')}.",
        "signals": cand.get("signals", []),
        "evidence": cand.get("evidence", {}),
        "missing_evidence": cand.get("missing_evidence", []),
        "evidence_completeness": cand.get("evidence_completeness", 1.0),
        "official_exclusion_reason": off_reason,
        "investigation_status": cand.get("investigation_status", "new"),
        "status_updated_at": cand.get("status_updated_at"),
        "status_notes": cand.get("status_notes"),
        "investigation_history": cand.get("investigation_history", []),
        "external_identifiers": ext_ids,
    }


def create_manual_candidate(
    brand_id: str,
    manual_in: CandidateManualCreate,
    db_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a manual candidate, evaluate via official guard & engine, and persist."""
    ensure_candidate_indexes(db_name)
    col = get_candidates_collection(db_name)

    brand = get_brand(brand_id, db_name=db_name)
    if not brand:
        raise ValueError(f"Brand '{brand_id}' not found.")

    now = datetime.now(timezone.utc).isoformat()
    cid = f"manual-soc-{uuid.uuid4().hex[:8]}"

    cand_dict: Dict[str, Any] = {
        "candidate_id": cid,
        "brand_id": brand_id,
        "candidate_type": manual_in.candidate_type,
        "platform": manual_in.platform,
        "source_type": "manual",
        "connector_id": "manual_submission",
        "is_demo_data": False,
        "is_synthetic": False,
        "candidate_name": manual_in.display_name,
        "display_name": manual_in.display_name,
        "handle": manual_in.handle.lstrip("@"),
        "canonical_profile_url": manual_in.canonical_profile_url,
        "stable_account_id": manual_in.stable_account_id,
        "bio": manual_in.bio or manual_in.description or "",
        "description": manual_in.description or manual_in.bio or "",
        "external_links": manual_in.external_links,
        "image_url": manual_in.image_url,
        "investigation_status": "new",
        "collected_at": now,
        "analyzed_at": now,
        "evidence": {
            "provenance_note": "Manually submitted candidate for threat analysis",
        },
    }

    # Run official guard BEFORE scoring
    official_eval = evaluate_official_status(brand, cand_dict)
    if official_eval.status == ExclusionStatus.OFFICIAL_EXCLUDED:
        cand_dict["score"] = 0
        cand_dict["severity"] = "Low"
        cand_dict["classification"] = "OFFICIAL_EXCLUDED"
        cand_dict["is_excluded_from_scoring"] = True
        cand_dict["signals"] = []
        cand_dict["investigation_status"] = "resolved"
        cand_dict["missing_evidence"] = []
    else:
        eval_res = evaluate_candidate(brand, cand_dict)
        cand_dict["score"] = eval_res.score
        cand_dict["severity"] = eval_res.severity
        cand_dict["classification"] = eval_res.classification
        cand_dict["signals"] = [s.model_dump() for s in eval_res.signals]
        cand_dict["missing_evidence"] = eval_res.missing_evidence
        cand_dict["evidence_completeness"] = eval_res.evidence_completeness

    col.insert_one(cand_dict)
    cand_dict.pop("_id", None)
    return cand_dict


def seed_social_demo_candidates(brand_id: str, db_name: Optional[str] = None) -> int:
    """
    Explicit repeatable seed endpoint for social demo candidates from candidates.json.
    Pulls the 25 social records, evaluates official guard and detection engine,
    and upserts into MongoDB Atlas.
    """
    ensure_candidate_indexes(db_name)
    col = get_candidates_collection(db_name)

    brand = get_brand(brand_id, db_name=db_name)
    if not brand:
        raise ValueError(f"Brand '{brand_id}' not found.")

    candidates_paths = [
        Path("d:/BrandShield Ai/novapay_synthetic_dataset/candidates.json"),
        Path("../novapay_synthetic_dataset/candidates.json"),
        Path("novapay_synthetic_dataset/candidates.json"),
    ]

    loaded_raw = []
    for p in candidates_paths:
        if p.exists():
            try:
                loaded_raw = json.loads(p.read_text(encoding="utf-8"))
                break
            except Exception as e:
                logger.warning("Could not read candidates from %s: %s", p, e)

    # Filter to social candidates only
    social_candidates = [
        c for c in loaded_raw if c.get("candidate_type") == "social_profile"
    ]

    # Fallback built-in demo cases if file is unavailable
    if not social_candidates:
        social_candidates = [
            {
                "candidate_id": "SYN-SOC-016",
                "candidate_type": "social_profile",
                "platform": "bluesky",
                "candidate_name": "NovaPay",
                "handle": "novapay.synthetic.example",
                "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay.synthetic.example",
                "stable_account_id": "did:synthetic:novapay-official-0001",
                "bio": "Official NovaPay digital payments account.",
            },
            {
                "candidate_id": "SYN-SOC-001",
                "candidate_type": "social_profile",
                "platform": "bluesky",
                "candidate_name": "N0vaPay Support",
                "handle": "n0vapay-support.synthetic.example",
                "canonical_profile_url": "https://bsky.synthetic.example/profile/n0vapay-support",
                "bio": "Official support agent here! DM to claim refund and support.",
            },
            {
                "candidate_id": "SYN-SOC-002",
                "candidate_type": "social_profile",
                "platform": "bluesky",
                "candidate_name": "Nova Pay Official",
                "handle": "novapay-official.synthetic.example",
                "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay-official",
                "bio": "NovaPay official updates and rewards channel.",
            },
            {
                "candidate_id": "SYN-SOC-003",
                "candidate_type": "social_profile",
                "platform": "bluesky",
                "candidate_name": "NovaPay",
                "handle": "novapay-online.synthetic.example",
                "canonical_profile_url": "https://bsky.synthetic.example/profile/novapay-online",
                "external_links": ["https://novapay-login.example"],
                "bio": "Login to your wallet online.",
            },
            {
                "candidate_id": "SYN-SOC-011",
                "candidate_type": "social_profile",
                "platform": "bluesky",
                "candidate_name": "NovaPay Rogue Desk",
                "handle": "rogue-novapay.synthetic.example",
                "canonical_profile_url": "https://bsky.synthetic.example/profile/rogue-novapay",
                "stable_account_id": "did:synthetic:novapay-official-0001",  # Identity conflict
                "bio": "Claims official DID with conflicting handle.",
            },
            {
                "candidate_id": "SYN-SOC-017",
                "candidate_type": "social_profile",
                "platform": "bluesky",
                "candidate_name": "Nova Payments Ltd",
                "handle": "novapayments.synthetic.example",
                "canonical_profile_url": "https://bsky.synthetic.example/profile/novapayments",
                "bio": "Corporate advisory firm based in London.",
            },
        ]

    now = datetime.now(timezone.utc).isoformat()
    bulk_ops = []

    for item in social_candidates:
        cand_dict = dict(item)
        cand_dict["brand_id"] = brand_id
        cand_dict["source_type"] = "demo"
        cand_dict["connector_id"] = "demo_synthetic_seed"
        cand_dict["is_demo_data"] = True
        cand_dict["is_synthetic"] = True
        cand_dict["investigation_status"] = "new"
        cand_dict["collected_at"] = cand_dict.get("collected_at") or now
        cand_dict["analyzed_at"] = now

        # Run official guard BEFORE scoring
        official_eval = evaluate_official_status(brand, cand_dict)
        if official_eval.status == ExclusionStatus.OFFICIAL_EXCLUDED:
            cand_dict["score"] = 0
            cand_dict["severity"] = "Low"
            cand_dict["classification"] = "OFFICIAL_EXCLUDED"
            cand_dict["is_excluded_from_scoring"] = True
            cand_dict["signals"] = []
            cand_dict["investigation_status"] = "resolved"
        else:
            eval_res = evaluate_candidate(brand, cand_dict)
            cand_dict["score"] = eval_res.score
            cand_dict["severity"] = eval_res.severity
            cand_dict["classification"] = eval_res.classification
            cand_dict["signals"] = [s.model_dump() for s in eval_res.signals]
            cand_dict["missing_evidence"] = eval_res.missing_evidence
            cand_dict["evidence_completeness"] = eval_res.evidence_completeness

        bulk_ops.append(
            UpdateOne(
                {"candidate_id": cand_dict["candidate_id"]},
                {"$set": cand_dict},
                upsert=True,
            )
        )

    if bulk_ops:
        col.bulk_write(bulk_ops, ordered=False)

    return len(bulk_ops)


def submit_manual_app_candidate(
    brand_id: str,
    manual_in: AppManualCreate,
    db_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a manual mobile app candidate, evaluate via official guard & engine, and persist."""
    ensure_candidate_indexes(db_name)
    col = get_candidates_collection(db_name)

    brand = get_brand(brand_id, db_name=db_name)
    if not brand:
        raise ValueError(f"Brand '{brand_id}' not found.")

    now = datetime.now(timezone.utc).isoformat()
    cid = f"manual-app-{uuid.uuid4().hex[:8]}"

    cand_dict: Dict[str, Any] = {
        "candidate_id": cid,
        "brand_id": brand_id,
        "candidate_type": "app_listing",
        "platform": manual_in.store or "apple_app_store",
        "store": manual_in.store or "apple_app_store",
        "source_type": "manual",
        "connector_id": "manual_submission",
        "is_demo_data": False,
        "is_synthetic": False,
        "candidate_name": manual_in.app_name,
        "app_name": manual_in.app_name,
        "package_or_bundle_id": manual_in.package_or_bundle_id,
        "canonical_listing_url": manual_in.canonical_listing_url,
        "publisher_or_developer": manual_in.publisher_or_developer,
        "publisher_id": manual_in.publisher_id,
        "description": manual_in.description or "",
        "external_links": manual_in.external_links,
        "image_url": manual_in.image_url,
        "investigation_status": "new",
        "collected_at": now,
        "analyzed_at": now,
        "evidence": {
            "provenance_note": "Manually submitted app listing for threat analysis",
        },
    }

    # Run official guard BEFORE scoring
    official_eval = evaluate_official_status(brand, cand_dict)
    if official_eval.status == ExclusionStatus.OFFICIAL_EXCLUDED:
        cand_dict["score"] = 0
        cand_dict["severity"] = "Low"
        cand_dict["classification"] = "OFFICIAL_EXCLUDED"
        cand_dict["is_excluded_from_scoring"] = True
        cand_dict["signals"] = []
        cand_dict["investigation_status"] = "resolved"
    else:
        eval_res = evaluate_candidate(brand, cand_dict)
        cand_dict["score"] = eval_res.score
        cand_dict["severity"] = eval_res.severity
        cand_dict["classification"] = eval_res.classification
        cand_dict["signals"] = [s.model_dump() for s in eval_res.signals]
        cand_dict["missing_evidence"] = eval_res.missing_evidence
        cand_dict["evidence_completeness"] = eval_res.evidence_completeness

    col.update_one(
        {"candidate_id": cand_dict["candidate_id"]},
        {"$set": cand_dict},
        upsert=True,
    )

    doc = col.find_one({"candidate_id": cand_dict["candidate_id"]}, {"_id": 0})
    return doc


def seed_app_demo_candidates(brand_id: str, db_name: Optional[str] = None) -> int:
    """
    Seed repeatable synthetic mobile app candidates for demonstration and testing.
    Pulls from novapay_synthetic_dataset/candidates.json where candidate_type == 'app_listing'.
    Applies the official guard before scoring.
    """
    ensure_candidate_indexes(db_name)
    col = get_candidates_collection(db_name)

    brand = get_brand(brand_id, db_name=db_name)
    if not brand:
        raise ValueError(f"Brand '{brand_id}' not found.")

    candidates_paths = [
        Path("d:/BrandShield Ai/novapay_synthetic_dataset/candidates.json"),
        Path("../../novapay_synthetic_dataset/candidates.json"),
        Path("../novapay_synthetic_dataset/candidates.json"),
        Path("novapay_synthetic_dataset/candidates.json"),
    ]

    app_candidates = []
    for p in candidates_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    all_candidates = json.load(f)
                    app_candidates = [
                        c for c in all_candidates
                        if c.get("candidate_type") == "app_listing"
                    ]
                    if app_candidates:
                        break
            except Exception as err:
                logger.warning(f"Failed to read synthetic app dataset from {p}: {err}")

    if not app_candidates:
        # Fallback minimal app dataset fixtures if file missing
        app_candidates = [
            {
                "candidate_id": "SYN-APP-001",
                "candidate_type": "app_listing",
                "platform": "apple_app_store",
                "store": "apple_app_store",
                "candidate_name": "N0vaPay Wallet",
                "app_name": "N0vaPay Wallet",
                "package_or_bundle_id": "example.synthetic.n0vapaywallet",
                "publisher_or_developer": "Nova Wallet Services",
                "publisher_id": "synthetic-dev-77001",
                "canonical_listing_url": "https://appstore.synthetic.example/app/n0vapay-wallet/id9000010001",
                "description": "Digital wallet and peer-to-peer payments service.",
            },
            {
                "candidate_id": "SYN-APP-004",
                "candidate_type": "app_listing",
                "platform": "apple_app_store",
                "store": "apple_app_store",
                "candidate_name": "Nova Pay Official",
                "app_name": "Nova Pay Official",
                "package_or_bundle_id": "com.novapay.app",
                "publisher_or_developer": "NovaPay Inc.",
                "publisher_id": "synthetic-dev-10001",
                "canonical_listing_url": "https://apps.apple.com/app/novapay-official/id123456789",
                "description": "Official NovaPay mobile wallet and payments application.",
            },
            {
                "candidate_id": "SYN-APP-013",
                "candidate_type": "app_listing",
                "platform": "apple_app_store",
                "store": "apple_app_store",
                "candidate_name": "NovaPay Rogue Token",
                "app_name": "NovaPay Rogue Token",
                "package_or_bundle_id": "com.novapay.app",
                "publisher_or_developer": "Rogue Developer Inc.",
                "publisher_id": "synthetic-dev-99999",
                "canonical_listing_url": "https://apps.apple.com/app/novapay-rogue/id999999999",
                "description": "2FA Authenticator token generator for NovaPay.",
            },
        ]

    now = datetime.now(timezone.utc).isoformat()
    bulk_ops = []

    for item in app_candidates:
        cand_dict = dict(item)
        cand_dict["brand_id"] = brand_id
        cand_dict["candidate_type"] = "app_listing"
        cand_dict["platform"] = cand_dict.get("platform") or cand_dict.get("store") or "apple_app_store"
        cand_dict["store"] = cand_dict.get("store") or "apple_app_store"
        cand_dict["source_type"] = "demo"
        cand_dict["connector_id"] = "demo_synthetic_seed"
        cand_dict["is_demo_data"] = True
        cand_dict["is_synthetic"] = True
        cand_dict["investigation_status"] = "new"
        cand_dict["collected_at"] = cand_dict.get("collected_at") or now
        cand_dict["analyzed_at"] = now

        # Run official guard BEFORE scoring
        official_eval = evaluate_official_status(brand, cand_dict)
        if official_eval.status == ExclusionStatus.OFFICIAL_EXCLUDED:
            cand_dict["score"] = 0
            cand_dict["severity"] = "Low"
            cand_dict["classification"] = "OFFICIAL_EXCLUDED"
            cand_dict["is_excluded_from_scoring"] = True
            cand_dict["signals"] = []
            cand_dict["investigation_status"] = "resolved"
        else:
            eval_res = evaluate_candidate(brand, cand_dict)
            cand_dict["score"] = eval_res.score
            cand_dict["severity"] = eval_res.severity
            cand_dict["classification"] = eval_res.classification
            cand_dict["signals"] = [s.model_dump() for s in eval_res.signals]
            cand_dict["missing_evidence"] = eval_res.missing_evidence
            cand_dict["evidence_completeness"] = eval_res.evidence_completeness

        bulk_ops.append(
            UpdateOne(
                {"candidate_id": cand_dict["candidate_id"]},
                {"$set": cand_dict},
                upsert=True,
            )
        )

    if bulk_ops:
        col.bulk_write(bulk_ops, ordered=False)

    return len(bulk_ops)
