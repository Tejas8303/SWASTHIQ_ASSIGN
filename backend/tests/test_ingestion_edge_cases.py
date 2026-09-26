import json
from pathlib import Path
from app.core.ingestion import parse_and_validate_billing_log
from app.core.reconciliation import compute_eod_reconciliation
from app.core.analytics import compute_analytics

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "swasthiq_sample_billing_dataset"

def test_july_27_edge_cases_and_actionable_errors():
    """Tests July 27: 1 malformed row (missing payment_mode), 18 valid rows, typo normalization."""
    file_path = DATASET_DIR / "billing_log_2026-07-27.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_records, errors = parse_and_validate_billing_log(data)

    assert len(data) == 19
    assert len(valid_records) == 18
    assert len(errors) == 1

    # Check actionable error specifics
    err = errors[0]
    assert err.row_index == 18
    assert err.visit_id == "V-20260727-019"
    assert err.field == "payment_mode"
    assert "Missing required field 'payment_mode'" in err.error_message

    # Check drug name normalization: PARACETMOL typo normalized to PARACETAMOL
    all_drugs = [item.drug_name for v in valid_records for item in v.line_items]
    assert "PARACETMOL" not in all_drugs
    assert "PARACETAMOL" in all_drugs


def test_july_26_empty_day():
    """Tests July 26: Empty day [] edge case."""
    file_path = DATASET_DIR / "billing_log_2026-07-26.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_records, errors = parse_and_validate_billing_log(data)

    assert len(valid_records) == 0
    assert len(errors) == 0

    recon = compute_eod_reconciliation(valid_records, date_str="2026-07-26")
    assert recon.total_visits == 0
    assert recon.total_billed_paise == 0
    assert recon.total_collected_paise == 0
    assert recon.total_outstanding_paise == 0
    assert recon.total_refunds_paise == 0
    assert recon.collection_rate_percent == 0.0

    analytics = compute_analytics(valid_records, date_str="2026-07-26")
    assert analytics.peak_hour is None
    assert len(analytics.top_by_quantity) == 0
    assert len(analytics.top_by_revenue) == 0


def test_july_25_refunds_only_day():
    """Tests July 25: All 3 rows are refunds with negative amounts."""
    file_path = DATASET_DIR / "billing_log_2026-07-25.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_records, errors = parse_and_validate_billing_log(data)

    assert len(valid_records) == 3
    assert len(errors) == 0
    assert all(v.is_refund for v in valid_records)

    recon = compute_eod_reconciliation(valid_records, date_str="2026-07-25")
    assert recon.total_visits == 3
    assert recon.refund_visits_count == 3
    assert recon.total_billed_paise == 0
    assert recon.total_outstanding_paise == 0
    # Sum of refunds: 24000 + 22000 + 3000 = 49000 paise (₹490)
    assert recon.total_refunds_paise == 49000
    assert recon.total_refunds_rupees == 490.0
    assert recon.by_payment_mode["card"].refunds_paise == 24000
    assert recon.by_payment_mode["upi"].refunds_paise == 25000
    assert recon.by_payment_mode["cash"].refunds_paise == 0


def test_malformed_types_rejection():
    """Rejection with actionable error on non-integer paise or negative amounts."""
    bad_payload = [
        {
            "clinic_id": "CLN-1",
            "visit_id": "V-BAD-1",
            "timestamp": "2026-07-27T10:00:00Z",
            "line_items": [{"drug_name": "ASPIRIN", "qty": 1, "unit_price_paise": 1000}],
            "payment_mode": "cash",
            "amount_paid_paise": "500",  # String instead of int
            "discount_paise": 0,
            "is_refund": False
        },
        {
            "clinic_id": "CLN-1",
            "visit_id": "V-BAD-2",
            "timestamp": "2026-07-27T10:00:00Z",
            "line_items": [{"drug_name": "ASPIRIN", "qty": 1, "unit_price_paise": 1000}],
            "payment_mode": "bitcoin",  # Invalid payment mode
            "amount_paid_paise": 1000,
            "discount_paise": 0,
            "is_refund": False
        },
        {
            "clinic_id": "CLN-1",
            "visit_id": "V-BAD-3",
            "timestamp": "not-a-timestamp",
            "line_items": [{"drug_name": "ASPIRIN", "qty": 1, "unit_price_paise": 1000}],
            "payment_mode": "cash",
            "amount_paid_paise": 1000,
            "discount_paise": 0,
            "is_refund": False
        }
    ]

    valid, errors = parse_and_validate_billing_log(bad_payload)
    assert len(valid) == 0
    assert len(errors) == 3

    assert errors[0].field == "amount_paid_paise"
    assert "must be an integer paise amount" in errors[0].error_message

    assert errors[1].field == "payment_mode"
    assert "Invalid payment_mode 'bitcoin'" in errors[1].error_message

    assert errors[2].field == "timestamp"
    assert "Invalid ISO 8601 timestamp" in errors[2].error_message
