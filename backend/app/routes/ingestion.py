import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Query, status
from ..models.billing import IngestionResult, RowValidationError
from ..core.ingestion import parse_and_validate_billing_log
from ..db.repository import save_visits_batch, save_ingestion_audit, get_latest_audit
from ..config import DEFAULT_CLINIC_ID

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

@router.post("", response_model=IngestionResult)
async def ingest_billing_log(
    payload: List[Dict[str, Any]] = Body(..., description="Raw JSON array of billing visit records"),
    strict: bool = Query(False, description="If true, rejects entire batch if any row is malformed")
):
    """
    Ingests a raw billing log JSON array.
    Validates row-by-row and rejects malformed rows with specific, actionable errors.
    If strict=false, valid rows are persisted while malformed rows are quarantined with error details.
    """
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be a JSON array of visit records"
        )

    valid_records, validation_errors = parse_and_validate_billing_log(payload)
    total_count = len(payload)
    valid_count = len(valid_records)
    rejected_count = len(validation_errors)

    clinic_id = valid_records[0].clinic_id if valid_records else DEFAULT_CLINIC_ID
    visit_date = valid_records[0].timestamp.strftime("%Y-%m-%d") if valid_records else None

    # Handle strict mode rejection
    if strict and rejected_count > 0:
        save_ingestion_audit(
            clinic_id=clinic_id,
            visit_date=visit_date,
            filename="strict_batch",
            total_rows=total_count,
            valid_count=0,
            rejected_count=rejected_count,
            errors=[e.model_dump() for e in validation_errors]
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Strict ingestion rejected batch: {rejected_count} malformed rows detected.",
                "errors": [e.model_dump() for e in validation_errors]
            }
        )

    # Persist valid records atomically
    if valid_records and visit_date:
        save_visits_batch(valid_records, clinic_id, visit_date)

    # Save audit record
    save_ingestion_audit(
        clinic_id=clinic_id,
        visit_date=visit_date,
        filename="json_payload",
        total_rows=total_count,
        valid_count=valid_count,
        rejected_count=rejected_count,
        errors=[e.model_dump() for e in validation_errors]
    )

    if rejected_count == 0:
        status_val = "success"
        msg = f"Successfully ingested {valid_count} visits."
    elif valid_count > 0:
        status_val = "partial_success"
        msg = f"Ingested {valid_count} valid visits; rejected {rejected_count} malformed rows with actionable errors."
    else:
        status_val = "rejected"
        msg = f"All {rejected_count} rows were rejected due to validation errors."

    return IngestionResult(
        clinic_id=clinic_id,
        date=visit_date,
        total_rows=total_count,
        valid_rows_count=valid_count,
        rejected_rows_count=rejected_count,
        errors=validation_errors,
        status=status_val,
        message=msg
    )


@router.post("/file", response_model=IngestionResult)
async def upload_billing_log_file(
    file: UploadFile = File(..., description="JSON file containing daily billing log array"),
    strict: bool = Query(False, description="Strict validation mode")
):
    """Uploads a billing log file (.json)."""
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content must be a JSON array of visit records"
        )

    valid_records, validation_errors = parse_and_validate_billing_log(data)
    total_count = len(data)
    valid_count = len(valid_records)
    rejected_count = len(validation_errors)

    clinic_id = valid_records[0].clinic_id if valid_records else DEFAULT_CLINIC_ID
    visit_date = valid_records[0].timestamp.strftime("%Y-%m-%d") if valid_records else None

    if strict and rejected_count > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"File contains {rejected_count} malformed rows.",
                "errors": [e.model_dump() for e in validation_errors]
            }
        )

    if valid_records and visit_date:
        save_visits_batch(valid_records, clinic_id, visit_date)

    save_ingestion_audit(
        clinic_id=clinic_id,
        visit_date=visit_date,
        filename=file.filename,
        total_rows=total_count,
        valid_count=valid_count,
        rejected_count=rejected_count,
        errors=[e.model_dump() for e in validation_errors]
    )

    if rejected_count == 0:
        status_val = "success"
        msg = f"Successfully ingested {valid_count} visits from {file.filename}."
    elif valid_count > 0:
        status_val = "partial_success"
        msg = f"Ingested {valid_count} valid visits; {rejected_count} malformed rows rejected from {file.filename}."
    else:
        status_val = "rejected"
        msg = f"All {rejected_count} rows in {file.filename} failed validation."

    return IngestionResult(
        clinic_id=clinic_id,
        date=visit_date,
        total_rows=total_count,
        valid_rows_count=valid_count,
        rejected_rows_count=rejected_count,
        errors=validation_errors,
        status=status_val,
        message=msg
    )


@router.get("/audit/latest")
async def get_latest_ingestion_audit(
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD")
):
    """Retrieves the most recent audit log for diagnostic display."""
    audit = get_latest_audit(visit_date=date)
    return audit or {"message": "No ingestion audits found"}
