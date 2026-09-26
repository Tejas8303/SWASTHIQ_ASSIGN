from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from ..models.reports import (
    ReconciliationReport,
    AnalyticsReport,
    NarrativeReport,
    EODBundleResponse
)
from ..core.reconciliation import compute_eod_reconciliation
from ..core.analytics import compute_analytics
from ..core.narrative import generate_narrative_report
from ..db.repository import get_visits_by_date, get_latest_audit
from ..config import DEFAULT_CLINIC_ID

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/reconciliation", response_model=ReconciliationReport)
async def get_reconciliation_report(
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    clinic_id: str = Query(DEFAULT_CLINIC_ID, description="Target clinic identifier")
):
    """Computes deterministic EOD reconciliation for the specified date."""
    visits = get_visits_by_date(date, clinic_id)
    return compute_eod_reconciliation(visits, clinic_id=clinic_id, date_str=date)


@router.get("/analytics", response_model=AnalyticsReport)
async def get_analytics_report(
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    clinic_id: str = Query(DEFAULT_CLINIC_ID, description="Target clinic identifier")
):
    """Computes deterministic analytics: hourly revenue, peak hour, dual rankings."""
    visits = get_visits_by_date(date, clinic_id)
    return compute_analytics(visits, clinic_id=clinic_id, date_str=date)


@router.get("/narrative", response_model=NarrativeReport)
async def get_narrative_report(
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    clinic_id: str = Query(DEFAULT_CLINIC_ID, description="Target clinic identifier")
):
    """Generates an owner-facing WhatsApp narrative with verified grounding."""
    visits = get_visits_by_date(date, clinic_id)
    recon = compute_eod_reconciliation(visits, clinic_id=clinic_id, date_str=date)
    analytics = compute_analytics(visits, clinic_id=clinic_id, date_str=date)
    return generate_narrative_report(recon, analytics)


@router.get("/eod-bundle", response_model=EODBundleResponse)
async def get_eod_bundle(
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    clinic_id: str = Query(DEFAULT_CLINIC_ID, description="Target clinic identifier")
):
    """
    Convenience endpoint that returns the complete EOD package:
    Reconciliation, Analytics, Narrative with Traced Figures, and Ingestion Audit.
    """
    visits = get_visits_by_date(date, clinic_id)
    recon = compute_eod_reconciliation(visits, clinic_id=clinic_id, date_str=date)
    analytics = compute_analytics(visits, clinic_id=clinic_id, date_str=date)
    narrative = generate_narrative_report(recon, analytics)
    audit = get_latest_audit(visit_date=date, clinic_id=clinic_id)

    return EODBundleResponse(
        clinic_id=clinic_id,
        date=date,
        reconciliation=recon,
        analytics=analytics,
        narrative=narrative,
        ingestion_summary=audit
    )
