import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
from ..config import DATABASE_PATH

def init_db(db_path: str = DATABASE_PATH):
    """Initializes SQLite database and tables."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        
        # Visits table (Sole Ground Truth)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                visit_id TEXT PRIMARY KEY,
                clinic_id TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                doctor_id TEXT,
                payment_mode TEXT NOT NULL,
                amount_paid_paise INTEGER NOT NULL,
                discount_paise INTEGER NOT NULL DEFAULT 0,
                is_refund INTEGER NOT NULL DEFAULT 0,
                gross_total_paise INTEGER NOT NULL,
                net_billed_paise INTEGER NOT NULL,
                outstanding_paise INTEGER NOT NULL,
                line_items_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_clinic_date ON visits (clinic_id, visit_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_timestamp ON visits (timestamp);")

        # Ingestion audits table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clinic_id TEXT,
                visit_date TEXT,
                filename TEXT,
                total_rows INTEGER NOT NULL,
                valid_count INTEGER NOT NULL,
                rejected_count INTEGER NOT NULL,
                errors_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


@contextmanager
def get_db(db_path: str = DATABASE_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yields a SQLite connection within an atomic transaction."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
