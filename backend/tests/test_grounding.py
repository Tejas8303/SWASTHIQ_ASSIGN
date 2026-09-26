from datetime import datetime
from app.models.billing import VisitRecord, LineItem, PaymentMode
from app.core.reconciliation import compute_eod_reconciliation
from app.core.analytics import compute_analytics
from app.core.grounding import verify_grounding
from app.core.narrative import generate_deterministic_narrative, generate_narrative_report

def test_grounding_verification_flags_invented_numbers():
    visits = [
        VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-1",
            timestamp=datetime(2026, 7, 27, 10, 0),
            line_items=[LineItem(drug_name="PARACETAMOL", qty=5, unit_price_paise=2000)], # 10000 paise = 100 Rs
            payment_mode=PaymentMode.CASH,
            amount_paid_paise=10000,
            discount_paise=0,
            is_refund=False
        )
    ]
    recon = compute_eod_reconciliation(visits, clinic_id="CLN-TEST", date_str="2026-07-27")
    analytics = compute_analytics(visits, clinic_id="CLN-TEST", date_str="2026-07-27")

    # Hallucinated narrative claiming ₹99,999 profit and 500 visits
    hallucinated_text = (
        "Good evening! Mehta Clinic made ₹99,999 in profit today across 500 visits."
    )
    traced, zero_invented, ungrounded = verify_grounding(hallucinated_text, recon, analytics)

    assert zero_invented is False
    assert "99999" in ungrounded
    assert "500" in ungrounded


def test_deterministic_narrative_is_zero_invented_numbers():
    visits = [
        VisitRecord(
            clinic_id="CLN-KNP-014",
            visit_id="V-1",
            timestamp=datetime(2026, 7, 27, 12, 0),
            line_items=[LineItem(drug_name="PARACETAMOL", qty=10, unit_price_paise=2000)],
            payment_mode=PaymentMode.CASH,
            amount_paid_paise=18000, # 2000 outstanding
            discount_paise=0,
            is_refund=False
        )
    ]
    recon = compute_eod_reconciliation(visits, clinic_id="CLN-KNP-014", date_str="2026-07-27")
    analytics = compute_analytics(visits, clinic_id="CLN-KNP-014", date_str="2026-07-27")

    narrative = generate_narrative_report(recon, analytics)

    assert narrative.zero_invented_numbers is True
    assert narrative.grounding_status == "VERIFIED_GROUNDED"
    assert len(narrative.traced_figures) > 0
    assert "profit" in narrative.narrative_text.lower()
    assert "revenue, not profit" in narrative.narrative_text.lower()
