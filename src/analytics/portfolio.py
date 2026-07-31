"""
Investor Portfolio Analytics & XIRR Engine.
Computes non-periodic Extended Internal Rate of Return (XIRR),
portfolio valuation, unrealized PnL, and asset allocation drift analysis.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import optimize

from src.database.db_manager import DatabaseManager, get_db_manager
from src.database.query_bank import QueryBank
from src.utils.logger import get_logger

logger = get_logger(__name__)


def xirr(cashflows: List[Tuple[date, float]], guess: float = 0.10) -> float:
    """
    Calculates Extended Internal Rate of Return (XIRR) for irregular non-periodic cashflows.
    
    Args:
        cashflows: List of (date, amount) tuples.
                   Outflows (investments) must be negative numbers.
                   Inflows (current market value / redemptions) must be positive numbers.
        guess: Initial rate guess (default 10% = 0.10).
        
    Returns:
        float: Annualized XIRR decimal (e.g., 0.154 = 15.4%). Returns 0.0 if calculation fails.
    """
    if len(cashflows) < 2:
        return 0.0

    # Ensure cashflows are sorted chronologically
    sorted_cf = sorted(cashflows, key=lambda x: x[0])
    
    dates = [cf[0] for cf in sorted_cf]
    amounts = [cf[1] for cf in sorted_cf]

    # Verify at least one negative (investment) and one positive (value) cashflow exists
    has_negative = any(amt < 0 for amt in amounts)
    has_positive = any(amt > 0 for amt in amounts)
    if not (has_negative and has_positive):
        return 0.0

    d0 = dates[0]
    days = np.array([(d - d0).days for d in dates], dtype=float)
    amounts_arr = np.array(amounts, dtype=float)

    def npv(r: float) -> float:
        if r <= -0.999:  # Avoid division by zero or complex numbers
            return 1e10
        return np.sum(amounts_arr / ((1.0 + r) ** (days / 365.25)))

    def npv_prime(r: float) -> float:
        if r <= -0.999:
            return 1e10
        return np.sum(-amounts_arr * (days / 365.25) / ((1.0 + r) ** ((days / 365.25) + 1.0)))

    try:
        # Try Newton-Raphson method first for speed
        rate = optimize.newton(npv, guess, fprime=npv_prime, maxiter=100, tol=1e-6)
        return float(rate)
    except (RuntimeError, OverflowError, ValueError):
        try:
            # Fallback to Brent's bounded root finder if Newton fails
            res = optimize.root_scalar(npv, bracket=[-0.99, 10.0], method="brentq")
            if res.converged:
                return float(res.root)
        except Exception:
            pass

    return 0.0


class PortfolioTracker:
    """
    Portfolio Analytics Engine for tracking investor holdings, XIRR, and asset allocation drift.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_mgr = db_manager or get_db_manager()
        self.query_bank = QueryBank(self.db_mgr)

    def get_investor_xirr(self, investor_id: int) -> float:
        """
        Calculates overall portfolio XIRR for a specific investor based on transaction history and current NAVs.
        """
        sql = """
        WITH latest_nav AS (
            SELECT 
                f.scheme_code,
                f.nav AS current_nav,
                f.date_id,
                ROW_NUMBER() OVER (PARTITION BY f.scheme_code ORDER BY f.date_id DESC) AS rn
            FROM fact_daily_nav f
        )
        SELECT 
            d.full_date,
            t.total_amount,
            t.units,
            t.scheme_code,
            ln.current_nav,
            d_latest.full_date AS latest_date
        FROM fact_transactions t
        JOIN dim_date d ON t.date_id = d.date_id
        JOIN latest_nav ln ON t.scheme_code = ln.scheme_code AND ln.rn = 1
        JOIN dim_date d_latest ON ln.date_id = d_latest.date_id
        WHERE t.investor_id = :investor_id
        ORDER BY d.full_date ASC;
        """

        with self.db_mgr.get_session() as session:
            df_txns = pd.read_sql(sql, session.bind, params={"investor_id": investor_id})

        if df_txns.empty:
            return 0.0

        cashflows: List[Tuple[date, float]] = []

        # 1. Outflows (Investments as negative numbers)
        for _, row in df_txns.iterrows():
            dt = pd.to_datetime(row["full_date"]).date()
            amount = -abs(float(row["total_amount"]))
            cashflows.append((dt, amount))

        # 2. Inflow (Current total portfolio valuation as positive number on latest date)
        latest_date = pd.to_datetime(df_txns["latest_date"].iloc[0]).date()
        total_current_value = (df_txns["units"] * df_txns["current_nav"]).sum()
        cashflows.append((latest_date, float(total_current_value)))

        xirr_val = xirr(cashflows)
        logger.info("Computed Portfolio XIRR for Investor ID %d: %.2f%%", investor_id, xirr_val * 100)
        return xirr_val

    def get_portfolio_summary_report(self, investor_id: int) -> Dict[str, Any]:
        """
        Generates comprehensive investor portfolio report including total valuation,
        unrealized PnL, XIRR %, scheme breakdown, and asset allocation.
        """
        sql = """
        WITH latest_nav AS (
            SELECT 
                f.scheme_code,
                f.nav AS current_nav,
                f.date_id,
                ROW_NUMBER() OVER (PARTITION BY f.scheme_code ORDER BY f.date_id DESC) AS rn
            FROM fact_daily_nav f
        )
        SELECT 
            i.investor_id,
            i.investor_name,
            i.risk_profile,
            s.scheme_code,
            s.scheme_name,
            c.category_name,
            c.asset_class,
            SUM(t.total_amount) AS invested_amount,
            SUM(t.units) AS units_held,
            ln.current_nav,
            SUM(t.units) * ln.current_nav AS current_value
        FROM fact_transactions t
        JOIN dim_investor i ON t.investor_id = i.investor_id
        JOIN dim_scheme s ON t.scheme_code = s.scheme_code
        JOIN dim_category c ON s.category_id = c.category_id
        JOIN latest_nav ln ON s.scheme_code = ln.scheme_code AND ln.rn = 1
        WHERE t.investor_id = :investor_id
        GROUP BY i.investor_id, i.investor_name, i.risk_profile, s.scheme_code, s.scheme_name, c.category_name, c.asset_class, ln.current_nav;
        """

        with self.db_mgr.get_session() as session:
            df_holdings = pd.read_sql(sql, session.bind, params={"investor_id": investor_id})

        if df_holdings.empty:
            return {}

        total_invested = float(df_holdings["invested_amount"].sum())
        total_current_val = float(df_holdings["current_value"].sum())
        total_pnl = total_current_val - total_invested
        total_return_pct = (total_pnl / total_invested * 100.0) if total_invested > 0 else 0.0

        portfolio_xirr = self.get_investor_xirr(investor_id)

        # Asset Allocation breakdown
        asset_alloc = (
            df_holdings.groupby("asset_class")["current_value"]
            .sum()
            .reset_index()
        )
        asset_alloc["allocation_pct"] = round((asset_alloc["current_value"] / total_current_val) * 100.0, 2)

        # Holdings list
        holdings_list = []
        for _, row in df_holdings.iterrows():
            holdings_list.append({
                "scheme_code": int(row["scheme_code"]),
                "scheme_name": str(row["scheme_name"]),
                "category_name": str(row["category_name"]),
                "asset_class": str(row["asset_class"]),
                "invested_amount": round(float(row["invested_amount"]), 2),
                "units_held": round(float(row["units_held"]), 4),
                "current_nav": round(float(row["current_nav"]), 4),
                "current_value": round(float(row["current_value"]), 2),
                "pnl": round(float(row["current_value"] - row["invested_amount"]), 2),
                "return_pct": round(float((row["current_value"] - row["invested_amount"]) / row["invested_amount"] * 100), 2) if row["invested_amount"] > 0 else 0.0,
                "weight_pct": round(float(row["current_value"] / total_current_val * 100), 2) if total_current_val > 0 else 0.0,
            })

        return {
            "investor_id": investor_id,
            "investor_name": str(df_holdings["investor_name"].iloc[0]),
            "risk_profile": str(df_holdings["risk_profile"].iloc[0]),
            "total_invested_amount": round(total_invested, 2),
            "total_current_value": round(total_current_val, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "xirr_pct": round(portfolio_xirr * 100.0, 2),
            "asset_allocation": asset_alloc.to_dict(orient="records"),
            "holdings": holdings_list,
        }
