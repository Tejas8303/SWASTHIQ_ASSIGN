import json
import sqlite3
from typing import List, Optional, Dict, Any
from ..models.billing import VisitRecord, LineItem, PaymentMode
from .database import get_db
from ..config import DATABASE_PATH


def save_visits_batch(
    records: List[VisitRecord],
    clinic_id: str,
    visit_date: str,
    db_path: str = DATABASE_PATH
) -> int:
    """
    Atomically saves or updates a batch of validated VisitRecords.
    Uses an atomic transaction to ensure ACID consistency.
    """
    if not records:
        return 0

    with get_db(db_path) as conn:
        with conn:
            cursor = conn.cursor()
            for r in records:
                v_date = r.timestamp.strftime("%Y-%m-%d")
                items_json = json.dumps([item.model_dump() for item in r.line_items])
                cursor.execute("""
                    INSERT INTO visits (
                        visit_id, clinic_id, visit_date, timestamp, doctor_id,
                        payment_mode, amount_paid_paise, discount_paise, is_refund,
                        gross_total_paise, net_billed_paise, outstanding_paise,
                        line_items_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(visit_id) DO UPDATE SET
                        clinic_id=excluded.clinic_id,
                        visit_date=excluded.visit_date,
                        timestamp=excluded.timestamp,
                        doctor_id=excluded.doctor_id,
                        payment_mode=excluded.payment_mode,
                        amount_paid_paise=excluded.amount_paid_paise,
                        discount_paise=excluded.discount_paise,
                        is_refund=excluded.is_refund,
                        gross_total_paise=excluded.gross_total_paise,
                        net_billed_paise=excluded.net_billed_paise,
                        outstanding_paise=excluded.outstanding_paise,
                        line_items_json=excluded.line_items_json,
                        updated_at=CURRENT_TIMESTAMP;
                """, (
                    r.visit_id,
                    r.clinic_id,
                    v_date,
                    r.timestamp.isoformat(),
                    r.doctor_id,
                    r.payment_mode.value,
                    r.amount_paid_paise,
                    r.discount_paise,
                    1 if r.is_refund else 0,
                    r.gross_total_paise,
                    r.net_billed_paise,
                    r.outstanding_paise,
                    items_json
                ))
    return len(records)


def upsert_visit(
    record: VisitRecord,
    db_path: str = DATABASE_PATH
) -> VisitRecord:
    """
    Updates or inserts a single visit atomically, ensuring data consistency on update.
    Re-evaluates net_billed and outstanding before persisting.
    """
    save_visits_batch([record], record.clinic_id, record.timestamp.strftime("%Y-%m-%d"), db_path)
    return record


def get_visits_by_date(
    date_str: str,
    clinic_id: Optional[str] = None,
    db_path: str = DATABASE_PATH
) -> List[VisitRecord]:
    """Retrieves all visits for a specific date and optional clinic."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if clinic_id:
            cursor.execute("""
                SELECT * FROM visits 
                WHERE visit_date = ? AND clinic_id = ?
                ORDER BY timestamp ASC
            """, (date_str, clinic_id))
        else:
            cursor.execute("""
                SELECT * FROM visits 
                WHERE visit_date = ?
                ORDER BY timestamp ASC
            """, (date_str,))
        
        rows = cursor.fetchall()
        visits = []
        for row in rows:
            items_raw = json.loads(row["line_items_json"])
            items = [LineItem(**it) for it in items_raw]
            visits.append(VisitRecord(
                clinic_id=row["clinic_id"],
                visit_id=row["visit_id"],
                timestamp=row["timestamp"],
                doctor_id=row["doctor_id"],
                line_items=items,
                payment_mode=PaymentMode(row["payment_mode"]),
                amount_paid_paise=row["amount_paid_paise"],
                discount_paise=row["discount_paise"],
                is_refund=bool(row["is_refund"])
            ))
        return visits


def get_available_dates(db_path: str = DATABASE_PATH) -> List[Dict[str, Any]]:
    """Retrieves all available dates and their visit counts, including 0-visit audited days."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT visit_date, clinic_id, COUNT(*) as visit_count,
                   SUM(net_billed_paise) as total_billed_paise,
                   SUM(amount_paid_paise) as total_paid_paise
            FROM visits
            GROUP BY visit_date, clinic_id
        """)
        rows = cursor.fetchall()
        date_map = {
            row["visit_date"]: {
                "date": row["visit_date"],
                "clinic_id": row["clinic_id"],
                "visit_count": row["visit_count"],
                "total_billed_paise": row["total_billed_paise"] or 0,
                "total_paid_paise": row["total_paid_paise"] or 0
            }
            for row in rows
        }

        # Include dates from ingestion_audits that had 0 valid visits
        cursor.execute("""
            SELECT DISTINCT visit_date, clinic_id
            FROM ingestion_audits
            WHERE visit_date IS NOT NULL AND visit_date != ''
        """)
        for a_row in cursor.fetchall():
            dt = a_row["visit_date"]
            if dt not in date_map:
                date_map[dt] = {
                    "date": dt,
                    "clinic_id": a_row["clinic_id"] or "CLN-KNP-014",
                    "visit_count": 0,
                    "total_billed_paise": 0,
                    "total_paid_paise": 0
                }

        # Return sorted descending by date
        return sorted(date_map.values(), key=lambda x: x["date"], reverse=True)


def save_ingestion_audit(
    clinic_id: Optional[str],
    visit_date: Optional[str],
    filename: Optional[str],
    total_rows: int,
    valid_count: int,
    rejected_count: int,
    errors: List[Dict[str, Any]],
    db_path: str = DATABASE_PATH
) -> int:
    """Records an audit row for every ingestion operation."""
    with get_db(db_path) as conn:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ingestion_audits (
                    clinic_id, visit_date, filename, total_rows, valid_count, rejected_count, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                clinic_id,
                visit_date,
                filename or "direct_json",
                total_rows,
                valid_count,
                rejected_count,
                json.dumps(errors)
            ))
            return cursor.lastrowid


def get_latest_audit(
    visit_date: Optional[str] = None,
    clinic_id: Optional[str] = None,
    db_path: str = DATABASE_PATH
) -> Optional[Dict[str, Any]]:
    """Fetches the most recent ingestion audit log."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM ingestion_audits"
        params = []
        conds = []
        if visit_date:
            conds.append("visit_date = ?")
            params.append(visit_date)
        if clinic_id:
            conds.append("clinic_id = ?")
            params.append(clinic_id)
        if conds:
            query += " WHERE " + " AND ".join(conds)
        query += " ORDER BY id DESC LIMIT 1"
        cursor.execute(query, params)
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "clinic_id": row["clinic_id"],
            "visit_date": row["visit_date"],
            "filename": row["filename"],
            "total_rows": row["total_rows"],
            "valid_count": row["valid_count"],
            "rejected_count": row["rejected_count"],
            "errors": json.loads(row["errors_json"]),
            "created_at": row["created_at"]
        }
