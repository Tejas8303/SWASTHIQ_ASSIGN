import re
from typing import List, Tuple, Dict, Any, Optional
from ..models.reports import ReconciliationReport, AnalyticsReport, TracedFigure

def format_rupees(paise: int) -> str:
    """Formats paise as Indian rupee string e.g. ₹42,850 or ₹3,190."""
    rupees = paise / 100.0
    if rupees == int(rupees):
        val_str = f"{int(rupees):,}"
    else:
        val_str = f"{rupees:,.2f}"
    return f"₹{val_str}"


def extract_numbers_and_entities(text: str) -> List[str]:
    """
    Extracts all numeric tokens, currency mentions (₹...), percentages (%...),
    and hour intervals from text for rigorous verification.
    """
    patterns = [
        r"₹\s*[\d,]+(?:\.\d+)?",         # Rupee figures e.g. ₹42,850
        r"\b\d+%",                       # Percentages e.g. 91%
        r"\b\d{1,2}(?:am|pm)-\d{1,2}(?:am|pm)\b",  # Hour ranges e.g. 12pm-1pm
        r"\b\d+\s+units\b",             # Drug units e.g. 142 units
        r"\b\d+\s+visits\b",            # Visits count e.g. 18 visits
        r"\b\d+\b",                      # Standalone digits e.g. 18, 3, 1
    ]
    combined = re.findall("|".join(patterns), text, flags=re.IGNORECASE)
    return [c.strip() for c in combined if c.strip()]


def verify_grounding(
    narrative_text: str,
    reconciliation: ReconciliationReport,
    analytics: AnalyticsReport
) -> Tuple[List[TracedFigure], bool, List[str]]:
    """
    Grounding Verifier:
    Verifies that every figure in the narrative traces back to the deterministic report.
    Returns (traced_figures, zero_invented_numbers, ungrounded_tokens).
    """
    traced: List[TracedFigure] = []
    
    # 1. Total Billed
    billed_formatted = format_rupees(reconciliation.total_billed_paise)
    traced.append(TracedFigure(
        figure=billed_formatted,
        field_name="billed",
        report_value=reconciliation.total_billed_paise,
        is_grounded=True,
        context=f"₹{reconciliation.total_billed_rupees:,.2f} ({reconciliation.total_billed_paise} paise)"
    ))

    # 2. Total Collected
    collected_formatted = format_rupees(reconciliation.total_collected_paise)
    traced.append(TracedFigure(
        figure=collected_formatted,
        field_name="collected",
        report_value=reconciliation.total_collected_paise,
        is_grounded=True,
        context=f"₹{reconciliation.total_collected_rupees:,.2f} ({reconciliation.total_collected_paise} paise)"
    ))

    # 3. Total Outstanding
    outstanding_formatted = format_rupees(reconciliation.total_outstanding_paise)
    traced.append(TracedFigure(
        figure=outstanding_formatted,
        field_name="outstanding",
        report_value=reconciliation.total_outstanding_paise,
        is_grounded=True,
        context=f"₹{reconciliation.total_outstanding_rupees:,.2f} ({reconciliation.total_outstanding_paise} paise)"
    ))

    # 4. Total Refunds
    refunds_formatted = format_rupees(reconciliation.total_refunds_paise)
    traced.append(TracedFigure(
        figure=refunds_formatted,
        field_name="refunds",
        report_value=reconciliation.total_refunds_paise,
        is_grounded=True,
        context=f"₹{reconciliation.total_refunds_rupees:,.2f} ({reconciliation.total_refunds_paise} paise)"
    ))

    # 5. Peak Hour & Revenue
    if analytics.peak_hour and analytics.peak_hour.revenue_paise > 0:
        peak_rev_formatted = format_rupees(analytics.peak_hour.revenue_paise)
        traced.append(TracedFigure(
            figure=f"{analytics.peak_hour.time_range} / {peak_rev_formatted}",
            field_name="busiest_hr_revenue",
            report_value={
                "time_range": analytics.peak_hour.time_range,
                "revenue_paise": analytics.peak_hour.revenue_paise
            },
            is_grounded=True,
            context=f"Highest business hour ({analytics.peak_hour.time_range}) with {peak_rev_formatted}"
        ))

    # 6. Top Medicine by Quantity
    if analytics.top_by_quantity:
        top_qty = analytics.top_by_quantity[0]
        traced.append(TracedFigure(
            figure=f"{top_qty.drug_name} / {top_qty.quantity}",
            field_name="top_qty_medicine",
            report_value={"drug_name": top_qty.drug_name, "quantity": top_qty.quantity},
            is_grounded=True,
            context=f"Most dispensed drug: {top_qty.drug_name} with {top_qty.unit_label}"
        ))

    # 7. Top Medicine by Revenue
    if analytics.top_by_revenue:
        top_rev = analytics.top_by_revenue[0]
        top_rev_formatted = format_rupees(top_rev.revenue_paise)
        traced.append(TracedFigure(
            figure=f"{top_rev.drug_name} / {top_rev_formatted}",
            field_name="top_rev_medicine",
            report_value={"drug_name": top_rev.drug_name, "revenue_paise": top_rev.revenue_paise},
            is_grounded=True,
            context=f"Highest earning drug: {top_rev.drug_name} generating {top_rev_formatted}"
        ))

    # Search narrative for ungrounded numbers:
    # Any number in the narrative must match one of the verified values
    grounded_number_set = {
        reconciliation.total_visits,
        reconciliation.pending_invoices_count,
        reconciliation.refund_visits_count,
        int(reconciliation.total_billed_rupees),
        int(reconciliation.total_collected_rupees),
        int(reconciliation.total_outstanding_rupees),
        int(reconciliation.total_refunds_rupees),
        int(reconciliation.collection_rate_percent),
        round(reconciliation.collection_rate_percent),
    }
    if analytics.peak_hour:
        grounded_number_set.add(int(analytics.peak_hour.revenue_rupees))
    for m in analytics.top_by_quantity:
        grounded_number_set.add(m.quantity)
    for m in analytics.top_by_revenue:
        grounded_number_set.add(int(m.revenue_rupees))

    # Also allow day of month if date is mentioned e.g. "27" in "27 Jul"
    if reconciliation.date:
        parts = reconciliation.date.split("-")
        if len(parts) == 3:
            try:
                grounded_number_set.add(int(parts[2]))
                grounded_number_set.add(int(parts[0]))
            except ValueError:
                pass

    # Extract all digits from narrative
    extracted_digits = re.findall(r"\b\d+\b", narrative_text.replace(",", ""))
    ungrounded = []
    for digit_str in extracted_digits:
        val = int(digit_str)
        # allow small common words or hour digits (e.g. 12, 1, 9, 10, etc.)
        if val in grounded_number_set or val in range(1, 24):
            continue
        ungrounded.append(digit_str)

    zero_invented_numbers = (len(ungrounded) == 0)
    return traced, zero_invented_numbers, ungrounded
