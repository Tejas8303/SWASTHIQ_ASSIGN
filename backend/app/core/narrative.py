import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Tuple
from ..models.reports import ReconciliationReport, AnalyticsReport, NarrativeReport
from .grounding import format_rupees, verify_grounding
from ..config import GEMINI_API_KEY, OPENAI_API_KEY, GROQ_API_KEY

logger = logging.getLogger(__name__)

def format_date_short(date_str: str) -> str:
    """Converts '2026-07-27' to '27 Jul'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d %b")
    except Exception:
        return date_str


def generate_deterministic_narrative(
    reconciliation: ReconciliationReport,
    analytics: AnalyticsReport
) -> str:
    """
    Generates a guaranteed 100% grounded WhatsApp summary matching Kaagazy's format.
    Never invents numbers or approximations.
    """
    date_formatted = format_date_short(reconciliation.date)
    clinic_short = reconciliation.clinic_name.replace("Multi-Specialty ", "")

    # Edge Case: 0 visits day
    if reconciliation.total_visits == 0:
        return (
            f"Good evening! Here's today's summary for {clinic_short} ({date_formatted}):\n\n"
            f"No billing transactions or patient visits were logged today.\n"
            f"Total billed: ₹0, collected: ₹0, outstanding: ₹0.\n\n"
            f"Note: cost data wasn't available today, so profit cannot be computed — flagging rather than estimating."
        )

    # Edge Case: Refund-only day
    if reconciliation.total_billed_paise == 0 and reconciliation.total_refunds_paise > 0:
        ref_amt = format_rupees(reconciliation.total_refunds_paise)
        return (
            f"Good evening! Here's today's summary for {clinic_short} ({date_formatted}):\n\n"
            f"₹0 billed across {reconciliation.total_visits} visits.\n"
            f"{ref_amt} was refunded across {reconciliation.refund_visits_count} visits.\n\n"
            f"Note: cost data wasn't available today, so this reflects refund adjustments, not profit — flagging rather than estimating."
        )

    # Standard clinic operating day
    billed_str = format_rupees(reconciliation.total_billed_paise)
    collected_str = format_rupees(reconciliation.total_collected_paise)
    outstanding_str = format_rupees(reconciliation.total_outstanding_paise)
    refunds_str = format_rupees(reconciliation.total_refunds_paise)

    lines = [
        f"Good evening! Here's today's summary for {clinic_short} ({date_formatted}):\n",
        f"{billed_str} billed across {reconciliation.total_visits} visits, {collected_str} collected ({reconciliation.collection_rate_percent:.0f}%).",
    ]

    # Outstanding & refund line
    if reconciliation.total_refunds_paise > 0:
        lines.append(
            f"{outstanding_str} is still outstanding across {reconciliation.pending_invoices_count} visits, and {refunds_str} was refunded on {reconciliation.refund_visits_count} visit."
        )
    elif reconciliation.total_outstanding_paise > 0:
        lines.append(
            f"{outstanding_str} is still outstanding across {reconciliation.pending_invoices_count} visits."
        )
    else:
        lines.append("All bills fully settled today with zero outstanding.")

    # Peak hour line
    if analytics.peak_hour and analytics.peak_hour.revenue_paise > 0:
        peak_rev = format_rupees(analytics.peak_hour.revenue_paise)
        lines.append(f"Busiest hour: {analytics.peak_hour.time_range}, with {peak_rev} in revenue.")

    # Top medicines lines
    if analytics.top_by_quantity:
        top_qty = analytics.top_by_quantity[0]
        lines.append(f"Top mover by quantity: {top_qty.drug_name} ({top_qty.quantity} units).")

    if analytics.top_by_revenue:
        top_rev = analytics.top_by_revenue[0]
        top_rev_str = format_rupees(top_rev.revenue_paise)
        lines.append(f"Top by revenue: {top_rev.drug_name} ({top_rev_str}).")

    # Plain statement on uncomputable metric (profit)
    lines.append("\nNote: cost data wasn't available today, so this is revenue, not profit — flagging rather than estimating.")

    return "\n".join(lines)


def call_llm_for_narrative(
    reconciliation: ReconciliationReport,
    analytics: AnalyticsReport
) -> Optional[str]:
    """
    Attempts to call an external LLM (Gemini or OpenAI or Groq) if API key is present.
    Returns generated string or None on any failure/timeout.
    """
    prompt_payload = {
        "clinic_name": reconciliation.clinic_name,
        "date": reconciliation.date,
        "date_short": format_date_short(reconciliation.date),
        "total_billed_rupees": reconciliation.total_billed_rupees,
        "total_collected_rupees": reconciliation.total_collected_rupees,
        "collection_rate_percent": reconciliation.collection_rate_percent,
        "total_outstanding_rupees": reconciliation.total_outstanding_rupees,
        "pending_invoices_count": reconciliation.pending_invoices_count,
        "total_refunds_rupees": reconciliation.total_refunds_rupees,
        "refund_visits_count": reconciliation.refund_visits_count,
        "total_visits": reconciliation.total_visits,
        "peak_hour": analytics.peak_hour.time_range if analytics.peak_hour else "N/A",
        "peak_revenue_rupees": analytics.peak_hour.revenue_rupees if analytics.peak_hour else 0,
        "top_medicine_by_quantity": {
            "name": analytics.top_by_quantity[0].drug_name,
            "quantity": analytics.top_by_quantity[0].quantity
        } if analytics.top_by_quantity else None,
        "top_medicine_by_revenue": {
            "name": analytics.top_by_revenue[0].drug_name,
            "revenue_rupees": analytics.top_by_revenue[0].revenue_rupees
        } if analytics.top_by_revenue else None,
    }

    system_instruction = (
        "You are Kaagazy's EOD Clinic AI Assistant. Write a concise WhatsApp narrative summary for the clinic owner.\n"
        "STRICT CONSTRAINTS:\n"
        "1. Every single number and figure you write MUST come directly from the provided JSON. Do NOT invent, round, or approximate any figures.\n"
        "2. If cost data is not provided, plainly state that profit cannot be computed from the data provided.\n"
        "3. Keep the tone professional, friendly, and formatted for WhatsApp.\n"
    )

    user_prompt = f"Deterministic EOD Report Data:\n{json.dumps(prompt_payload, indent=2)}\n\nGenerate the WhatsApp summary:"

    # Try Gemini if key exists
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            body = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}]
                    }
                ],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 400}
            }
            res = requests.post(url, json=body, timeout=10)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")

    # Try OpenAI if key exists
    if OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            body = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 400
            }
            res = requests.post(url, headers=headers, json=body, timeout=10)
            if res.status_code == 200:
                data = res.json()
                text = data["choices"][0]["message"]["content"]
                return text.strip()
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")

    return None


def generate_narrative_report(
    reconciliation: ReconciliationReport,
    analytics: AnalyticsReport
) -> NarrativeReport:
    """
    Main narrative generation entrypoint.
    Produces owner-facing summary, validates grounding, and builds trace proof.
    """
    model_used = "deterministic-grounded-engine"
    narrative_text = None

    # Check if external LLM configured and call it
    if GEMINI_API_KEY or OPENAI_API_KEY or GROQ_API_KEY:
        try:
            llm_text = call_llm_for_narrative(reconciliation, analytics)
            if llm_text:
                # Rigorous grounding check on LLM text
                traced, zero_invented, ungrounded = verify_grounding(llm_text, reconciliation, analytics)
                if zero_invented:
                    narrative_text = llm_text
                    model_used = "llm-grounded (gemini/gpt)"
                else:
                    logger.warning(f"LLM produced ungrounded numbers: {ungrounded}. Falling back to deterministic.")
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")

    # If no LLM text or grounding check failed, use deterministic template
    if not narrative_text:
        narrative_text = generate_deterministic_narrative(reconciliation, analytics)
        model_used = "deterministic-grounded-engine"

    # Verify final narrative
    traced_figures, zero_invented, ungrounded = verify_grounding(
        narrative_text, reconciliation, analytics
    )

    grounding_status = "VERIFIED_GROUNDED" if zero_invented else "UNGROUNDED_DETECTED"

    return NarrativeReport(
        narrative_text=narrative_text,
        recipient="Dr. Arvind Mehta • WhatsApp",
        clinic_name=reconciliation.clinic_name,
        date_formatted=format_date_short(reconciliation.date),
        traced_figures=traced_figures,
        grounding_status=grounding_status,
        zero_invented_numbers=zero_invented,
        uncomputable_metrics_noted=["profit (cost price not provided in dataset)"],
        model_used=model_used
    )
