from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import CORS_ORIGINS
from .db.database import init_db
from .routes.ingestion import router as ingestion_router
from .routes.reports import router as reports_router
from .routes.visits import router as visits_router
from .routes.days import router as days_router
from seed_data import seed_sample_datasets

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB schema and seed initial sample dataset
    init_db()
    try:
        seed_sample_datasets()
    except Exception as e:
        print(f"Dataset auto-seeding warning: {e}")
    yield
    # Shutdown

app = FastAPI(
    title="SwasthiQ Kaagazy EOD Billing & Analytics Agent API",
    description="Deterministic EOD reconciliation, revenue analytics, and LLM-grounded narrative layer.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(ingestion_router)
app.include_router(reports_router)
app.include_router(visits_router)
app.include_router(days_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "SwasthiQ EOD Billing API"}
