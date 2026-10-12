import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pymongo.collection import Collection

from app.database import get_database
from app.schemas.brand import BrandCreate, BrandUpdate

logger = logging.getLogger("brandshield.crud.brand")


def get_brands_collection(db_name: Optional[str] = None) -> Collection:
    """Retrieve the brands collection from MongoDB."""
    db = get_database(db_name)
    return db["brands"]


def ensure_brand_indexes(db_name: Optional[str] = None) -> None:
    """Ensure appropriate indexes are set up in MongoDB."""
    col = get_brands_collection(db_name)
    try:
        col.create_index("brand_id", unique=True)
        col.create_index("name")
        col.create_index("official_domains")
        col.create_index("official_social_assets.normalized_handle")
        col.create_index("official_app_assets.package_or_bundle_id")
    except Exception as err:
        logger.warning("Failed to ensure brand indexes: %s", err)


def create_brand(brand_in: BrandCreate, db_name: Optional[str] = None) -> Dict[str, Any]:
    """Create a new brand document in MongoDB Atlas."""
    ensure_brand_indexes(db_name)
    col = get_brands_collection(db_name)

    now = datetime.now(timezone.utc).isoformat()
    brand_dict = brand_in.model_dump()

    # Generate brand_id if not present
    if not brand_dict.get("brand_id"):
        slug = brand_dict["name"].strip().lower().replace(" ", "-")
        brand_dict["brand_id"] = f"brand-{slug}-{uuid.uuid4().hex[:6]}"

    # Assign asset_ids to social and app assets if missing
    for idx, soc in enumerate(brand_dict.get("official_social_assets", [])):
        if not soc.get("asset_id"):
            soc["asset_id"] = f"asset-{brand_dict['brand_id']}-soc-{idx+1:03d}"

    for idx, app in enumerate(brand_dict.get("official_app_assets", [])):
        if not app.get("asset_id"):
            app["asset_id"] = f"asset-{brand_dict['brand_id']}-app-{idx+1:03d}"

    brand_dict["created_at"] = now
    brand_dict["updated_at"] = now

    # Remove existing MongoDB _id if present in dump
    brand_dict.pop("_id", None)

    col.insert_one(brand_dict)
    brand_dict.pop("_id", None)
    return brand_dict


def list_brands(db_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all registered brand profiles."""
    col = get_brands_collection(db_name)
    cursor = col.find({}, {"_id": 0})
    return list(cursor)


def get_brand(brand_id: str, db_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve brand by brand_id or name."""
    col = get_brands_collection(db_name)
    doc = col.find_one({"$or": [{"brand_id": brand_id}, {"name": brand_id}]}, {"_id": 0})
    return doc


def update_brand(
    brand_id: str,
    update_in: BrandUpdate,
    db_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update an existing brand profile."""
    col = get_brands_collection(db_name)
    update_dict = {k: v for k, v in update_in.model_dump().items() if v is not None}
    if not update_dict:
        return get_brand(brand_id, db_name)

    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = col.find_one_and_update(
        {"$or": [{"brand_id": brand_id}, {"name": brand_id}]},
        {"$set": update_dict},
        projection={"_id": 0},
        return_document=True,
    )
    return res


def delete_brand(brand_id: str, db_name: Optional[str] = None) -> bool:
    """Delete a brand profile."""
    col = get_brands_collection(db_name)
    res = col.delete_one({"$or": [{"brand_id": brand_id}, {"name": brand_id}]})
    return res.deleted_count > 0


def seed_novapay(db_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Explicit repeatable seed command for fictional brand NovaPay.
    Reads from novapay_synthetic_dataset/brands.json if accessible,
    or uses the verified canonical NovaPay definition.
    """
    col = get_brands_collection(db_name)

    # Attempt reading from dataset file
    candidates_paths = [
        Path("d:/BrandShield Ai/novapay_synthetic_dataset/brands.json"),
        Path("../novapay_synthetic_dataset/brands.json"),
        Path("novapay_synthetic_dataset/brands.json"),
    ]

    seed_data = None
    for p in candidates_paths:
        if p.exists():
            try:
                loaded = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(loaded, list) and len(loaded) > 0:
                    seed_data = loaded[0]
                    break
            except Exception as e:
                logger.warning("Could not read seed from %s: %e", p, e)

    if not seed_data:
        # Fallback to verified canonical definition
        seed_data = {
            "brand_id": "brand-novapay-synthetic",
            "name": "NovaPay",
            "description": "NovaPay is a fictional digital wallet and peer-to-peer payments service used only for software testing.",
            "official_website": "https://www.novapay.example",
            "official_domains": ["novapay.example"],
            "aliases": ["NovaPay Technologies"],
            "keywords": ["novapay", "nova pay", "wallet", "peer-to-peer payments"],
            "safe_list": ["Nova Pay Careers"],
            "status": "active",
            "created_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-01T00:00:00Z",
            "dataset_id": "novapay-synthetic-v1",
            "source_type": "demo",
            "is_demo_data": True,
            "is_synthetic": True,
            "official_logo": {
                "image_reference": "image_fixtures/official_novapay_logo.png",
                "image_hash": "be6ce19394469639",
                "hash_algorithm": "imagehash.phash(hash_size=8)",
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
                    "icon_reference": "image_fixtures/official_novapay_app_icon.png",
                    "icon_hash": "9ea4295bea4eea11",
                }
            ],
        }

    # Clean _id
    seed_data.pop("_id", None)
    seed_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Upsert by brand_id
    col.update_one(
        {"brand_id": seed_data["brand_id"]},
        {"$set": seed_data},
        upsert=True,
    )

    doc = col.find_one({"brand_id": seed_data["brand_id"]}, {"_id": 0})
    return doc
