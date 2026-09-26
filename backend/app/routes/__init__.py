from .ingestion import router as ingestion_router
from .reports import router as reports_router
from .visits import router as visits_router
from .days import router as days_router

__all__ = ["ingestion_router", "reports_router", "visits_router", "days_router"]
