from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PaymentModeSummary(BaseModel):
    mode: str
    billed_paise: int
    collected_paise: int
    outstanding_paise: int
    refunds_paise: int
    billed_rupees: float
    collected_rupees: float
    outstanding_rupees: float
    refunds_rupees: float


class ReconciliationReport(BaseModel):
    clinic_id: str
    clinic_name: str
    clinic_location: str
    date: str  # YYYY-MM-DD
    total_billed_paise: int
    total_collected_paise: int
    total_outstanding_paise: int
    total_refunds_paise: int
    total_billed_rupees: float
    total_collected_rupees: float
    total_outstanding_rupees: float
    total_refunds_rupees: float
    total_visits: int
    collection_rate_percent: float
    pending_invoices_count: int
    refund_visits_count: int
    by_payment_mode: Dict[str, PaymentModeSummary]


class HourlyRevenue(BaseModel):
    hour: int  # 0 to 23
    hour_label: str  # "9am", "12pm", "1pm"
    time_range_label: str  # "12pm-1pm"
    revenue_paise: int
    revenue_rupees: float
    visits_count: int
    is_peak: bool = False


class PeakHourInfo(BaseModel):
    hour: int
    time_range: str
    revenue_paise: int
    revenue_rupees: float


class MedicineQuantityRanking(BaseModel):
    rank: int
    drug_name: str
    quantity: int
    unit_label: str


class MedicineRevenueRanking(BaseModel):
    rank: int
    drug_name: str
    revenue_paise: int
    revenue_rupees: float


class AnalyticsReport(BaseModel):
    clinic_id: str
    date: str
    hourly_revenue: List[HourlyRevenue]
    peak_hour: Optional[PeakHourInfo]
    top_by_quantity: List[MedicineQuantityRanking]
    top_by_revenue: List[MedicineRevenueRanking]


class TracedFigure(BaseModel):
    figure: str
    field_name: str
    report_value: Any
    is_grounded: bool = True
    context: Optional[str] = None


class NarrativeReport(BaseModel):
    narrative_text: str
    recipient: str
    clinic_name: str
    date_formatted: str
    traced_figures: List[TracedFigure]
    grounding_status: str  # "VERIFIED_GROUNDED", "UNGROUNDED_DETECTED", "FALLBACK_USED"
    zero_invented_numbers: bool
    uncomputable_metrics_noted: List[str]
    model_used: str


class EODBundleResponse(BaseModel):
    clinic_id: str
    date: str
    reconciliation: ReconciliationReport
    analytics: AnalyticsReport
    narrative: NarrativeReport
    ingestion_summary: Optional[Dict[str, Any]] = None
