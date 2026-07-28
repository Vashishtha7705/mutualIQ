"""
SQL Query Bank & Business Reporting Engine.
Contains optimized analytical SQL queries utilizing Window Functions, CTEs,
and Multi-Table JOINs for mutual fund performance and portfolio intelligence.
"""

from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import text

from src.database.db_manager import DatabaseManager, get_db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class QueryBank:
    """
    Business Intelligence & SQL Query Bank Executor.
    Executes analytical queries against Star-Schema database tables and returns Pandas DataFrames.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_mgr = db_manager or get_db_manager()

    def get_top_performing_schemes(self, top_n: int = 5) -> pd.DataFrame:
        """
        Report 1: Ranks top-performing schemes per category using SQL Window Functions (ROW_NUMBER / RANK).
        """
        sql = """
        WITH latest_nav AS (
            SELECT 
                f.scheme_code,
                f.nav,
                f.cumulative_return,
                f.rolling_30d_volatility,
                f.date_id,
                ROW_NUMBER() OVER (PARTITION BY f.scheme_code ORDER BY f.date_id DESC) AS rn
            FROM fact_daily_nav f
        ),
        ranked_schemes AS (
            SELECT 
                s.scheme_code,
                s.scheme_name,
                c.category_name,
                a.fund_house_name,
                ln.nav AS latest_nav,
                ln.cumulative_return,
                ln.rolling_30d_volatility,
                d.full_date AS as_of_date,
                ROW_NUMBER() OVER (
                    PARTITION BY c.category_name 
                    ORDER BY ln.cumulative_return DESC
                ) AS category_rank
            FROM latest_nav ln
            JOIN dim_scheme s ON ln.scheme_code = s.scheme_code
            JOIN dim_category c ON s.category_id = c.category_id
            JOIN dim_amc a ON s.amc_id = a.amc_id
            JOIN dim_date d ON ln.date_id = d.date_id
            WHERE ln.rn = 1
        )
        SELECT 
            category_rank,
            category_name,
            scheme_code,
            scheme_name,
            fund_house_name,
            latest_nav,
            ROUND(cumulative_return * 100, 2) AS cumulative_return_pct,
            ROUND(rolling_30d_volatility * 100, 2) AS volatility_30d_pct,
            as_of_date
        FROM ranked_schemes
        WHERE category_rank <= :top_n
        ORDER BY category_name, category_rank;
        """

        logger.info("Executing SQL Query: Top %d schemes per category...", top_n)
        with self.db_mgr.get_session() as session:
            result = session.execute(text(sql), {"top_n": top_n})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

        logger.info("Retrieved %d records for Top Performing Schemes Report", len(df))
        return df

    def get_category_performance_summary(self) -> pd.DataFrame:
        """
        Report 2: Category-wide aggregated statistics (Scheme Count, Avg Return, Avg Volatility).
        """
        sql = """
        WITH latest_nav AS (
            SELECT 
                f.scheme_code,
                f.nav,
                f.daily_return,
                f.cumulative_return,
                f.rolling_30d_volatility,
                ROW_NUMBER() OVER (PARTITION BY f.scheme_code ORDER BY f.date_id DESC) AS rn
            FROM fact_daily_nav f
        )
        SELECT 
            c.category_name,
            c.asset_class,
            COUNT(DISTINCT s.scheme_code) AS total_schemes,
            ROUND(AVG(ln.nav), 2) AS avg_nav,
            ROUND(MIN(ln.nav), 2) AS min_nav,
            ROUND(MAX(ln.nav), 2) AS max_nav,
            ROUND(AVG(ln.cumulative_return) * 100, 2) AS avg_cumulative_return_pct,
            ROUND(AVG(ln.rolling_30d_volatility) * 100, 2) AS avg_volatility_pct
        FROM latest_nav ln
        JOIN dim_scheme s ON ln.scheme_code = s.scheme_code
        JOIN dim_category c ON s.category_id = c.category_id
        WHERE ln.rn = 1
        GROUP BY c.category_name, c.asset_class
        ORDER BY avg_cumulative_return_pct DESC;
        """

        logger.info("Executing SQL Query: Category Performance Summary...")
        with self.db_mgr.get_session() as session:
            result = session.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

        logger.info("Retrieved Category Summary Report (%d categories)", len(df))
        return df

    def get_scheme_vs_benchmark_comparison(self, scheme_code: int, index_name: str = "NIFTY_50_TRI") -> pd.DataFrame:
        """
        Report 3: CTE alignment comparing scheme daily returns vs. benchmark index returns.
        """
        sql = """
        WITH scheme_series AS (
            SELECT 
                f.date_id,
                f.nav,
                f.daily_return AS scheme_daily_return,
                f.cumulative_return AS scheme_cumulative_return
            FROM fact_daily_nav f
            WHERE f.scheme_code = :scheme_code
        ),
        benchmark_series AS (
            SELECT 
                b.date_id,
                b.close_value AS benchmark_close,
                b.daily_return AS benchmark_daily_return,
                b.cumulative_return AS benchmark_cumulative_return
            FROM fact_benchmark_index b
            WHERE b.index_name = :index_name
        )
        SELECT 
            d.full_date,
            s.nav AS scheme_nav,
            b.benchmark_close,
            ROUND(s.scheme_daily_return * 100, 4) AS scheme_daily_return_pct,
            ROUND(b.benchmark_daily_return * 100, 4) AS benchmark_daily_return_pct,
            ROUND((s.scheme_daily_return - b.benchmark_daily_return) * 100, 4) AS excess_daily_return_pct,
            ROUND(s.scheme_cumulative_return * 100, 2) AS scheme_cumulative_return_pct,
            ROUND(b.benchmark_cumulative_return * 100, 2) AS benchmark_cumulative_return_pct
        FROM scheme_series s
        JOIN benchmark_series b ON s.date_id = b.date_id
        JOIN dim_date d ON s.date_id = d.date_id
        ORDER BY d.full_date ASC;
        """

        logger.info("Executing SQL Query: Scheme %d vs Benchmark '%s'...", scheme_code, index_name)
        with self.db_mgr.get_session() as session:
            result = session.execute(text(sql), {"scheme_code": scheme_code, "index_name": index_name})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

        logger.info("Retrieved %d daily comparisons for Scheme %d", len(df), scheme_code)
        return df

    def get_investor_portfolio_summary(self) -> pd.DataFrame:
        """
        Report 4: Portfolio Holdings & SIP Cashflow Summary per Investor.
        """
        sql = """
        WITH latest_nav AS (
            SELECT 
                f.scheme_code,
                f.nav AS current_nav,
                ROW_NUMBER() OVER (PARTITION BY f.scheme_code ORDER BY f.date_id DESC) AS rn
            FROM fact_daily_nav f
        ),
        investor_summary AS (
            SELECT 
                i.investor_id,
                i.investor_name,
                i.risk_profile,
                s.scheme_code,
                s.scheme_name,
                COUNT(t.txn_id) AS total_sip_installments,
                SUM(t.total_amount) AS total_invested_amount,
                SUM(t.units) AS total_units_held,
                ROUND(SUM(t.total_amount) / SUM(t.units), 2) AS weighted_avg_purchase_nav,
                ln.current_nav
            FROM fact_transactions t
            JOIN dim_investor i ON t.investor_id = i.investor_id
            JOIN dim_scheme s ON t.scheme_code = s.scheme_code
            JOIN latest_nav ln ON s.scheme_code = ln.scheme_code AND ln.rn = 1
            GROUP BY i.investor_id, i.investor_name, i.risk_profile, s.scheme_code, s.scheme_name, ln.current_nav
        )
        SELECT 
            investor_id,
            investor_name,
            risk_profile,
            scheme_code,
            scheme_name,
            total_sip_installments,
            total_invested_amount,
            ROUND(total_units_held, 4) AS total_units_held,
            weighted_avg_purchase_nav,
            current_nav,
            ROUND(total_units_held * current_nav, 2) AS current_portfolio_value,
            ROUND((total_units_held * current_nav) - total_invested_amount, 2) AS total_profit_loss,
            ROUND((((total_units_held * current_nav) - total_invested_amount) / total_invested_amount) * 100, 2) AS total_return_pct
        FROM investor_summary
        ORDER BY investor_id, total_invested_amount DESC;
        """

        logger.info("Executing SQL Query: Investor Portfolio Summary...")
        with self.db_mgr.get_session() as session:
            result = session.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

        logger.info("Retrieved Investor Portfolio Report (%d holdings)", len(df))
        return df

    def get_rolling_trend_analysis(self, scheme_code: int, window_days: int = 30) -> pd.DataFrame:
        """
        Report 5: Rolling Moving Average & Volatility trend analysis via SQL Window Functions.
        """
        sql = """
        SELECT 
            d.full_date,
            f.nav,
            f.daily_return,
            ROUND(AVG(f.daily_return) OVER (
                PARTITION BY f.scheme_code 
                ORDER BY f.date_id 
                ROWS BETWEEN :window_days PRECEDING AND CURRENT ROW
            ) * 100, 4) AS rolling_avg_daily_return_pct,
            ROUND(AVG(f.nav) OVER (
                PARTITION BY f.scheme_code 
                ORDER BY f.date_id 
                ROWS BETWEEN :window_days PRECEDING AND CURRENT ROW
            ), 2) AS rolling_moving_avg_nav
        FROM fact_daily_nav f
        JOIN dim_date d ON f.date_id = d.date_id
        WHERE f.scheme_code = :scheme_code
        ORDER BY d.full_date ASC;
        """

        logger.info("Executing SQL Query: Rolling %d-day Trend Analysis for Scheme %d...", window_days, scheme_code)
        with self.db_mgr.get_session() as session:
            result = session.execute(text(sql), {"scheme_code": scheme_code, "window_days": window_days})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

        logger.info("Retrieved %d trend rows for Scheme %d", len(df), scheme_code)
        return df
