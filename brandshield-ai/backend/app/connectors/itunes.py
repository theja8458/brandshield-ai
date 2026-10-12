import logging
from typing import Any, Dict, List
from app.connectors.base import BaseConnector, ConnectorStatus, RawCandidate
from app.connectors.http_client import (
    fetch_and_hash_image_safe,
    safe_get_request,
)

logger = logging.getLogger("brandshield.connectors.itunes")

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


class ITunesConnector(BaseConnector):
    """
    Live public connector for Apple App Store via iTunes Search API.
    Fixed hostname: itunes.apple.com.
    """

    def __init__(self):
        super().__init__(
            connector_id="apple_itunes",
            display_name="Apple App Store (iTunes API)",
            platform="apple_app_store",
            mode="live",
        )

    async def health_check(self) -> ConnectorStatus:
        """Check if Apple iTunes Search API is reachable."""
        try:
            res = await safe_get_request(
                ITUNES_SEARCH_URL,
                params={"term": "apple", "entity": "software", "limit": 1},
            )
            if res.status_code == 200:
                self.record_success()
            else:
                self.record_failure(f"Upstream returned HTTP {res.status_code}", is_degraded=True)
        except Exception as err:
            self.record_failure(f"Connection failed: {type(err).__name__}")
        return self.get_status()

    async def search(self, query: str) -> List[RawCandidate]:
        """
        Search iOS apps via iTunes API.
        Maps trackName, bundleId, trackViewUrl, sellerName, artistId, description, artworkUrl512, sellerUrl.
        """
        params = {
            "term": query,
            "entity": "software",
            "limit": 25,
        }

        try:
            res = await safe_get_request(ITUNES_SEARCH_URL, params=params)
            if res.status_code != 200:
                self.record_failure(f"Search failed with HTTP {res.status_code}", is_degraded=True)
                raise RuntimeError(f"iTunes search returned HTTP {res.status_code}")

            data = res.json()
            self.record_success()
        except Exception as err:
            self.record_failure(str(err))
            raise

        results = data.get("results") or []
        candidates: List[RawCandidate] = []

        for item in results:
            track_id = item.get("trackId")
            bundle_id = (item.get("bundleId") or "").strip()
            track_name = (item.get("trackName") or "").strip()
            if not bundle_id or not track_name:
                continue

            candidate_id = f"live-app-itunes-{track_id or bundle_id}"
            listing_url = item.get("trackViewUrl") or ""
            publisher_name = item.get("sellerName") or item.get("artistName") or ""
            publisher_id = str(item.get("artistId")) if item.get("artistId") is not None else ""
            desc = item.get("description") or ""
            artwork_url = item.get("artworkUrl512") or item.get("artworkUrl100")

            external_links = []
            if item.get("sellerUrl"):
                external_links.append(item["sellerUrl"])

            # Compute image perceptual hash from allowlisted Apple CDN
            image_hash, image_err = await fetch_and_hash_image_safe(artwork_url)
            evidence: Dict[str, Any] = {
                "image_status": "retrieved_and_hashed" if image_hash else (image_err or "none_provided"),
                "provenance_note": f"Ingested via iTunes Search API with query '{query}'",
            }

            # Trimmed raw payload for provenance
            trimmed_raw = {
                "trackId": track_id,
                "trackName": track_name,
                "bundleId": bundle_id,
                "sellerName": publisher_name,
                "artistId": publisher_id,
                "trackViewUrl": listing_url,
                "artworkUrl512": artwork_url,
                "sellerUrl": item.get("sellerUrl"),
            }

            cand = RawCandidate(
                candidate_id=candidate_id,
                candidate_type="app_listing",
                platform="apple_app_store",
                store="apple_app_store",
                source_type="live_connector",
                connector_id=self.id,
                candidate_name=track_name,
                app_name=track_name,
                package_or_bundle_id=bundle_id,
                canonical_listing_url=listing_url,
                publisher_or_developer=publisher_name,
                publisher_id=publisher_id,
                description=desc,
                external_links=external_links,
                image_url=artwork_url,
                image_hash=image_hash,
                evidence=evidence,
                query_used=query,
                raw_payload=trimmed_raw,
            )
            candidates.append(cand)

        return candidates
