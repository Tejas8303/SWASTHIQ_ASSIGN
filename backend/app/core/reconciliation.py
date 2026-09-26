from typing import List, Dict
from ..models.billing import VisitRecord, PaymentMode
from ..models.reports import ReconciliationReport, PaymentModeSummary
from ..config import CLINIC_METADATA

def compute_eod_reconciliation(
    visits: List[VisitRecord],
    clinic_id: str = "CLN-KNP-014",
    date_str: str = ""
) -> ReconciliationReport:
    """
    Computes deterministic EOD reconciliation from validated visits.
    All calculations are performed strictly in integer paise.
    Never calls an LLM.
    """
    modes = ["cash", "card", "upi"]
    by_mode_data: Dict[str, Dict[str, int]] = {
        m: {"billed": 0, "collected": 0, "outstanding": 0, "refunds": 0}
        for m in modes
    }

    pending_invoices_count = 0
    refund_visits_count = 0

    for v in visits:
        mode_key = v.payment_mode.value.lower()
        if mode_key not in by_mode_data:
            by_mode_data[mode_key] = {"billed": 0, "collected": 0, "outstanding": 0, "refunds": 0}

        if v.is_refund:
            refund_visits_count += 1
            ref_amt = abs(v.amount_paid_paise)
            by_mode_data[mode_key]["refunds"] += ref_amt
        else:
            billed = v.net_billed_paise
            collected = v.amount_paid_paise
            outstanding = v.outstanding_paise

            by_mode_data[mode_key]["billed"] += billed
            by_mode_data[mode_key]["collected"] += collected
            by_mode_data[mode_key]["outstanding"] += outstanding

            if outstanding > 0:
                pending_invoices_count += 1

    total_billed_paise = sum(d["billed"] for d in by_mode_data.values())
    total_collected_paise = sum(d["collected"] for d in by_mode_data.values())
    total_outstanding_paise = sum(d["outstanding"] for d in by_mode_data.values())
    total_refunds_paise = sum(d["refunds"] for d in by_mode_data.values())

    if total_billed_paise > 0:
        collection_rate_percent = round((total_collected_paise / total_billed_paise) * 100.0, 1)
    else:
        collection_rate_percent = 0.0

    # Build payment mode summaries
    summaries: Dict[str, PaymentModeSummary] = {}
    for m in modes:
        d = by_mode_data.get(m, {"billed": 0, "collected": 0, "outstanding": 0, "refunds": 0})
        summaries[m] = PaymentModeSummary(
            mode=m,
            billed_paise=d["billed"],
            collected_paise=d["collected"],
            outstanding_paise=d["outstanding"],
            refunds_paise=d["refunds"],
            billed_rupees=round(d["billed"] / 100.0, 2),
            collected_rupees=round(d["collected"] / 100.0, 2),
            outstanding_rupees=round(d["outstanding"] / 100.0, 2),
            refunds_rupees=round(d["refunds"] / 100.0, 2),
        )

    clinic_meta = CLINIC_METADATA.get(clinic_id, {
        "name": f"Clinic {clinic_id}",
        "location": "Kanpur, Uttar Pradesh",
        "owner_name": "Dr. Arvind Mehta"
    })

    return ReconciliationReport(
        clinic_id=clinic_id,
        clinic_name=clinic_meta.get("name", "Clinic"),
        clinic_location=clinic_meta.get("location", "Kanpur, Uttar Pradesh"),
        date=date_str,
        total_billed_paise=total_billed_paise,
        total_collected_paise=total_collected_paise,
        total_outstanding_paise=total_outstanding_paise,
        total_refunds_paise=total_refunds_paise,
        total_billed_rupees=round(total_billed_paise / 100.0, 2),
        total_collected_rupees=round(total_collected_paise / 100.0, 2),
        total_outstanding_rupees=round(total_outstanding_paise / 100.0, 2),
        total_refunds_rupees=round(total_refunds_paise / 100.0, 2),
        total_visits=len(visits),
        collection_rate_percent=collection_rate_percent,
        pending_invoices_count=pending_invoices_count,
        refund_visits_count=refund_visits_count,
        by_payment_mode=summaries
    )
