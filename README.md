# BrandShield AI — Digital Risk Protection

> **Kampus.VC Hackathon Prototype**: Explainable, deterministic brand impersonation monitoring across social media and mobile app ecosystems.

BrandShield AI defends brands against fraudulent social accounts, look-alike mobile apps, and typosquatted domains without black-box ML hallucinations or false positives on official channels.

---

## Key Guarantees & Features

1. **Pre-Scoring Official-Asset Safety Guard**:
   * Official brand assets (verified handles, DIDs, website domains, App Store bundle IDs, developer IDs) are evaluated and marked `OFFICIAL_EXCLUDED` *before* threat scoring.
   * Legitimate properties receive a score of 0 and are quarantined from active alert counts.
2. **Deterministic, Multi-Signal Scoring Engine**:
   * Completely transparent, rules-based engine combining 6 independent signal families (Name Similarity, Look-alike Domains, App Publisher Mismatch, Scam Language, Perceptual Logo Hashing, Description Semantics).
   * **Name-Only Ceiling**: Similar or identical names alone cannot exceed 40/100 (Medium) without corroborating evidence (phishing domain, developer mismatch, or scam urgency phrases).
   * **Severity Bands**: Critical (85–100), High (70–84), Medium (40–69), Low (< 40).
3. **Impersonation Campaign Graph**:
   * Clusters cross-platform threat assets based *only* on concrete recorded indicators: identical non-generic external domains, developer publisher IDs, contact details, or exact perceptual logo hashes.
   * Generic platforms (GitHub, Bitly, Linktree) are filtered to prevent false edges.
   * Labeled objectively as `POTENTIAL_COORDINATION` (never unverified claims of common ownership).
4. **Transparent Provenance Tracking**:
   * Every record explicitly preserves its origin: `live_connector`, `manual`, or `demo`.
   * Synthetic records are never substituted as fake live findings during connector outages.
5. **Database Isolation**:
   * Automated tests run strictly against `brandshield_test` in MongoDB Atlas, leaving development data in `brandshield_dev` completely intact.

---

## Tech Stack

* **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, React Router, Lucide Icons
* **Backend**: Python 3.11+, FastAPI, Pydantic v2, PyMongo, HTTPX, RapidFuzz, Pillow, ImageHash
* **Database**: MongoDB Atlas (Cloud NoSQL)
* **Testing**: Pytest (81 passed unit/integration/acceptance tests), TypeScript compiler (`tsc`)

---

## System Architecture

```text
Data Sources (Apple iTunes, Bluesky XRPC, Manual, Demo Seed)
    └── Connectors (Allowlisted hosts, 8s timeout, graceful degradation)
         └── Normalization & Validation (Unicode NFKC, Homoglyphs)
              └── Official Safety Guard (Pre-scoring exclusion: OFFICIAL_EXCLUDED)
                   └── Detection Engine (6 Signal families, Name-Only Ceiling)
                        └── Campaign Graph Service (Concrete shared indicators)
                             └── MongoDB Atlas & React UI (Triage & Audit Trails)
```

Detailed diagrams and flow descriptions are available in [`docs/architecture.md`](docs/architecture.md) and [`docs/architecture.png`](docs/architecture.png).

---

## Setup & Local Execution

### Prerequisites
* Python 3.11+
* Node.js 18+ & npm
* MongoDB Atlas cluster connection string

### 1. Backend Setup

```bash
cd brandshield-ai/backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your MONGODB_URI and database names
```

Run test suite (runs against isolated `brandshield_test`):
```bash
pytest -v
```

Start backend development server:
```bash
uvicorn app.main:app --reload --port 8000
```

Verify backend health:
* Process health: `http://localhost:8000/health`
* Readiness & DB connection: `http://localhost:8000/api/v1/health`

### 2. Frontend Setup

```bash
cd brandshield-ai/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Ensure VITE_API_BASE_URL=http://localhost:8000

# Start development server
npm run dev

# Run production build validation
npm run build
```

---

## Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `DATABASE_NAME` | Active application database | `brandshield_dev` |
| `TEST_DATABASE_NAME` | Isolated database for test runs | `brandshield_test` |
| `FRONTEND_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:5173,http://localhost:3000` |
| `ENVIRONMENT` | Runtime environment | `development` / `production` |
| `PORT` | API server port | `8000` |

### Frontend (`frontend/.env`)
| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL for FastAPI backend | `http://localhost:8000` |

---

## Live Connectors & Ingestion Boundaries

BrandShield AI connects to public, unauthenticated APIs without requiring proprietary developer keys:

1. **Apple iTunes Search API (`software` entity)**:
   * Endpoint: `https://itunes.apple.com/search`
   * Bounded to `itunes.apple.com` and `*.mzstatic.com`
   * Rate limit: ~20 requests per minute
2. **Bluesky Public XRPC Search (`searchActors`)**:
   * Endpoint: `https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors`
   * Bounded to `public.api.bsky.app` and `cdn.bsky.app`
   * Rate limit: ~300 requests per 5 minutes per IP

### Network Boundaries & Graceful Degradation
* Requests have strict 8.0s timeouts and a 2 MB response size cap.
* Arbitrary user-supplied target URLs are strictly forbidden to prevent SSRF vulnerabilities.
* When an upstream source is unreachable, BrandShield AI reports that connector as degraded, continues processing available sources, and **never substitutes fake synthetic data**.

---

## Known Limitations & Honest Scoping

1. **Connector Scoping**:
   * Google Play Store, Instagram, and X (Twitter) are not included in this prototype because they do not provide unauthenticated public REST endpoints.
2. **Cloud Cold Starts**:
   * When hosted on free-tier services (e.g. Render), backend instances spin down after inactivity and take ~50 seconds to warm up. (Send a pre-ping to `/api/v1/health` 5 minutes before presentations).
3. **Campaign Attribution**:
   * Campaign clusters represent shared technical indicators, not proven legal ownership or criminal conspiracy. Groups are labeled `POTENTIAL_COORDINATION`.

---

## Project Documentation Directory

* [`docs/architecture.md`](docs/architecture.md): Complete dataflow, pre-scoring safety guard, and Mermaid diagram.
* [`docs/architecture.png`](docs/architecture.png): High-resolution diagram exported for presentation slides.
* [`docs/sources.md`](docs/sources.md): Public connector endpoints, parameters, field mappings, and rate limits.
* [`docs/test-results.md`](docs/test-results.md): Observed test results, acceptance verification, and benign vs. malicious scoring matrix.
* [`docs/demo-script.md`](docs/demo-script.md): 3–4 minute timed demo walkthrough with cold-start pre-ping and backup video checklist.
* [`docs/presentation-outline.md`](docs/presentation-outline.md): 7-slide hackathon presentation outline.
