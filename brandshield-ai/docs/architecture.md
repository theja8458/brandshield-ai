# BrandShield AI — System Architecture

BrandShield AI is an explainable, deterministic Digital Risk Protection (DRP) prototype designed for monitoring social-media and mobile-app impersonation.

## Architecture Diagram

```mermaid
flowchart TD
    subgraph DataSources["Data Sources & Ingestion"]
        BSKY["Bluesky Public Search API\n(searchActors)"]
        ITUNES["Apple iTunes Search API\n(software entity)"]
        MANUAL["Manual Candidate Submission"]
        DEMO["Repeatable Synthetic Seed\n(NovaPay v1)"]
    end

    subgraph Connectors["Connector Layer"]
        CONN["Unified Connector Interface\n(Graceful Degradation & Health Tracking)"]
    end

    subgraph Ingestion["Ingestion & Validation Pipeline"]
        VAL["Schema Validation & Normalization\n(NFKC, Homoglyphs, Domain Extraction)"]
    end

    subgraph OfficialGuard["Official-Asset Safety Guard"]
        OFF_CHECK{"Matches Registered\nOfficial Asset?"}
        OFF_EXC["Status: OFFICIAL_EXCLUDED\n(Excluded before scoring; zero false alerts)"]
    end

    subgraph DetectionEngine["Deterministic Detection Engine"]
        SCORE["Explainable Scoring (Max 100)\n- Name Similarity (Max 35)\n- Evasion Bonus (Max +10)\n- Name Family Cap (Max 40)\n- Lookalike Domain (25)\n- Publisher Mismatch (20)\n- Scam Language (15)\n- Image Hash / Logo (15)\n- Description Similarity (10)"]
        CLASS["Risk Classification\n- Critical (>= 85)\n- High (70-84)\n- Medium (40-69)\n- Low (< 40)"]
    end

    subgraph CampaignService["Impersonation Campaign Service"]
        GRAPH["Shared Indicators Graph\n(Domains, Contact Info, Hashes, Publisher IDs)"]
    end

    subgraph Storage["Persistence & Integrity"]
        ATLAS[("MongoDB Atlas\n(brandshield_dev / brandshield_test)")]
    end

    subgraph UserInterface["Responsive Web UI"]
        UI["React + TypeScript + Tailwind SPA\n- Dashboard & Live Health\n- Brand Profile Management\n- Social Monitoring\n- App Monitoring\n- Campaign Graph\n- Evidence Trail & Investigations"]
    end

    DataSources --> CONN
    CONN --> VAL
    VAL --> OFF_CHECK
    OFF_CHECK -- "Yes (Strong ID match)" --> OFF_EXC
    OFF_CHECK -- "No (Unknown asset)" --> SCORE
    OFF_EXC --> ATLAS
    SCORE --> CLASS
    CLASS --> ATLAS
    ATLAS --> GRAPH
    ATLAS --> UI
    GRAPH --> UI
```

## Core Architectural Guarantees

1. **Official-Asset Exclusion Before Scoring**:
   Registered official assets (canonical URLs, verified handles, stable account IDs, package/bundle IDs) are matched and excluded *before* any risk calculation takes place. This guarantees zero false positive alerts on legitimate brand properties.

2. **Deterministic & Explainable Scoring**:
   Risk scores are calculated by an open, rules-based algorithm rather than opaque black-box models. Every assigned point includes an auditable evidence reason and matched indicator.

3. **Name-Only Ceiling**:
   A similar name alone cannot exceed 40 points (Medium). It requires corroborating signals (look-alike domain, publisher mismatch, scam phrases, or matching visual hashes) to reach High or Critical severity.

4. **Transparent Provenance**:
   Every record is tagged with its origin (`live_connector`, `manual`, or `demo`), preventing any confusion between live network data and synthetic demo data.

5. **Storage & Isolation**:
   MongoDB Atlas stores brand profiles, candidate telemetry, and investigation logs. Unit and integration tests run strictly against an isolated `TEST_DATABASE_NAME`.
