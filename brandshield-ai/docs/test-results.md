# BrandShield AI — Test Results & Verification Report

This document records the **actual, observed test outcomes** across the backend test suite, frontend production build, synthetic dataset validator, and Prompt 08 acceptance tests.

---

## 1. Executive Summary of Observed Results

| Test Category | Command | Exit Code | Outcome | Execution Time |
| :--- | :--- | :---: | :---: | :---: |
| **Backend Test Suite** | `pytest -v` | **0** | **81 Passed, 2 Skipped, 1 Warning** | ~61.88s |
| **Frontend Production Build** | `npm run build` | **0** | **0 Errors, 1600 modules bundled** | ~3.15s |
| **Dataset Validator** | `python validate_dataset.py` | **0** | **8/8 Suites Passed (100%)** | ~0.60s |
| **Prompt 08 Acceptance Suite** | `pytest tests/test_prompt08_acceptance.py -v` | **0** | **10/10 Passed (14/14 Criteria Verified)** | ~17.29s |

*Database Isolation Note:* All automated backend tests ran strictly against the isolated database `brandshield_test` in MongoDB Atlas. Development data in `brandshield_dev` remained untouched.

---

## 2. Prompt 08 Acceptance Test Verification (14 Criteria)

The acceptance suite in `backend/tests/test_prompt08_acceptance.py` explicitly tests the 14 requirements defined in Prompt 08:

| # | Acceptance Criterion | Test Function | Observed Result |
| :--- | :--- | :--- | :---: |
| **1 & 2** | Create brand with official social/app assets & verify persistence in Atlas | `test_acceptance_01_and_02_brand_creation_and_atlas_persistence` | **PASS** |
| **3** | Confirm official social and app assets are excluded before threat scoring | `test_acceptance_03_official_assets_excluded_before_scoring` | **PASS** |
| **4 & 5** | Social look-alikes and suspicious apps receive explainable assessments | `test_acceptance_04_and_05_explainable_assessments_for_social_and_app` | **PASS** |
| **6** | Candidates with missing bio, description, icons, or links do not crash | `test_acceptance_06_missing_fields_do_not_crash_app` | **PASS** |
| **7 & 8** | Campaign graph edges derive from shared indicators; unrelated stay isolated | `test_acceptance_07_and_08_campaign_edges_and_unrelated_isolation` | **PASS** |
| **9** | Investigation triage status persists and is returned on re-fetch | `test_acceptance_09_investigation_status_persists` | **PASS** |
| **10** | Dashboard metrics strictly exclude official assets from active threat counts | `test_acceptance_10_dashboard_metrics_exclude_official_assets` | **PASS** |
| **11** | Demo seed, manual submission, and live connector are clearly distinguishable | `test_acceptance_11_distinct_provenance_labels` | **PASS** |
| **12 & 13** | Connector failure produces per-source error without synthetic fallbacks | `test_acceptance_12_and_13_safe_error_handling_and_no_synthetic_fallbacks` | **PASS** |
| **14** | Benign names stay below threat threshold (< 40) and safe-list variants score 0 | `test_acceptance_14_benign_name_table_no_overflagging` | **PASS** |

---

## 3. Benign vs. Malicious Scoring Verification Table

To ensure BrandShield AI prevents over-flagging and respects the Name-Only Ceiling, the detection engine was evaluated against both benign variants and malicious impersonators:

### Benign & Excluded Entities (Target: Score < 40 / No Threat Alert)

| Candidate Name | Context / Variation | Points Assigned | Final Score | Classification | Verified Outcome |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Nova Payments Ltd** | Independent company; low token overlap | Name Sim: 20 pts | **20** | `LOW_RISK` | **PASS** (Below 40 threshold) |
| **Pay Nova Fitness** | Generic inverted tokens; unrelated sector | Name Sim: 0 pts | **0** | `LOW_RISK` | **PASS** (Below 40 threshold) |
| **Novak Pay** | Single transposition; no malicious signals | Name Sim: 20 pts | **20** | `LOW_RISK` | **PASS** (Below 40 threshold) |
| **Nova Pay Careers** | Registered in Brand `safe_list` | Safe-list Guard: 0 pts | **0** | `LOW_RISK` | **PASS** (Excluded before scoring) |
| **NovaPay Official App** | Registered Bundle ID + Publisher ID | Official Guard: 0 pts | **0** | `OFFICIAL_EXCLUDED` | **PASS** (Excluded before scoring) |

### Malicious & Impersonation Candidates (Target: Score >= 40 / Actionable Alert)

| Candidate Name | Signals Detected | Point Breakdown | Final Score | Severity | Classification |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **N0vaPay Support** | Levenshtein homoglyph + Phishing URL + Scam bio | Name: 35<br>Homoglyph: +5 (Capped at 40)<br>Domain: +25<br>Scam Lang: +15 | **80** | **High** | `POTENTIAL_THREAT` |
| **NovaPay Wallet 2FA** | Brand token in title + Publisher mismatch + Phishing domain | Name: 35<br>Publisher Mismatch: +20 | **55** | **Medium** | `POTENTIAL_THREAT` |
| **NovaPay Official Support** | Exact brand name match + Scam bio keywords ("giveaway", "refund") | Name: 35<br>Scam Lang: +15 | **50** | **Medium** | `POTENTIAL_THREAT` |
| **NovaPay Clone (Name Only)** | Exact name match, but zero external links, valid publisher, no scam words | Name: 35<br>No corroborating evidence | **35** | **Low** | `LOW_RISK`<br>*(Capped by Name-Only Ceiling)* |

---

## 4. Warnings & Deprecations Analysis

During test execution, one third-party deprecation warning was observed:

```text
venv\Lib\site-packages\starlette\testclient.py:37: DeprecationWarning: 
The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
  _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]
```

*Investigation Outcome:*
This warning originates inside Starlette's `TestClient` (imported through FastAPI). It does not originate within BrandShield AI's codebase. Upgrading Starlette or AnyIO independently at this stage would introduce untested transitive dependency changes prior to hackathon presentation. As the warning has zero impact on application runtime or stability, it is acknowledged and left intact.

---

## 5. Synthetic Dataset Validation Details

Running `novapay_synthetic_dataset/validate_dataset.py` confirmed 100% data integrity:
- **`brands.json`**: 1 valid brand specification (`NovaPay`).
- **`ground_truth.csv`**: 12 labeled candidate records (social profiles and mobile apps).
- **`official_assets`**: 1 official social asset (`novapay.synthetic.example`), 1 official app asset (`example.synthetic.novapay.wallet`).
- **`provenance`**: All synthetic entities explicitly declare `source_type="demo"`, `is_demo_data=true`, and `is_synthetic=true`.
- **`campaign_links`**: Shared indicator graph matches campaign structure across infrastructure (`https://attacker-infrastructure.com`) without phantom edges.
