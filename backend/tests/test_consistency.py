import tempfile
import os
from datetime import datetime
from app.db.database import init_db
from app.models.billing import VisitRecord, LineItem, PaymentMode
from app.db.repository import save_visits_batch, upsert_visit, get_visits_by_date
from app.core.reconciliation import compute_eod_reconciliation

def test_data_consistency_upon_update():
    """
    Validates that updating a visit in the database immediately updates
    reconciliation totals and outstanding calculations without desync.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        init_db(db_path)

        visit1 = VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-100",
            timestamp=datetime(2026, 7, 27, 10, 0),
            line_items=[LineItem(drug_name="AMOXICILLIN", qty=2, unit_price_paise=5000)], # 10000 paise
            payment_mode=PaymentMode.CASH,
            amount_paid_paise=5000, # 5000 paise outstanding
            discount_paise=0,
            is_refund=False
        )

        save_visits_batch([visit1], "CLN-TEST", "2026-07-27", db_path=db_path)

        # Initial check
        visits = get_visits_by_date("2026-07-27", "CLN-TEST", db_path=db_path)
        recon1 = compute_eod_reconciliation(visits, "CLN-TEST", "2026-07-27")
        assert recon1.total_billed_paise == 10000
        assert recon1.total_collected_paise == 5000
        assert recon1.total_outstanding_paise == 5000
        assert recon1.pending_invoices_count == 1

        # Now update: patient pays remaining 5000 paise
        updated_visit = VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-100",
            timestamp=datetime(2026, 7, 27, 10, 0),
            line_items=[LineItem(drug_name="AMOXICILLIN", qty=2, unit_price_paise=5000)],
            payment_mode=PaymentMode.CASH,
            amount_paid_paise=10000, # fully paid now
            discount_paise=0,
            is_refund=False
        )

        upsert_visit(updated_visit, db_path=db_path)

        # Verify new state
        visits_after = get_visits_by_date("2026-07-27", "CLN-TEST", db_path=db_path)
        recon2 = compute_eod_reconciliation(visits_after, "CLN-TEST", "2026-07-27")
        assert recon2.total_billed_paise == 10000
        assert recon2.total_collected_paise == 10000
        assert recon2.total_outstanding_paise == 0
        assert recon2.pending_invoices_count == 0
        assert recon2.collection_rate_percent == 100.0

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
