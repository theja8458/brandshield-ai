import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.connectors.base import BaseConnector, ConnectorStatus, RawCandidate
from app.connectors.bluesky import BlueskyConnector
from app.connectors.itunes import ITunesConnector
from app.crud.brand import get_brand
from app.database import get_database
from app.detection.engine import evaluate_candidate
from app.services.official_guard import ExclusionStatus, evaluate_official_status

logger = logging.getLogger("brandshield.connectors.manager")


class SourceScanResult(BaseModel):
    connector_id: str
    display_name: str
    ok: bool
    candidates_found: int = 0
    new_candidates: int = 0
    excluded_official: int = 0
    error: Optional[str] = None


class BrandScanResponse(BaseModel):
    brand_id: str
    total_found: int
    total_new: int
    total_excluded_official: int
    source_results: List[SourceScanResult]
    scanned_at: str


class ConnectorManager:
    """Orchestrates public connectors, query generation, deduplication, and scan workflows."""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {
            "apple_itunes": ITunesConnector(),
            "bluesky": BlueskyConnector(),
        }

    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        return self._connectors.get(connector_id)

    async def get_all_statuses(self) -> List[ConnectorStatus]:
        """Retrieve status of all connectors, including demo and manual sources."""
        statuses = []
        for conn in self._connectors.values():
            status = await conn.health_check()
            statuses.append(status)

        # Explicitly describe Demo Seed and Manual modes
        statuses.append(
            ConnectorStatus(
                connector_id="demo_synthetic_seed",
                display_name="Repeatable Synthetic Seed (NovaPay v1)",
                platform="all",
                mode="demo",
                state="available",
                last_checked=datetime.now(timezone.utc).isoformat(),
                last_success_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        statuses.append(
            ConnectorStatus(
                connector_id="manual_analyst_entry",
                display_name="Manual Candidate Submission",
                platform="all",
                mode="manual",
                state="available",
                last_checked=datetime.now(timezone.utc).isoformat(),
                last_success_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        return statuses

    def generate_queries(self, brand: Dict[str, Any]) -> List[str]:
        """
        Generate bounded scan queries from brand name, aliases, and controlled variants.
        Capped strictly at 6 queries per scan.
        """
        name = (brand.get("name") or "").strip()
        queries = []
        if name:
            queries.append(name)
            if " " in name:
                queries.append(name.replace(" ", ""))
            else:
                # Add spaced variant if camelCase or title
                queries.append(name.lower())

            queries.append(f"{name} Official")
            queries.append(f"{name} Support")

        for alias in brand.get("aliases", []):
            if alias and alias not in queries:
                queries.append(alias)

        # Cap at 6 queries
        return queries[:6]

    async def scan_brand(
        self,
        brand_id: str,
        target_connectors: Optional[List[str]] = None,
        db_name: Optional[str] = None,
    ) -> BrandScanResponse:
        """
        Execute scan across selected public connectors for a registered brand.
        - Deduplicates by stable ID
        - Evaluates official guard BEFORE scoring
        - Persists scored candidates into MongoDB Atlas
        - Reports per-source partial successes and explicit errors
        """
        brand = get_brand(brand_id, db_name=db_name)
        if not brand:
            raise ValueError(f"Brand '{brand_id}' not found.")

        queries = self.generate_queries(brand)
        connectors_to_run = target_connectors or list(self._connectors.keys())

        db = get_database(db_name)
        candidates_col = db["candidates"]

        source_results: List[SourceScanResult] = []
        total_found = 0
        total_new = 0
        total_excluded = 0

        # Run each connector independently to guarantee graceful degradation
        for conn_id in connectors_to_run:
            conn = self.get_connector(conn_id)
            if not conn:
                source_results.append(
                    SourceScanResult(
                        connector_id=conn_id,
                        display_name=conn_id,
                        ok=False,
                        error="Unknown connector ID",
                    )
                )
                continue

            conn_found = 0
            conn_new = 0
            conn_excluded = 0
            conn_error = None
            seen_stable_ids = set()

            try:
                for q in queries:
                    raw_items = await conn.search(q)
                    for raw in raw_items:
                        # Deduplicate by stable ID (bundleId or did)
                        stable_key = raw.stable_account_id or raw.package_or_bundle_id or raw.candidate_id
                        if stable_key in seen_stable_ids:
                            continue
                        seen_stable_ids.add(stable_key)
                        conn_found += 1

                        cand_dict = raw.model_dump()
                        cand_dict["brand_id"] = brand.get("brand_id")

                        # Run official guard BEFORE scoring
                        official_eval = evaluate_official_status(brand, cand_dict)
                        if official_eval.status == ExclusionStatus.OFFICIAL_EXCLUDED:
                            conn_excluded += 1
                            cand_dict["score"] = 0
                            cand_dict["severity"] = "Low"
                            cand_dict["classification"] = "OFFICIAL_EXCLUDED"
                            cand_dict["is_excluded_from_scoring"] = True
                            cand_dict["signals"] = []
                            cand_dict["investigation_status"] = "resolved"
                        else:
                            # Evaluate through shared detection engine
                            eval_res = evaluate_candidate(brand, cand_dict)
                            cand_dict["score"] = eval_res.score
                            cand_dict["severity"] = eval_res.severity
                            cand_dict["classification"] = eval_res.classification
                            cand_dict["signals"] = [s.model_dump() for s in eval_res.signals]
                            cand_dict["missing_evidence"] = eval_res.missing_evidence
                            cand_dict["evidence_completeness"] = eval_res.evidence_completeness
                            cand_dict["investigation_status"] = "new"

                        cand_dict["analyzed_at"] = datetime.now(timezone.utc).isoformat()

                        # Upsert candidate into Atlas by candidate_id
                        res = candidates_col.update_one(
                            {"candidate_id": cand_dict["candidate_id"]},
                            {"$set": cand_dict},
                            upsert=True,
                        )
                        if res.upserted_id:
                            conn_new += 1

                source_results.append(
                    SourceScanResult(
                        connector_id=conn.id,
                        display_name=conn.display_name,
                        ok=True,
                        candidates_found=conn_found,
                        new_candidates=conn_new,
                        excluded_official=conn_excluded,
                    )
                )
            except Exception as err:
                logger.warning("Connector %s failed during scan: %s", conn.id, err)
                conn_error = f"{type(err).__name__}: {str(err)}"
                source_results.append(
                    SourceScanResult(
                        connector_id=conn.id,
                        display_name=conn.display_name,
                        ok=False,
                        candidates_found=conn_found,
                        new_candidates=conn_new,
                        excluded_official=conn_excluded,
                        error=conn_error,
                    )
                )

            total_found += conn_found
            total_new += conn_new
            total_excluded += conn_excluded

        return BrandScanResponse(
            brand_id=brand.get("brand_id", brand_id),
            total_found=total_found,
            total_new=total_new,
            total_excluded_official=total_excluded,
            source_results=source_results,
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )


connector_manager = ConnectorManager()
