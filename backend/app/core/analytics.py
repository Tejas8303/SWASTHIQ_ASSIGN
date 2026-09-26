from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from ..models.billing import VisitRecord
from ..models.reports import (
    AnalyticsReport,
    HourlyRevenue,
    PeakHourInfo,
    MedicineQuantityRanking,
    MedicineRevenueRanking
)

def format_hour_label(hour: int) -> str:
    """Formats 0-23 hour as e.g. '9am', '12pm', '1pm'."""
    if hour == 0:
        return "12am"
    elif hour < 12:
        return f"{hour}am"
    elif hour == 12:
        return "12pm"
    else:
        return f"{hour - 12}pm"


def format_hour_range(hour: int) -> str:
    """Formats hour interval as e.g. '12pm-1pm', '9am-10am'."""
    start = format_hour_label(hour)
    end = format_hour_label((hour + 1) % 24)
    return f"{start}-{end}"


def compute_analytics(
    visits: List[VisitRecord],
    clinic_id: str = "CLN-KNP-014",
    date_str: str = ""
) -> AnalyticsReport:
    """
    Computes deterministic analytics:
    - Revenue by hour-of-day
    - Identification of peak business hour
    - Two distinct medicine rankings: by quantity and by revenue
    Never calls an LLM.
    """
    # 1. Hourly Revenue Bucketing
    hour_revenue: Dict[int, int] = defaultdict(int)
    hour_visits: Dict[int, int] = defaultdict(int)

    # 2. Medicine Aggregations
    drug_quantities: Dict[str, int] = defaultdict(int)
    drug_revenues: Dict[str, int] = defaultdict(int)

    # Determine hour range to show (from min hour present or 8am-8pm)
    present_hours = set()

    for v in visits:
        hr = v.timestamp.hour
        present_hours.add(hr)
        hour_visits[hr] += 1
        
        # Revenue by hour: using net billed for sales, adjusting for refunds
        if v.is_refund:
            # negative cashflow adjustment
            hour_revenue[hr] += v.amount_paid_paise
        else:
            hour_revenue[hr] += v.net_billed_paise
            
            # Aggregate medicine movement from sales
            for item in v.line_items:
                drug_quantities[item.drug_name] += item.qty
                drug_revenues[item.drug_name] += item.total_price_paise

    # Establish full range of business hours to display
    if present_hours:
        min_hr = min(min(present_hours), 9)
        max_hr = max(max(present_hours), 18)
    else:
        min_hr = 9
        max_hr = 18

    # Find peak hour
    peak_hour_val: Optional[int] = None
    max_rev = -1
    for hr in range(min_hr, max_hr + 1):
        rev = hour_revenue.get(hr, 0)
        if rev > max_rev:
            max_rev = rev
            peak_hour_val = hr

    hourly_list: List[HourlyRevenue] = []
    for hr in range(min_hr, max_hr + 1):
        rev_paise = max(0, hour_revenue.get(hr, 0))  # display as >= 0 on chart
        v_count = hour_visits.get(hr, 0)
        is_peak = (hr == peak_hour_val and rev_paise > 0)
        hourly_list.append(
            HourlyRevenue(
                hour=hr,
                hour_label=format_hour_label(hr),
                time_range_label=format_hour_range(hr),
                revenue_paise=rev_paise,
                revenue_rupees=round(rev_paise / 100.0, 2),
                visits_count=v_count,
                is_peak=is_peak
            )
        )

    peak_info: Optional[PeakHourInfo] = None
    if peak_hour_val is not None and max_rev > 0:
        peak_info = PeakHourInfo(
            hour=peak_hour_val,
            time_range=format_hour_range(peak_hour_val),
            revenue_paise=max_rev,
            revenue_rupees=round(max_rev / 100.0, 2)
        )

    # 3. Top Medicines by Quantity (Descending)
    sorted_by_qty = sorted(
        drug_quantities.items(),
        key=lambda x: (x[1], drug_revenues[x[0]]),
        reverse=True
    )
    top_by_qty: List[MedicineQuantityRanking] = [
        MedicineQuantityRanking(
            rank=i + 1,
            drug_name=drug,
            quantity=qty,
            unit_label=f"{qty} units"
        )
        for i, (drug, qty) in enumerate(sorted_by_qty[:10])
    ]

    # 4. Top Medicines by Revenue (Descending)
    sorted_by_rev = sorted(
        drug_revenues.items(),
        key=lambda x: (x[1], drug_quantities[x[0]]),
        reverse=True
    )
    top_by_rev: List[MedicineRevenueRanking] = [
        MedicineRevenueRanking(
            rank=i + 1,
            drug_name=drug,
            revenue_paise=rev,
            revenue_rupees=round(rev / 100.0, 2)
        )
        for i, (drug, rev) in enumerate(sorted_by_rev[:10])
    ]

    return AnalyticsReport(
        clinic_id=clinic_id,
        date=date_str,
        hourly_revenue=hourly_list,
        peak_hour=peak_info,
        top_by_quantity=top_by_qty,
        top_by_revenue=top_by_rev
    )
