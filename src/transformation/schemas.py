"""
Data Contract & Validation Schemas using Pydantic v2.
Enforces strict field types, non-null constraints, positive NAV checks, and ISO date formatting.
"""

import datetime as dt
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class SchemeMetaSchema(BaseModel):
    """
    Schema validation contract for Mutual Fund Scheme Metadata.
    """
    scheme_code: int = Field(..., description="Unique AMFI Scheme Code (positive integer)", gt=0)
    scheme_name: str = Field(..., description="Official Scheme Name", min_length=2)
    category: str = Field(default="Equity Scheme - Other", description="Standardized Scheme Category")
    fund_house: str = Field(default="Unknown AMC", description="Asset Management Company (AMC)")
    isin_payout: Optional[str] = Field(default=None, description="ISIN Dividend Payout / Growth")
    isin_reinvest: Optional[str] = Field(default=None, description="ISIN Dividend Reinvestment")

    @field_validator("scheme_name", "category", "fund_house", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v or "").strip()


class DailyNAVSchema(BaseModel):
    """
    Schema validation contract for Daily Net Asset Value (NAV) records.
    """
    scheme_code: int = Field(..., description="AMFI Scheme Code", gt=0)
    date: dt.date = Field(..., description="Trading Date (YYYY-MM-DD)")
    nav: float = Field(..., description="Net Asset Value (strictly positive)", gt=0.0)

    @field_validator("nav", mode="before")
    @classmethod
    def parse_positive_nav(cls, v: Any) -> float:
        try:
            val = float(v)
            if val <= 0:
                raise ValueError(f"NAV must be greater than zero, got {val}")
            return val
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid NAV value '{v}': {exc}") from exc


class BenchmarkSchema(BaseModel):
    """
    Schema validation contract for Historical Benchmark Index records.
    """
    index_name: str = Field(..., description="Benchmark Index Name", min_length=2)
    date: dt.date = Field(..., description="Trading Date (YYYY-MM-DD)")
    close_value: float = Field(..., description="Index Closing Value (strictly positive)", gt=0.0)
