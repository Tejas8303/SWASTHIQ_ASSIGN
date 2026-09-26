import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "clinic_billing.db"))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # "auto", "gemini", "openai", "groq", "mock"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Clinic metadata defaults
DEFAULT_CLINIC_ID = "CLN-KNP-014"
CLINIC_METADATA = {
    "CLN-KNP-014": {
        "name": "Mehta Multi-Specialty Clinic",
        "location": "Kanpur, Uttar Pradesh",
        "owner_name": "Dr. Arvind Mehta"
    }
}

# CORS settings
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"
]
