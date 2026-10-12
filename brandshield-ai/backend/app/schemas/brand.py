import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class AssetPlatform(str, Enum):
    BLUESKY = "bluesky"
    TWITTER_X = "x"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    OTHER = "other"


class AppStore(str, Enum):
    APPLE_APP_STORE = "apple_app_store"
    GOOGLE_PLAY = "google_play"
    OTHER = "other"


def normalize_domain(domain_str: str) -> str:
    """Normalize domain: lower-case, remove protocol/path/www, and trim."""
    d = domain_str.strip().lower()
    # Strip protocol if user pasted a full URL
    d = re.sub(r"^https?://", "", d)
    # Strip path or trailing slash
    d = d.split("/")[0].split(":")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def validate_domain_format(domain_str: str) -> bool:
    """Validate RFC-compliant domain name format."""
    normalized = normalize_domain(domain_str)
    # Simple regex for valid host/domain name with dot
    pattern = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
    return bool(re.match(pattern, normalized))


class OfficialSocialAsset(BaseModel):
    asset_id: Optional[str] = Field(default=None, description="Unique asset ID")
    platform: str = Field(..., description="Platform: bluesky, x, etc.")
    display_name: str = Field(..., min_length=1, max_length=100)
    canonical_profile_url: str = Field(..., description="Canonical profile URL")
    normalized_handle: str = Field(..., min_length=1, description="Handle without leading @")
    stable_account_id: Optional[str] = Field(default=None, description="Platform stable ID (e.g. did:plc:...)")

    @field_validator("normalized_handle")
    @classmethod
    def clean_handle(cls, v: str) -> str:
        cleaned = v.strip().lstrip("@").lower()
        if not cleaned:
            raise ValueError("Handle cannot be empty")
        return cleaned

    @field_validator("canonical_profile_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v_clean = v.strip()
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            raise ValueError("Canonical profile URL must start with http:// or https://")
        return v_clean


class OfficialAppAsset(BaseModel):
    asset_id: Optional[str] = Field(default=None, description="Unique asset ID")
    store: str = Field(..., description="Store: apple_app_store, google_play")
    app_name: str = Field(..., min_length=1, max_length=100)
    canonical_listing_url: str = Field(..., description="Store listing URL")
    package_or_bundle_id: str = Field(..., min_length=2, description="e.g. com.brand.app or example.synthetic.novapay.wallet")
    trusted_publisher_name: str = Field(..., min_length=1)
    trusted_publisher_id: Optional[str] = Field(default=None, description="Stable developer/seller account ID")
    icon_reference: Optional[str] = Field(default=None)
    icon_hash: Optional[str] = Field(default=None, description="64-bit hexadecimal pHash")

    @field_validator("canonical_listing_url")
    @classmethod
    def validate_listing_url(cls, v: str) -> str:
        v_clean = v.strip()
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            raise ValueError("Canonical listing URL must start with http:// or https://")
        return v_clean

    @field_validator("package_or_bundle_id")
    @classmethod
    def clean_bundle_id(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if len(cleaned) < 3:
            raise ValueError("Package or bundle ID must be at least 3 characters")
        return cleaned


class OfficialLogo(BaseModel):
    image_reference: Optional[str] = None
    image_hash: str = Field(..., description="Hexadecimal perceptual hash")
    hash_algorithm: str = Field(default="imagehash.phash(hash_size=8)")


class BrandCreate(BaseModel):
    brand_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., max_length=1000)
    official_website: str = Field(..., description="Primary official website URL")
    official_domains: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    safe_list: List[str] = Field(default_factory=list, description="Known legitimate variants that must never be scored as threats")
    official_logo: Optional[OfficialLogo] = None
    official_social_assets: List[OfficialSocialAsset] = Field(default_factory=list)
    official_app_assets: List[OfficialAppAsset] = Field(default_factory=list)
    status: str = Field(default="active")
    dataset_id: Optional[str] = None
    source_type: str = Field(default="manual")
    is_demo_data: bool = Field(default=False)
    is_synthetic: bool = Field(default=False)

    @field_validator("official_website")
    @classmethod
    def validate_website(cls, v: str) -> str:
        v_clean = v.strip()
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            raise ValueError("Official website must start with http:// or https://")
        return v_clean

    @field_validator("official_domains")
    @classmethod
    def validate_domains(cls, domains: List[str]) -> List[str]:
        cleaned = []
        for d in domains:
            norm = normalize_domain(d)
            if not validate_domain_format(norm):
                raise ValueError(f"Invalid domain format: '{d}'")
            if norm not in cleaned:
                cleaned.append(norm)
        return cleaned

    @model_validator(mode="after")
    def validate_unique_assets(self) -> "BrandCreate":
        # Validate unique handles per platform
        social_seen = set()
        for asset in self.official_social_assets:
            key = (asset.platform.lower(), asset.normalized_handle.lower())
            if key in social_seen:
                raise ValueError(f"Duplicate official social asset registered: {asset.platform} handle '{asset.normalized_handle}'")
            social_seen.add(key)

        # Validate unique package IDs per store
        app_seen = set()
        for app in self.official_app_assets:
            key = (app.store.lower(), app.package_or_bundle_id.lower())
            if key in app_seen:
                raise ValueError(f"Duplicate official app asset registered: {app.store} package '{app.package_or_bundle_id}'")
            app_seen.add(key)

        return self


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    official_website: Optional[str] = None
    official_domains: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    safe_list: Optional[List[str]] = None
    official_logo: Optional[OfficialLogo] = None
    official_social_assets: Optional[List[OfficialSocialAsset]] = None
    official_app_assets: Optional[List[OfficialAppAsset]] = None
    status: Optional[str] = None


class BrandResponse(BrandCreate):
    brand_id: str
    created_at: str
    updated_at: str
