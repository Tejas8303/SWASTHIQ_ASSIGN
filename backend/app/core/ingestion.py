import re
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from ..models.billing import VisitRecord, LineItem, PaymentMode, RowValidationError

# Drug name alias normalization dictionary for edge cases
DRUG_NAME_ALIASES = {
    "PARACETMOL": "PARACETAMOL",
    "PARACETAMOL": "PARACETAMOL",
    "AMOXICILLIN": "AMOXICILLIN",
    "METFORMIN": "METFORMIN",
    "ATORVASTATIN": "ATORVASTATIN",
    "OMEPRAZOLE": "OMEPRAZOLE",
}

def normalize_drug_name(raw_name: str) -> str:
    """Normalizes drug names, fixing known typos and whitespace variations."""
    cleaned = raw_name.strip().upper()
    return DRUG_NAME_ALIASES.get(cleaned, cleaned)


def parse_and_validate_billing_log(
    raw_data: Any
) -> Tuple[List[VisitRecord], List[RowValidationError]]:
    """
    Parses and validates a raw billing log JSON array.
    Rejects malformed rows with specific, actionable errors without crashing or throwing generic 500s.
    Returns (valid_records, validation_errors).
    """
    if not isinstance(raw_data, list):
        return [], [
            RowValidationError(
                row_index=0,
                visit_id=None,
                field="root",
                error_message="Payload must be a JSON array of visit records",
                raw_data={"type": str(type(raw_data))}
            )
        ]

    valid_records: List[VisitRecord] = []
    errors: List[RowValidationError] = []

    for index, row in enumerate(raw_data):
        if not isinstance(row, dict):
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=None,
                    field="row",
                    error_message=f"Row {index} is not a valid JSON object",
                    raw_data={"content": str(row)}
                )
            )
            continue

        visit_id = row.get("visit_id")
        
        # 1. Validate required string fields
        clinic_id = row.get("clinic_id")
        if not clinic_id or not isinstance(clinic_id, str) or not clinic_id.strip():
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="clinic_id",
                    error_message="Missing or empty required string field 'clinic_id'",
                    raw_data=row
                )
            )
            continue

        if not visit_id or not isinstance(visit_id, str) or not visit_id.strip():
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=None,
                    field="visit_id",
                    error_message="Missing or empty required string field 'visit_id'",
                    raw_data=row
                )
            )
            continue

        # 2. Validate timestamp
        raw_ts = row.get("timestamp")
        if not raw_ts:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="timestamp",
                    error_message="Missing required field 'timestamp'",
                    raw_data=row
                )
            )
            continue
        
        try:
            # Handle ISO 8601 UTC timestamp
            if isinstance(raw_ts, str):
                cleaned_ts = raw_ts.replace("Z", "+00:00")
                parsed_timestamp = datetime.fromisoformat(cleaned_ts)
            elif isinstance(raw_ts, datetime):
                parsed_timestamp = raw_ts
            else:
                raise ValueError("Timestamp must be an ISO 8601 string")
        except Exception as e:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="timestamp",
                    error_message=f"Invalid ISO 8601 timestamp '{raw_ts}': {str(e)}",
                    raw_data=row
                )
            )
            continue

        # 3. Validate payment_mode
        payment_mode_raw = row.get("payment_mode")
        if payment_mode_raw is None:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="payment_mode",
                    error_message="Missing required field 'payment_mode' (must be 'cash', 'card', or 'upi')",
                    raw_data=row
                )
            )
            continue
        
        if not isinstance(payment_mode_raw, str) or payment_mode_raw.lower() not in ["cash", "card", "upi"]:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="payment_mode",
                    error_message=f"Invalid payment_mode '{payment_mode_raw}'. Allowed values: cash, card, upi",
                    raw_data=row
                )
            )
            continue
        payment_mode = PaymentMode(payment_mode_raw.lower())

        # 4. Validate is_refund
        is_refund_raw = row.get("is_refund", False)
        if not isinstance(is_refund_raw, bool):
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="is_refund",
                    error_message=f"is_refund must be a boolean (true or false), got {type(is_refund_raw).__name__}",
                    raw_data=row
                )
            )
            continue
        is_refund = is_refund_raw

        # 5. Validate amount_paid_paise
        amount_paid_raw = row.get("amount_paid_paise")
        if amount_paid_raw is None:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="amount_paid_paise",
                    error_message="Missing required field 'amount_paid_paise'",
                    raw_data=row
                )
            )
            continue
        
        if not isinstance(amount_paid_raw, int) or isinstance(amount_paid_raw, bool):
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="amount_paid_paise",
                    error_message=f"amount_paid_paise must be an integer paise amount, got {type(amount_paid_raw).__name__} ({amount_paid_raw})",
                    raw_data=row
                )
            )
            continue

        if is_refund and amount_paid_raw > 0:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="amount_paid_paise",
                    error_message=f"A refund row (is_refund=true) must have negative or zero amount_paid_paise, got {amount_paid_raw}",
                    raw_data=row
                )
            )
            continue

        if not is_refund and amount_paid_raw < 0:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="amount_paid_paise",
                    error_message=f"Non-refund visit cannot have negative amount_paid_paise ({amount_paid_raw})",
                    raw_data=row
                )
            )
            continue

        # 6. Validate discount_paise
        discount_raw = row.get("discount_paise", 0)
        if not isinstance(discount_raw, int) or isinstance(discount_raw, bool):
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="discount_paise",
                    error_message=f"discount_paise must be an integer paise amount, got {type(discount_raw).__name__}",
                    raw_data=row
                )
            )
            continue
        if discount_raw < 0:
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="discount_paise",
                    error_message=f"discount_paise cannot be negative, got {discount_raw}",
                    raw_data=row
                )
            )
            continue

        # 7. Validate line_items
        line_items_raw = row.get("line_items")
        if not isinstance(line_items_raw, list):
            errors.append(
                RowValidationError(
                    row_index=index,
                    visit_id=visit_id,
                    field="line_items",
                    error_message="line_items must be a non-empty array of items",
                    raw_data=row
                )
            )
            continue

        valid_items: List[LineItem] = []
        item_error_found = False
        for it_idx, item in enumerate(line_items_raw):
            if not isinstance(item, dict):
                errors.append(
                    RowValidationError(
                        row_index=index,
                        visit_id=visit_id,
                        field=f"line_items[{it_idx}]",
                        error_message="Line item must be a dictionary with drug_name, qty, unit_price_paise",
                        raw_data=row
                    )
                )
                item_error_found = True
                break
            
            raw_drug = item.get("drug_name")
            qty = item.get("qty")
            unit_price = item.get("unit_price_paise")

            if not raw_drug or not isinstance(raw_drug, str) or not raw_drug.strip():
                errors.append(
                    RowValidationError(
                        row_index=index,
                        visit_id=visit_id,
                        field=f"line_items[{it_idx}].drug_name",
                        error_message="drug_name is required and cannot be empty",
                        raw_data=row
                    )
                )
                item_error_found = True
                break
            
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                errors.append(
                    RowValidationError(
                        row_index=index,
                        visit_id=visit_id,
                        field=f"line_items[{it_idx}].qty",
                        error_message=f"qty must be a positive integer, got {qty}",
                        raw_data=row
                    )
                )
                item_error_found = True
                break

            if not isinstance(unit_price, int) or isinstance(unit_price, bool) or unit_price < 0:
                errors.append(
                    RowValidationError(
                        row_index=index,
                        visit_id=visit_id,
                        field=f"line_items[{it_idx}].unit_price_paise",
                        error_message=f"unit_price_paise must be a non-negative integer paise amount, got {unit_price}",
                        raw_data=row
                    )
                )
                item_error_found = True
                break

            normalized_name = normalize_drug_name(raw_drug)
            valid_items.append(
                LineItem(
                    drug_name=normalized_name,
                    qty=qty,
                    unit_price_paise=unit_price
                )
            )

        if item_error_found:
            continue

        # Create validated record
        record = VisitRecord(
            clinic_id=clinic_id.strip(),
            visit_id=visit_id.strip(),
            timestamp=parsed_timestamp,
            doctor_id=row.get("doctor_id"),
            line_items=valid_items,
            payment_mode=payment_mode,
            amount_paid_paise=amount_paid_raw,
            discount_paise=discount_raw,
            is_refund=is_refund
        )
        valid_records.append(record)

    return valid_records, errors
