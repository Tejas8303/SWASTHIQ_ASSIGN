import pytest
from datetime import datetime
from app.models.billing import VisitRecord, LineItem, PaymentMode
from app.core.reconciliation import compute_eod_reconciliation
from app.core.analytics import compute_analytics

def test_deterministic_reconciliation_math():
    visits = [
        VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-1",
            timestamp=datetime(2026, 7, 27, 9, 30),
            line_items=[LineItem(drug_name="PARACETAMOL", qty=2, unit_price_paise=2000)], # 4000 paise
            payment_mode=PaymentMode.CASH,
            amount_paid_paise=3500, # 500 outstanding
            discount_paise=500,     # net billed: 4000 - 500 = 3500
            is_refund=False
        ),
        VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-2",
            timestamp=datetime(2026, 7, 27, 10, 15),
            line_items=[LineItem(drug_name="AMOXICILLIN", qty=1, unit_price_paise=6000)], # 6000 paise
            payment_mode=PaymentMode.CARD,
            amount_paid_paise=4000, # net billed 6000, 2000 outstanding
            discount_paise=0,
            is_refund=False
        ),
        VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-3",
            timestamp=datetime(2026, 7, 27, 11, 0),
            line_items=[LineItem(drug_name="METFORMIN", qty=1, unit_price_paise=3000)],
            payment_mode=PaymentMode.UPI,
            amount_paid_paise=-3000, # refund
            discount_paise=0,
            is_refund=True
        )
    ]

    report = compute_eod_reconciliation(visits, clinic_id="CLN-TEST", date_str="2026-07-27")

    # Math verifications in integer paise
    assert report.total_visits == 3
    assert report.refund_visits_count == 1
    assert report.pending_invoices_count == 1  # V-2 has outstanding 2000; V-1 had net billed 3500 paid 3500 -> 0 outstanding

    # Cash: billed 3500, paid 3500, outstanding 0
    assert report.by_payment_mode["cash"].billed_paise == 3500
    assert report.by_payment_mode["cash"].collected_paise == 3500
    assert report.by_payment_mode["cash"].outstanding_paise == 0

    # Card: billed 6000, paid 4000, outstanding 2000
    assert report.by_payment_mode["card"].billed_paise == 6000
    assert report.by_payment_mode["card"].collected_paise == 4000
    assert report.by_payment_mode["card"].outstanding_paise == 2000

    # UPI: refund 3000
    assert report.by_payment_mode["upi"].billed_paise == 0
    assert report.by_payment_mode["upi"].refunds_paise == 3000

    # Totals
    assert report.total_billed_paise == 9500
    assert report.total_collected_paise == 7500
    assert report.total_outstanding_paise == 2000
    assert report.total_refunds_paise == 3000

    # Identity check
    assert report.total_billed_paise == report.total_collected_paise + report.total_outstanding_paise


def test_analytics_peak_hour_and_dual_rankings():
    visits = [
        VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-1",
            timestamp=datetime(2026, 7, 27, 12, 10),
            line_items=[
                LineItem(drug_name="PARACETAMOL", qty=10, unit_price_paise=2000) # 20000 paise
            ],
            payment_mode=PaymentMode.CASH,
            amount_paid_paise=20000,
            discount_paise=0,
            is_refund=False
        ),
        VisitRecord(
            clinic_id="CLN-TEST",
            visit_id="V-2",
            timestamp=datetime(2026, 7, 27, 14, 30),
            line_items=[
                LineItem(drug_name="ATORVASTATIN", qty=2, unit_price_paise=15000) # 30000 paise
            ],
            payment_mode=PaymentMode.CARD,
            amount_paid_paise=30000,
            discount_paise=0,
            is_refund=False
        )
    ]

    analytics = compute_analytics(visits, clinic_id="CLN-TEST", date_str="2026-07-27")

    # Peak hour should be 14:00 (2pm-3pm) with 30000 paise (₹300)
    assert analytics.peak_hour is not None
    assert analytics.peak_hour.hour == 14
    assert analytics.peak_hour.revenue_paise == 30000

    # Two distinct rankings:
    # By Quantity: PARACETAMOL is #1 (10 units vs 2 units)
    assert analytics.top_by_quantity[0].drug_name == "PARACETAMOL"
    assert analytics.top_by_quantity[0].quantity == 10

    # By Revenue: ATORVASTATIN is #1 (30000 paise vs 20000 paise)
    assert analytics.top_by_revenue[0].drug_name == "ATORVASTATIN"
    assert analytics.top_by_revenue[0].revenue_paise == 30000
