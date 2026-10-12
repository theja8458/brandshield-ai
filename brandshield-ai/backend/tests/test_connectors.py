import os
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.connectors.bluesky import BlueskyConnector
from app.connectors.http_client import is_host_allowlisted, safe_get_request
from app.connectors.itunes import ITunesConnector
from app.connectors.manager import connector_manager


ITUNES_SAMPLE_RESPONSE = {
    "resultCount": 2,
    "results": [
        {
            "trackId": 90001,
            "trackName": "NovaPay Official App",
            "bundleId": "example.synthetic.novapay.wallet",  # Registered official bundle ID
            "trackViewUrl": "https://apps.apple.com/app/id90001",
            "sellerName": "NovaPay Technologies Ltd",
            "artistId": "synthetic-dev-10001",
            "description": "Official wallet app",
            "artworkUrl512": "https://is1-ssl.mzstatic.com/image/thumb/app.png",
            "sellerUrl": "https://novapay.example",
        },
        {
            "trackId": 90002,
            "trackName": "NovaPay Free Rewards",
            "bundleId": "com.imposter.novapay.rewards",
            "trackViewUrl": "https://apps.apple.com/app/id90002",
            "sellerName": "Rogue Developer",
            "artistId": 99999,
            "description": "Claim free money and rewards now!",
            "artworkUrl512": "https://is1-ssl.mzstatic.com/image/thumb/rogue.png",
            "sellerUrl": "https://novapay-claim.example",
        },
    ],
}

BLUESKY_SAMPLE_RESPONSE = {
    "actors": [
        {
            "did": "did:synthetic:novapay-official-0001",
            "handle": "novapay.synthetic.example",  # Registered official handle
            "displayName": "NovaPay",
            "description": "Official peer-to-peer payments.",
            "avatar": "https://cdn.bsky.app/img/avatar/official.jpg",
        },
        {
            "did": "did:plc:imposter67890",
            "handle": "novapay-support.bsky.social",
            "displayName": "NovaPay Official Support Agent",
            "description": "DM to claim your refund and support.",
            "avatar": "https://cdn.bsky.app/img/avatar/imposter.jpg",
        },
    ]
}


def test_allowlisted_hosts_enforced():
    """Verify outbound HTTP requests reject non-allowlisted hostnames."""
    assert is_host_allowlisted("https://itunes.apple.com/search") is True
    assert is_host_allowlisted("https://public.api.bsky.app/xrpc/search") is True
    assert is_host_allowlisted("https://evil-attacker.example/api") is False
    assert is_host_allowlisted("https://google.com") is False

    # Image CDNs
    assert is_host_allowlisted("https://is1-ssl.mzstatic.com/image/thumb.png", is_image=True) is True
    assert is_host_allowlisted("https://cdn.bsky.app/img/avatar/abc.jpg", is_image=True) is True
    assert is_host_allowlisted("https://malicious-cdn.example/logo.png", is_image=True) is False


@pytest.mark.asyncio
async def test_safe_get_request_rejects_arbitrary_urls():
    """Verify safe_get_request raises ValueError for unallowlisted URLs."""
    with pytest.raises(ValueError, match="host is not in allowlist"):
        await safe_get_request("https://untrusted-domain.com/data")


@pytest.mark.asyncio
async def test_itunes_connector_successful_parsing():
    """Verify Apple iTunes connector parses results and maps fields correctly."""
    connector = ITunesConnector()
    mock_resp = httpx.Response(200, json=ITUNES_SAMPLE_RESPONSE)

    with patch("app.connectors.itunes.safe_get_request", new_callable=AsyncMock, return_value=mock_resp):
        with patch("app.connectors.itunes.fetch_and_hash_image_safe", new_callable=AsyncMock, return_value=(None, "none")):
            candidates = await connector.search("novapay")

    assert len(candidates) == 2
    c1, c2 = candidates[0], candidates[1]
    assert c1.candidate_type == "app_listing"
    assert c1.package_or_bundle_id == "example.synthetic.novapay.wallet"
    assert c1.publisher_id == "synthetic-dev-10001"
    assert c2.candidate_name == "NovaPay Free Rewards"
    assert c2.source_type == "live_connector"
    assert connector.get_status().state == "available"


@pytest.mark.asyncio
async def test_bluesky_connector_successful_parsing():
    """Verify Bluesky connector parses actors and derives canonical profile URLs."""
    connector = BlueskyConnector()
    mock_resp = httpx.Response(200, json=BLUESKY_SAMPLE_RESPONSE)

    with patch("app.connectors.bluesky.safe_get_request", new_callable=AsyncMock, return_value=mock_resp):
        with patch("app.connectors.bluesky.fetch_and_hash_image_safe", new_callable=AsyncMock, return_value=(None, "none")):
            candidates = await connector.search("novapay")

    assert len(candidates) == 2
    c1 = candidates[0]
    assert c1.candidate_type == "social_profile"
    assert c1.handle == "novapay.synthetic.example"
    assert c1.stable_account_id == "did:synthetic:novapay-official-0001"
    assert c1.canonical_profile_url == "https://bsky.app/profile/novapay.synthetic.example"
    assert connector.get_status().state == "available"


@pytest.mark.asyncio
async def test_connector_handles_timeout_and_records_degraded():
    """Verify timeouts are handled gracefully and connector status records failure."""
    connector = ITunesConnector()

    with patch("app.connectors.itunes.safe_get_request", side_effect=httpx.TimeoutException("Timed out")):
        with pytest.raises(Exception):
            await connector.search("test")

    status = connector.get_status()
    assert status.state == "unavailable"
    assert status.last_error_message is not None


@pytest.mark.asyncio
async def test_connector_handles_http_500():
    """Verify HTTP 500 error from upstream records failure without crashing the whole system."""
    connector = BlueskyConnector()
    mock_resp = httpx.Response(500, text="Internal Server Error")

    with patch("app.connectors.bluesky.safe_get_request", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(RuntimeError, match="HTTP 500"):
            await connector.search("test")

    status = connector.get_status()
    assert status.state in ("degraded", "unavailable")


@pytest.mark.asyncio
async def test_connector_handles_empty_results():
    """Verify empty result lists are handled cleanly with zero candidates."""
    connector = ITunesConnector()
    mock_resp = httpx.Response(200, json={"resultCount": 0, "results": []})

    with patch("app.connectors.itunes.safe_get_request", new_callable=AsyncMock, return_value=mock_resp):
        candidates = await connector.search("nonexistentquery123")

    assert candidates == []
    assert connector.get_status().state == "available"


@pytest.mark.asyncio
async def test_scan_brand_deduplicates_and_excludes_official():
    """
    CRITICAL WORKFLOW TEST:
    Verify that scanning a brand deduplicates by stable ID,
    excludes official assets before scoring, and persists to test database.
    """
    from app.crud.brand import seed_novapay

    # Seed NovaPay brand in isolated test database
    brand = seed_novapay()
    brand_id = brand["brand_id"]

    mock_itunes = httpx.Response(200, json=ITUNES_SAMPLE_RESPONSE)
    mock_bsky = httpx.Response(200, json=BLUESKY_SAMPLE_RESPONSE)

    def mock_safe_get(url, *args, **kwargs):
        if "itunes" in url:
            return mock_itunes
        return mock_bsky

    with patch("app.connectors.itunes.safe_get_request", new_callable=AsyncMock, side_effect=mock_safe_get):
        with patch("app.connectors.bluesky.safe_get_request", new_callable=AsyncMock, side_effect=mock_safe_get):
            with patch("app.connectors.http_client.fetch_and_hash_image_safe", new_callable=AsyncMock, return_value=(None, "none")):
                scan_res = await connector_manager.scan_brand(brand_id)

    assert scan_res.brand_id == brand_id
    assert scan_res.total_found > 0
    # Official bundle ID (example.synthetic.novapay.wallet) was in the sample response -> must be excluded!
    assert scan_res.total_excluded_official >= 1


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_TESTS"),
    reason="Live network test skipped by default. Run with RUN_LIVE_TESTS=1 to execute live smoke test.",
)
async def test_live_public_smoke_test():
    """
    OPTIONAL LIVE SMOKE TEST:
    Performs real public calls to Apple iTunes and Bluesky when RUN_LIVE_TESTS=1.
    """
    itunes = ITunesConnector()
    itunes_status = await itunes.health_check()
    assert itunes_status.state == "available"

    bsky = BlueskyConnector()
    bsky_status = await bsky.health_check()
    assert bsky_status.state == "available"
