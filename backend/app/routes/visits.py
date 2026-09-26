from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Body, status
from ..models.billing import VisitRecord
from ..db.repository import get_visits_by_date, upsert_visit
from ..config import DEFAULT_CLINIC_ID

router = APIRouter(prefix="/api/visits", tags=["Visits"])


@router.get("", response_model=List[VisitRecord])
async def list_visits(
    date: str = Query(..., description="Target date YYYY-MM-DD"),
    clinic_id: str = Query(DEFAULT_CLINIC_ID, description="Target clinic identifier")
):
    """Lists all stored visits for a given date and clinic."""
    return get_visits_by_date(date, clinic_id)


@router.post("/update", response_model=Dict[str, Any])
async def update_or_create_visit(
    visit: VisitRecord = Body(..., description="Visit record to insert or update")
):
    """
    Updates or inserts a visit record.
    Maintains data consistency upon update:
    - Atomically persists within a database transaction
    - Re-computes gross_total, net_billed, and outstanding values in integer paise
    - Invalidates downstream caches, ensuring subsequent reconciliation queries reflect the new state.
    """
    updated = upsert_visit(visit)
    return {
        "status": "success",
        "message": f"Visit {updated.visit_id} saved successfully.",
        "visit_id": updated.visit_id,
        "net_billed_paise": updated.net_billed_paise,
        "amount_paid_paise": updated.amount_paid_paise,
        "outstanding_paise": updated.outstanding_paise
    }
