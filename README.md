# 📈 Mutual Fund Analytics Platform

A production-grade, end-to-end Quantitative Mutual Fund Analytics & Portfolio Intelligence Platform built with Python, Pandas, SQLite, Plotly, Streamlit, and Power BI.

---

## 🏗️ System Architecture & Modular Design

```
mutual-fund-analytics/
├── config/                  # YAML Configurations & Environment variables
│   └── config.yaml
├── data/                    # Data storage layers (Git ignored raw/processed/db)
│   ├── database/            # SQLite / Relational Star Schema DBs
│   ├── processed/           # Transformed clean datasets (Parquet/CSV)
│   └── raw/                 # Ingested raw AMFI / API / Benchmark datasets
├── logs/                    # Rotating application logs
├── src/                     # Core Source Code Package
│   ├── analytics/           # Quantitative analytics engine (CAGR, Sharpe, VaR, etc.)
│   ├── config/              # Centralized configuration loader
│   ├── database/            # Schema creation, ORM models, SQL loaders
│   ├── ingestion/           # AMFI API & CSV data ingestion pipelines
│   ├── scoring/             # Fund scoring matrix & quantitative recommendation engine
│   ├── transformation/      # Data cleaning, normalization, Pydantic validation
│   └── utils/               # Centralized logging & helper utilities
├── tests/                   # Pytest automated test suites
├── requirements.txt         # Production dependencies
└── README.md                # Documentation & Architecture breakdown
```

---

## 🛠️ Tech Stack & Engineering Standards

- **Programming Language:** Python 3.10+
- **Data Processing:** Pandas, NumPy, SciPy
- **Data Validation & Config:** Pydantic v2, PyYAML
- **Database Layer:** SQLite3 / SQLAlchemy (Star-Schema Dimensional Model)
- **Web App & Dashboards:** Streamlit, Plotly Express/GO, Power BI
- **Quality Assurance:** Pytest, Thread-safe Rotating Logger, Type Annotations (PEP 526)

---

## 🚀 Quick Start Guide

### 1. Set Up Workspace & Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest tests/
```
