# 📈 MutualIQ: Enterprise Mutual Fund Analytics & Portfolio Intelligence Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.1%2B-150458.svg)](https://pandas.pydata.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-D71F00.svg)](https://www.sqlalchemy.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31%2B-FF4B4B.svg)](https://streamlit.io/)
[![Power BI Ready](https://img.shields.io/badge/Power_BI-Star_Schema-F2C811.svg)](https://powerbi.microsoft.com/)
[![Tests](https://img.shields.io/badge/Pytest-38%20Passed-brightgreen.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, production-grade Quantitative Mutual Fund Analytics, Star-Schema Database, Risk Management Engine, XIRR Portfolio Tracker, and Interactive Streamlit Web Platform built from scratch.

---

## 🏗️ System Architecture & Data Pipeline Flow

```
[ AMFI NAV Live API ]       [ MFAPI Historical API ]       [ Index Benchmarks ]
          │                            │                             │
          └────────────────────────────┼─────────────────────────────┘
                                       │ (Module 2: Ingestion Layer)
                                       v
                             [ Raw Data Landing ]
                            (data/raw/ - JSON/TXT)
                                       │
                                       │ (Module 3: Transformation & Pydantic Validation)
                                       v
                          [ Clean Processed Data ]
                           (data/processed/ Parquet)
                                       │
                                       │ (Module 4: Star-Schema Database Loader)
                                       v
                    +------------------------------------+
                    |  SQLite Star Schema Database       |
                    |  - dim_amc                         |
                    |  - dim_category                    |
                    |  - dim_scheme                      |
                    |  - dim_date (YYYYMMDD)             |
                    |  - dim_investor                    |
                    |  - fact_daily_nav                  |
                    |  - fact_benchmark_index            |
                    |  - fact_transactions               |
                    +------------------+-----------------+
                                       │
      ┌────────────────────────────────┼────────────────────────────────┐
      │ (Module 5: Query Bank)         │ (Module 6: Risk Math Engine)  │ (Module 7: XIRR & Portfolio)
      v                                v                                v
[ SQL Business Reports ]     [ 18 Quantitative Metrics ]     [ XIRR & Portfolio Tracker ]
(Top Schemes, Category AUM)  (CAGR, Sharpe, Sortino, VaR)    (Asset Allocation Drift)
      │                                │                                │
      └────────────────────────────────┼────────────────────────────────┘
                                       │
                                       │ (Module 8: Multi-Factor Fund Scorer)
                                       v
                           [ 5-Star Rating Engine ]
                          (Percentile Peer Scoring)
                                       │
      ┌────────────────────────────────┴────────────────────────────────┐
      │ (Module 9: Streamlit Web App)                                   │ (Module 10: Power BI Export)
      v                                                                 v
[ Interactive Streamlit App ]                                [ Power BI Star-Schema CSVs ]
(http://localhost:8501)                                      (data/processed/powerbi/)
```

---

## 🚀 Key Modules Implemented

### Module 1: System Infrastructure & Architecture
- Centralized YAML Configuration Loader (`src/config/config_loader.py`) with dynamic path resolution.
- Enterprise Thread-Safe Logger (`src/utils/logger.py`) featuring colored console logs & rotating file handlers.

### Module 2: Data Ingestion & Extraction Layer
- AMFI Live Bulk NAV Ingestor (`src/ingestion/amfi_ingestor.py`) with exponential backoff retry.
- MFAPI Historical Time-Series Client (`src/ingestion/mfapi_ingestor.py`).
- Market Index Benchmark Ingestor (`src/ingestion/benchmark_ingestor.py`).

### Module 3: Data Cleaning, Validation & Transformation
- Pydantic v2 Contract Validation (`src/transformation/schemas.py`) enforcing positive NAVs ($NAV > 0$).
- Multi-format Date Normalization & Category Standardizer (`src/transformation/cleaner.py`).
- Continuous Calendar Resampling (`ffill`) & Daily Returns Calculator (`src/transformation/enricher.py`).
- High-performance Parquet storage.

### Module 4: Relational Star-Schema Database
- SQLAlchemy 2.0 ORM Dimensional Model (`src/database/models.py`):
  - Dimension Tables: `dim_amc`, `dim_category`, `dim_scheme`, `dim_date` (`YYYYMMDD` integer keys), `dim_investor`.
  - Fact Tables: `fact_daily_nav`, `fact_benchmark_index`, `fact_transactions`.
- SQLite Foreign Key checks & Write-Ahead Logging (WAL Mode).

### Module 5: Optimized SQL Query Bank
- Analytical Business Reports (`src/database/query_bank.py`):
  - Top Performing Schemes via Window Ranking (`ROW_NUMBER() OVER (PARTITION BY category)`).
  - Category AUM & Volatility Aggregations.
  - Scheme vs Benchmark Excess Return CTE Alignment.
  - Investor Portfolio Holdings & Monthly SIP Cashflows.

### Module 6: Quantitative Financial Analytics Engine
- Complete Math Engine (`src/analytics/metrics_engine.py` & `rolling_analytics.py`):
  - **Return Ratios:** CAGR, Absolute Return, 1Y/3Y/5Y Rolling CAGR.
  - **Risk Ratios:** Annualized Volatility ($\sigma$), Downside Volatility ($\sigma_d$), Max Drawdown.
  - **Risk-Adjusted Ratios:** Sharpe Ratio, Sortino Ratio, Calmar Ratio.
  - **CAPM Benchmark Ratios:** Beta ($\beta$), Jensen's Alpha ($\alpha$), Treynor Ratio.
  - **Relative Risk Ratios:** Tracking Error ($TE$), Information Ratio ($IR$).
  - **Tail Loss Risk:** Value at Risk (VaR 95%), Conditional VaR (CVaR / Expected Shortfall).

### Module 7: Investor Analytics & Portfolio XIRR Engine
- Exact Non-Periodic XIRR Solver (`src/analytics/portfolio.py`) using Newton-Raphson optimization ($\sum \frac{C_i}{(1+r)^{\frac{d_i - d_0}{365.25}}} = 0$).
- Portfolio Valuation, Unrealized PnL %, and Asset Allocation Drift Analysis.

### Module 8: Multi-Factor Fund Scoring & Recommendation Engine
- 5-Factor Weighted Composite Scoring Engine (`src/scoring/fund_scorer.py`):
  - 30% Returns + 25% Risk-Adjusted + 20% Downside Safety + 15% Alpha + 10% Volatility.
- Percentile-based 1-Star to 5-Star Rating Framework.
- AI Risk-Profile Matching Engine (`src/scoring/recommendation.py`).

### Module 9: Multi-Page Streamlit Web Application
- Custom Dark Glassmorphic CSS UI Theme (`app.py`).
- 4 Multi-Page Interactive Modules (`pages/`):
  1. 🔍 **Fund Analytics Explorer:** Interactive Plotly NAV charts, rolling CAGR, drawdowns, and 18 metric cards.
  2. ⚖️ **Peer Comparison Tool:** Multi-fund side-by-side matrices, risk-return scatter plots, and radar charts.
  3. 💼 **Investor Portfolio Tracker:** Holdings PnL, XIRR %, asset allocation pie charts, and interactive SIP Future Value simulator.
  4. 🤖 **AI Fund Recommendation Engine:** Risk profiling wizard with model portfolio target weights.

### Module 10: Power BI Integration & Exporter
- Automated Power BI Data Pipeline (`src/database/powerbi_export.py`) landing Star-Schema CSVs in `data/processed/powerbi/`.

---

## 📐 Financial Formulas Summary

| Metric | Formula |
| :--- | :--- |
| **CAGR** | $\text{CAGR} = \left(\frac{\text{NAV}_{\text{end}}}{\text{NAV}_{\text{start}}}\right)^{\frac{365}{N_{\text{days}}}} - 1$ |
| **Sharpe Ratio** | $SR = \frac{\text{CAGR} - R_f}{\sigma_{\text{annualized}}}$ |
| **Sortino Ratio** | $SoR = \frac{\text{CAGR} - R_f}{\sigma_{\text{downside}}}$ |
| **Jensen's Alpha ($\alpha$)** | $\alpha = \text{CAGR}_p - [R_f + \beta_p \cdot (\text{CAGR}_m - R_f)]$ |
| **XIRR** | $\sum_{i=0}^{N} \frac{C_i}{(1 + \text{XIRR})^{\frac{d_i - d_0}{365.25}}} = 0$ |
| **Max Drawdown (MDD)** | $\text{MDD} = \min\left(\frac{\text{NAV}_t - \text{Peak}_t}{\text{Peak}_t}\right)$ |

---

## ⚡ Quick Start Guide

### 1. Installation & Environment Setup
```bash
# Clone Repository
git clone https://github.com/Vashishtha7705/mutualIQ.git
cd mutualIQ

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install -r requirements.txt
```

### 2. Run Complete Data Pipeline (Ingestion -> Transformation -> Database Load -> Power BI Export)
```bash
# Step 1: Data Ingestion
PYTHONPATH=. python3 -m src.ingestion.pipeline

# Step 2: Data Transformation
PYTHONPATH=. python3 -m src.transformation.pipeline

# Step 3: Database Load
PYTHONPATH=. python3 -m src.database.pipeline

# Step 4: Export Power BI Data Files
PYTHONPATH=. python3 -m src.database.powerbi_export
```

### 3. Launch Streamlit Web Application
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

### 4. Run Pytest Automated Unit Test Suite
```bash
PYTHONPATH=. pytest tests/
```

---

## 📊 Power BI Integration & DAX Modeling

Import the exported Star-Schema CSV files located in `data/processed/powerbi/` into Power BI Desktop and create relationship joins on `date_id`, `scheme_code`, `amc_id`, and `category_id`.

### Essential DAX Measures:

```dax
// 1. Total Portfolio Current Value
Total Portfolio Value = 
SUMX(
    fact_transactions,
    fact_transactions[units] * RELATED(fact_daily_nav[nav])
)

// 2. Total Invested Capital
Total Invested Amount = SUM(fact_transactions[total_amount])

// 3. Total Portfolio PnL
Total Portfolio PnL = [Total Portfolio Value] - [Total Invested Amount]

// 4. Portfolio Return %
Portfolio Return % = DIVIDE([Total Portfolio PnL], [Total Invested Amount], 0) * 100
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
