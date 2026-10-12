# BrandShield AI — Data Sources & Public Connectors

This document details the public ingestion sources, endpoints, allowlisted network boundaries, rate limits, and verification instructions for BrandShield AI.

---

## 1. Implemented Live Public Connectors

### Apple iTunes Search API (Mobile Apps)
* **Target Endpoint**: `https://itunes.apple.com/search`
* **Entity**: `software` (iOS / iPadOS applications)
* **Allowlisted Host**: `itunes.apple.com`
* **Allowlisted Image CDN**: `*.mzstatic.com`
* **Query Parameters**:
  * `term`: Target brand name or search token
  * `entity`: `software`
  * `limit`: Up to 25 results
* **Field Mapping**:
  * `trackName` $\to$ `app_name`, `candidate_name`
  * `bundleId` $\to$ `package_or_bundle_id` (e.g. `com.company.app`)
  * `trackViewUrl` $\to$ `canonical_listing_url`
  * `sellerName` $\to$ `publisher_or_developer`
  * `artistId` $\to$ `publisher_id` (numeric developer identifier)
  * `description` $\to$ `description`
  * `artworkUrl512` $\to$ `image_url` (used for perceptual hash comparison)
  * `sellerUrl` $\to$ `external_links`
* **Usage Terms & Rate Limits**:
  * Public, unauthenticated API. Apple applies an approximate rate limit of ~20 calls per minute.
  * Connectors apply an 8.0s timeout and a maximum of 2 exponential backoff retries.

### Bluesky Public Actor Search (Social Profiles)
* **Target Endpoint**: `https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors`
* **Protocol**: AT Protocol public XRPC query
* **Allowlisted Host**: `public.api.bsky.app`
* **Allowlisted Image CDN**: `cdn.bsky.app`
* **Query Parameters**:
  * `q`: Search string (handle prefix or display name token)
  * `limit`: Up to 25 results
* **Field Mapping**:
  * `did` $\to$ `stable_account_id` (decentralized identifier, e.g. `did:plc:...`)
  * `handle` $\to$ `handle` (e.g. `user.bsky.social`)
  * `displayName` $\to$ `display_name`, `candidate_name`
  * `description` $\to$ `bio`, `description`
  * `avatar` $\to$ `image_url` (used for perceptual hash comparison)
  * Canonical profile URL derived as `https://bsky.app/profile/{handle}`
* **Usage Terms & Rate Limits**:
  * Public unauthenticated endpoint. Bluesky rate limit is approximately 300 requests per 5 minutes per IP.

---

## 2. Ingestion Guardrails & Safety Architecture

1. **Fixed Hostname Allowlisting**:
   Outbound requests are strictly limited to `itunes.apple.com` and `public.api.bsky.app`. User-supplied or candidate-supplied arbitrary URLs are never requested server-side.
2. **Response Boundaries**:
   * Timeout bounded to **8.0 seconds**.
   * Upstream response payload size bounded to **2 MB**.
   * Max 2 retries with exponential backoff on network errors or 5xx responses.
3. **Graceful Degradation**:
   If one connector experiences an upstream timeout or outage, BrandShield AI marks only that specific connector as degraded or unavailable and continues processing results from available sources. **The system never substitutes fake synthetic data during a live failure.**
4. **Deduplication & Provenance**:
   Candidates are deduplicated by stable platform identifiers (`did` for Bluesky; `bundleId` or `trackId` for Apple iTunes). Every record records `source_type="live_connector"` and the query token used.
5. **Official-Asset Safety Guard**:
   All retrieved candidates are evaluated against the registered official assets *before* scoring. Confirmed official matches are marked `OFFICIAL_EXCLUDED` with an auditable explanation and never trigger alerts.

---

## 3. Prototype & Demo Modes

* **Repeatable Synthetic Seed (`demo_synthetic_seed`)**:
  * Pre-generated benchmark dataset (`novapay-synthetic-v1`) based on fictional digital wallet brand **NovaPay**.
  * Used for offline verification, evaluation against `ground_truth.csv`, and reproducible hackathon judging.
  * Explicitly tagged `source_type="demo"` and `is_demo_data=true`.
* **Manual Candidate Submission (`manual_analyst_entry`)**:
  * Enables security analysts to submit candidate metadata directly for risk scoring and campaign grouping.
  * Explicitly tagged `source_type="manual"`.

---

## 4. Platform Exclusions & Future Roadmap

> [!NOTE]
> **Google Play Store & Other Networks**:
> Currently, Google Play does not offer an official, unauthenticated public search REST API (requiring OAuth service accounts or web scraping). In adherence to hackathon safety and terms of service, Google Play, Instagram, and X scraping are not implemented in this prototype and are reserved for future enterprise connector expansion.

---

## 5. Verification Commands (Manual Smoke Testing)

Verify Apple iTunes API directly:
```bash
curl -s "https://itunes.apple.com/search?term=paypal&entity=software&limit=1"
```

Verify Bluesky public search directly:
```bash
curl -s "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?q=bsky&limit=1"
```
