# 🏠 Melbourne Northern Corridor — Property Intelligence Platform

> **End-to-end data science and AI automation project** covering 7 Melbourne 
> northern corridor suburbs across 12 years (2014–2026).  
> Built by **Khoshaba Odeesho** | [Assyrian AI](https://github.com/Assyrian91)

---

## 🔴 Live Dashboard

**[→ View Live on Streamlit Cloud](https://assyrian91-prop-market-intelligence.streamlit.app)**

---

## 📌 Project Overview

A fully automated property market intelligence platform that demonstrates:

- **SQL data engineering** — 6-table PostgreSQL schema with window functions, 
  CAGR calculations, rankings, and permanent views
- **Python data science** — data cleaning, feature engineering, 
  and ML model training
- **Machine learning** — XGBoost and Linear Regression price prediction 
  models (XGBoost MAE: $11,744 on real 2024 data)
- **AI integration** — Google Gemini 2.0 Flash generating professional 
  market narrative reports from real data
- **Streamlit dashboard** — 5-page interactive dashboard deployed publicly 
  on Streamlit Cloud
- **Supabase PostgreSQL** — cloud database with 6 tables, 
  249 rows of real data, live connection

---

## 🗺️ Suburbs Covered

| Suburb | 2014 Price | 2026 Price | CAGR |
|---|---|---|---|
| Mickleham | $168,000 | $710,300 | **12.29% pa** |
| Kalkallo | $180,000 | $650,100 | **12.22% pa** |
| Beveridge | $351,500 | $642,000 | 6.04% pa |
| Craigieburn | $362,000 | $730,000 | 5.13% pa |
| Wallan | $356,000 | $640,000 | 4.73% pa |
| Roxburgh Park | $385,000 | $630,000 | 4.59% pa |
| Donnybrook | $530,000 | $650,000 | 3.46% pa |

---

## 🏗️ Architecture
Victorian Gov Data (2014–2024)

Supplementary Sources (2025–2026)
│
▼
Supabase PostgreSQL
┌─────────────────────────────────────┐
│  prop_historical_prices  (91 rows)  │
│  prop_suburb_stats       (83 rows)  │
│  prop_ml_predictions     (14 rows)  │
│  prop_ai_reports          (8 rows)  │
│  prop_rent_snapshot        (7 rows) │
│  prop_live_listings       (46 rows) │
│  prop_cagr_summary  [VIEW]          │
└─────────────────────────────────────┘
│
┌───────┴────────┐
▼                ▼
Python ML         Gemini AI
XGBoost           Narratives
LinearReg         8 Reports
│                │
└───────┬────────┘
▼
Streamlit Dashboard
5 Pages · Live · Public



---

## 📊 Dashboard Pages

| Page | What It Shows |
|---|---|
| 🏠 Overview | Corridor KPIs, price history, CAGR leaderboard |
| 📈 Price Intelligence | 12-year trends, YoY heatmap, suburb deep-dive |
| 🤖 ML Predictions | XGBoost vs Linear Regression comparison |
| 🏘️ Live Listings | Current properties for sale and rent |
| 📋 AI Reports | Gemini-generated market narratives |

---

## 🤖 ML Model Results

| Model | MAE | R² | Verdict |
|---|---|---|---|
| **XGBoost v1** | **$11,744** | **0.3189** | ✅ Champion |
| Linear Regression v1 | $41,584 | -5.27 | Baseline |

**Best prediction:** Donnybrook — only 0.42% error  
**Average XGBoost confidence:** 98.1%

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Database | Supabase PostgreSQL |
| Data Science | Python, pandas, numpy |
| ML Models | scikit-learn, XGBoost |
| AI Narratives | Google Gemini 2.0 Flash API |
| Dashboard | Streamlit + Plotly |
| Secrets | python-dotenv |
| Version Control | Git + GitHub |

---

## 📁 Repository Structure
prop-market-intelligence/
├── prop_dashboard.py        # Streamlit 5-page dashboard
├── prop_ml_model.py         # XGBoost + Linear Regression training
├── prop_ai_narrative.py     # Gemini AI report generation
├── requirements.txt         # Python dependencies
├── .gitignore               # Excludes .env and secrets
└── README.md                # This file
---

## 🚀 Running Locally

```bash
# Clone the repo
git clone https://github.com/Assyrian91/prop-market-intelligence.git
cd prop-market-intelligence

# Install dependencies
pip install -r requirements.txt

# Create .env file with your Supabase credentials
# DB_HOST=your-host
# DB_PORT=5432
# DB_NAME=postgres
# DB_USER=postgres
# DB_PASSWORD=your-password

# Run the dashboard
streamlit run prop_dashboard.py
```

---

## 📊 Data Sources

| Source | Coverage | Trust |
|---|---|---|
| Victorian Government Property Sales Report | 2014–2024 all suburbs | ✅ Official |
| SKAD Real Estate | Craigieburn 2025–2026 | ✅ Sourced |
| Valuer-General Victoria | Beveridge 2025 | ✅ Official |
| VicPropertyCheck | Wallan 2026 | ✅ Sourced |
| Picki LGA Data | Mickleham, Kalkallo, Roxburgh Park 2026 | ✅ ABS-sourced |
| Estimated (corridor trend) | 7 sparse rows | ⚠️ Flagged |

---

## 👤 Author

**Khoshaba Odeesho**  
Data Analyst | AI Automation Engineer  
Melbourne, Australia  

[GitHub](https://github.com/Assyrian91) · [LinkedIn](https://linkedin.com/in/your-profile)

---

*Built as part of a professional data science portfolio — 
demonstrating end-to-end capability from raw data to deployed AI product.*