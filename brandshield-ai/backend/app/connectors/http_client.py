import asyncio
import fnmatch
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse
import httpx

from app.services.image_hasher import compute_image_phash

logger = logging.getLogger("brandshield.connectors.http")

HTTP_TIMEOUT_SECONDS = 8.0
MAX_RETRIES = 2
MAX_RESPONSE_SIZE = 2 * 1024 * 1024  # 2MB

# Fixed allowlisted hostnames (never fetch arbitrary user URLs)
ALLOWLISTED_API_HOSTS = {
    "itunes.apple.com",
    "public.api.bsky.app",
}

ALLOWLISTED_IMAGE_HOST_PATTERNS = [
    "*.mzstatic.com",
    "mzstatic.com",
    "cdn.bsky.app",
]


def is_host_allowlisted(url: str, is_image: bool = False) -> bool:
    """Verify URL hostname belongs strictly to the allowlisted domains."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False

        if not is_image:
            return hostname in ALLOWLISTED_API_HOSTS

        # Image host checking against allowed CDN patterns
        for pattern in ALLOWLISTED_IMAGE_HOST_PATTERNS:
            if fnmatch.fnmatch(hostname, pattern):
                return True
        return False
    except Exception:
        return False


async def safe_get_request(
    url: str,
    params: Optional[dict] = None,
    is_image: bool = False,
) -> httpx.Response:
    """
    Perform safe HTTP GET with bounded timeout, allowlist verification, and retry backoff.
    """
    if not is_host_allowlisted(url, is_image=is_image):
        raise ValueError(f"Outbound request rejected: host is not in allowlist for '{url}'")

    last_exception: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers={"User-Agent": "BrandShield-AI-DRP-Bot/1.0 (+https://brandshield.internal)"},
            ) as client:
                response = await client.get(url, params=params)

                # Check response size limit
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                    raise ValueError(f"Upstream response exceeded size limit of {MAX_RESPONSE_SIZE} bytes")

                # If 5xx server error, retry with backoff
                if response.status_code >= 500 and attempt < MAX_RETRIES:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue

                return response
        except (httpx.TimeoutException, httpx.NetworkError) as err:
            last_exception = err
            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            break
        except Exception as err:
            raise

    if last_exception:
        raise last_exception
    raise RuntimeError("Request failed after retries")


async def fetch_and_hash_image_safe(image_url: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely download image from allowlisted host and compute 64-bit pHash.
    Returns (hex_phash, error_reason). NEVER crashes if fetch fails.
    """
    if not image_url:
        return None, "none_provided"

    if not is_host_allowlisted(image_url, is_image=True):
        return None, "host_not_allowlisted"

    try:
        res = await safe_get_request(image_url, is_image=True)
        if res.status_code != 200:
            return None, f"http_status_{res.status_code}"

        content_type = res.headers.get("content-type", "").lower()
        if not any(t in content_type for t in ["image/jpeg", "image/png", "image/webp", "image/"]):
            return None, "invalid_content_type"

        image_bytes = res.content
        if len(image_bytes) > MAX_RESPONSE_SIZE:
            return None, "image_size_exceeded"

        phash_str, _ = compute_image_phash(image_bytes)
        return phash_str, None
    except Exception as err:
        logger.info("Image fetch or hash failed for %s: %s", image_url, type(err).__name__)
        return None, f"fetch_failed_{type(err).__name__}"
