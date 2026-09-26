from enum import Enum
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class PaymentMode(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"


class LineItem(BaseModel):
    drug_name: str = Field(..., description="Name of the medicine")
    qty: int = Field(..., description="Quantity of medicine prescribed/sold")
    unit_price_paise: int = Field(..., description="Unit price in integer paise")

    @field_validator("drug_name")
    @classmethod
    def validate_drug_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("drug_name cannot be empty")
        return s

    @field_validator("qty")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("qty must be an integer")
        if v <= 0:
            raise ValueError(f"qty must be positive, got {v}")
        return v

    @field_validator("unit_price_paise")
    @classmethod
    def validate_unit_price(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("unit_price_paise must be an integer")
        if v < 0:
            raise ValueError(f"unit_price_paise cannot be negative, got {v}")
        return v

    @property
    def total_price_paise(self) -> int:
        return self.qty * self.unit_price_paise


class VisitRecord(BaseModel):
    clinic_id: str = Field(..., description="Unique clinic identifier")
    visit_id: str = Field(..., description="Unique visit identifier")
    timestamp: datetime = Field(..., description="ISO 8601 UTC timestamp")
    doctor_id: Optional[str] = Field(None, description="Doctor identifier")
    line_items: List[LineItem] = Field(..., description="List of line items in visit")
    payment_mode: PaymentMode = Field(..., description="Payment mode: cash, card, or upi")
    amount_paid_paise: int = Field(..., description="Amount paid in integer paise")
    discount_paise: int = Field(0, description="Discount given in integer paise")
    is_refund: bool = Field(False, description="Whether this visit is a refund adjustment")

    @field_validator("clinic_id", "visit_id")
    @classmethod
    def validate_non_empty_str(cls, v: str, info) -> str:
        s = v.strip()
        if not s:
            raise ValueError(f"{info.field_name} cannot be empty")
        return s

    @field_validator("discount_paise")
    @classmethod
    def validate_discount(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("discount_paise must be an integer")
        if v < 0:
            raise ValueError(f"discount_paise cannot be negative, got {v}")
        return v

    @field_validator("amount_paid_paise")
    @classmethod
    def validate_amount_paid_type(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("amount_paid_paise must be an integer paise amount")
        return v

    @model_validator(mode="after")
    def validate_amounts_and_refund(self) -> "VisitRecord":
        if self.is_refund:
            if self.amount_paid_paise > 0:
                raise ValueError(
                    f"Refund visit must have non-positive amount_paid_paise, got {self.amount_paid_paise}"
                )
        else:
            if self.amount_paid_paise < 0:
                raise ValueError(
                    f"Non-refund visit cannot have negative amount_paid_paise, got {self.amount_paid_paise}"
                )
        return self

    @property
    def gross_total_paise(self) -> int:
        return sum(item.total_price_paise for item in self.line_items)

    @property
    def net_billed_paise(self) -> int:
        if self.is_refund:
            return 0
        return max(0, self.gross_total_paise - self.discount_paise)

    @property
    def outstanding_paise(self) -> int:
        if self.is_refund:
            return 0
        return max(0, self.net_billed_paise - self.amount_paid_paise)

    @property
    def refund_amount_paise(self) -> int:
        if not self.is_refund:
            return 0
        return abs(self.amount_paid_paise)


class RowValidationError(BaseModel):
    row_index: int = Field(..., description="0-indexed position in the uploaded log")
    visit_id: Optional[str] = Field(None, description="Visit ID if identifiable")
    field: str = Field(..., description="Field name that failed validation")
    error_message: str = Field(..., description="Specific, actionable error description")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="The raw offending row data")


class IngestionResult(BaseModel):
    clinic_id: Optional[str] = None
    date: Optional[str] = None
    total_rows: int
    valid_rows_count: int
    rejected_rows_count: int
    errors: List[RowValidationError] = []
    status: str  # "success", "partial_success", "rejected"
    message: str
