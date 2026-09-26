from typing import List, Dict, Any
from fastapi import APIRouter
from ..db.repository import get_available_dates

router = APIRouter(prefix="/api/days", tags=["Days"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_available_days():
    """Lists all clinic days currently stored in the database with visit totals."""
    return get_available_dates()
