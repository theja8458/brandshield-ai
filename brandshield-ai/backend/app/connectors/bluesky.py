import logging
from typing import Any, Dict, List
from app.connectors.base import BaseConnector, ConnectorStatus, RawCandidate
from app.connectors.http_client import (
    fetch_and_hash_image_safe,
    safe_get_request,
)

logger = logging.getLogger("brandshield.connectors.bluesky")

BLUESKY_ACTOR_SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"


class BlueskyConnector(BaseConnector):
    """
    Live public connector for Bluesky social platform.
    Uses public unauthenticated XRPC actor search.
    Fixed hostname: public.api.bsky.app.
    """

    def __init__(self):
        super().__init__(
            connector_id="bluesky",
            display_name="Bluesky Public Search",
            platform="bluesky",
            mode="live",
        )

    async def health_check(self) -> ConnectorStatus:
        """Probe Bluesky public endpoint availability."""
        try:
            res = await safe_get_request(
                BLUESKY_ACTOR_SEARCH_URL,
                params={"q": "bsky", "limit": 1},
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
        Search public actors on Bluesky.
        Maps did, handle, displayName, description, avatar.
        """
        params = {
            "q": query,
            "limit": 25,
        }

        try:
            res = await safe_get_request(BLUESKY_ACTOR_SEARCH_URL, params=params)
            if res.status_code != 200:
                self.record_failure(f"Search failed with HTTP {res.status_code}", is_degraded=True)
                raise RuntimeError(f"Bluesky search returned HTTP {res.status_code}")

            data = res.json()
            self.record_success()
        except Exception as err:
            self.record_failure(str(err))
            raise

        actors = data.get("actors") or []
        candidates: List[RawCandidate] = []

        for actor in actors:
            did = actor.get("did")
            handle = (actor.get("handle") or "").strip()
            display_name = (actor.get("displayName") or handle).strip()
            if not did or not handle:
                continue

            # Stable unique candidate id based on did
            clean_did_suffix = did.replace(":", "-")
            candidate_id = f"live-soc-bsky-{clean_did_suffix}"

            profile_url = f"https://bsky.app/profile/{handle}"
            bio = actor.get("description") or ""
            avatar_url = actor.get("avatar")

            # Hash avatar if hosted on allowlisted Bluesky CDN
            image_hash, image_err = await fetch_and_hash_image_safe(avatar_url)
            evidence: Dict[str, Any] = {
                "image_status": "retrieved_and_hashed" if image_hash else (image_err or "none_provided"),
                "provenance_note": f"Ingested via Bluesky Actor Search with query '{query}'",
            }

            trimmed_raw = {
                "did": did,
                "handle": handle,
                "displayName": display_name,
                "description": bio,
                "avatar": avatar_url,
                "createdAt": actor.get("createdAt"),
            }

            cand = RawCandidate(
                candidate_id=candidate_id,
                candidate_type="social_profile",
                platform="bluesky",
                source_type="live_connector",
                connector_id=self.id,
                candidate_name=display_name,
                handle=handle,
                canonical_profile_url=profile_url,
                stable_account_id=did,
                bio=bio,
                description=bio,
                image_url=avatar_url,
                image_hash=image_hash,
                evidence=evidence,
                query_used=query,
                raw_payload=trimmed_raw,
            )
            candidates.append(cand)

        return candidates
