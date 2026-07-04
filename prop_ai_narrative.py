# ============================================================
# PROJECT: Melbourne Northern Corridor Property Intelligence
# FILE: prop_ai_narrative.py
# PURPOSE: Generate AI narrative market reports per suburb
#          using real data from Supabase + Google Gemini API
#          Save reports to prop_ai_reports table
# AUTHOR: Khoshaba Odeesho | Assyrian AI
# ============================================================

import psycopg2
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import os
import time

load_dotenv()

# ============================================================
# STEP 1 — CONFIG
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL     = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
    f"?key={os.getenv('GEMINI_API_KEY')}"
)
REPORT_YEAR    = 2024

# ============================================================
# STEP 2 — GEMINI CALL FUNCTION
# ============================================================

def call_gemini(prompt, max_retries=3):
    """Call Gemini API with retry logic."""
    headers = {"Content-Type": "application/json"}
    body    = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature"    : 0.2,
            "maxOutputTokens": 600,
        }
    }

    for attempt in range(max_retries):
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers = headers,
            json    = body
        )

        if response.status_code == 200:
            result = response.json()
            text   = (
                result["candidates"][0]
                      ["content"]["parts"][0]["text"]
                .strip()
            )
            tokens = result.get(
                "usageMetadata", {}
            ).get("totalTokenCount", 0)
            return text, tokens

        elif response.status_code == 429:
            wait = 10 * (attempt + 1)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)

        else:
            print(f"  API error {response.status_code}: {response.text}")
            return None, 0

    return None, 0

# ============================================================
# STEP 3 — DATABASE CONNECTION
# ============================================================

print("Connecting to Supabase...")
conn = psycopg2.connect(
    host     = os.getenv("DB_HOST"),
    port     = os.getenv("DB_PORT"),
    dbname   = os.getenv("DB_NAME"),
    user     = os.getenv("DB_USER"),
    password = os.getenv("DB_PASSWORD"),
    sslmode  = "require"
)
cursor = conn.cursor()
print("Connected.\n")

# ============================================================
# STEP 4 — LOAD DATA FROM SUPABASE
# ============================================================

print("Loading suburb intelligence data...")

cursor.execute("""
    SELECT suburb, median_price, yoy_change_pct, price_change_abs,
           suburb_rank, total_suburbs, vs_corridor_avg_pct,
           corridor_avg_price, growth_category
    FROM prop_suburb_stats
    WHERE year = %s
    ORDER BY suburb_rank;
""", (REPORT_YEAR,))
stats_rows = cursor.fetchall()
stats_cols = [
    "suburb","median_price","yoy_change_pct","price_change_abs",
    "suburb_rank","total_suburbs","vs_corridor_avg_pct",
    "corridor_avg_price","growth_category"
]
stats = [dict(zip(stats_cols, row)) for row in stats_rows]

cursor.execute("SELECT * FROM prop_cagr_summary ORDER BY cagr_pct DESC;")
cagr_rows = cursor.fetchall()
cagr_cols = [
    "suburb","start_year","start_price","end_year","end_price",
    "years","total_gain","total_growth_pct","cagr_pct"
]
cagr = [dict(zip(cagr_cols, row)) for row in cagr_rows]

cursor.execute("""
    SELECT suburb, median_weekly_rent, annual_rent,
           rental_yield_pct, vacancy_rate_pct
    FROM prop_rent_snapshot
    ORDER BY rental_yield_pct DESC;
""")
rent_rows = cursor.fetchall()
rent_cols = [
    "suburb","median_weekly_rent","annual_rent",
    "rental_yield_pct","vacancy_rate_pct"
]
rent = [dict(zip(rent_cols, row)) for row in rent_rows]

cursor.execute("""
    SELECT suburb, predicted_price, actual_price,
           prediction_error_pct, confidence_score
    FROM prop_ml_predictions
    WHERE prediction_year = %s
    AND model_name = 'XGBoost_v1'
    ORDER BY suburb;
""", (REPORT_YEAR,))
ml_rows = cursor.fetchall()
ml_cols = [
    "suburb","predicted_price","actual_price",
    "prediction_error_pct","confidence_score"
]
ml = [dict(zip(ml_cols, row)) for row in ml_rows]

print(f"Loaded: {len(stats)} suburb stats | {len(cagr)} CAGR records | "
      f"{len(rent)} rent records | {len(ml)} ML predictions\n")

# Clear old reports for clean run
cursor.execute("DELETE FROM prop_ai_reports;")
conn.commit()
print("Old reports cleared.\n")

# ============================================================
# STEP 5 — CORRIDOR CONTEXT
# ============================================================

corridor_avg = float(stats[0]["corridor_avg_price"]) if stats else 0
top_suburb   = stats[0]["suburb"] if stats else "N/A"
top_price    = float(stats[0]["median_price"]) if stats else 0
best_cagr    = cagr[0] if cagr else {}
best_yield   = rent[0] if rent else {}

# ============================================================
# STEP 6 — GENERATE REPORT PER SUBURB
# ============================================================

print("Generating AI narrative reports...")
print("=" * 65)

reports_saved = 0

for suburb_stat in stats:
    suburb = suburb_stat["suburb"]

    suburb_cagr = next((c for c in cagr if c["suburb"] == suburb), {})
    suburb_rent = next((r for r in rent if r["suburb"] == suburb), {})
    suburb_ml   = next((m for m in ml  if m["suburb"] == suburb), {})

    prompt = f"""Write a professional Australian property market investment report for {suburb}, Melbourne.

Use ONLY the data below. Do NOT repeat these instructions. Start directly with the report.
Structure it with these 5 bold headings:

**1. Market Position & Price Performance**
**2. Long-Term Growth Track Record**
**3. Rental Investment Case**
**4. ML Model Accuracy**
**5. Investment Verdict**

Keep total length under 280 words. Use specific numbers. Professional tone.

DATA FOR {suburb} — {REPORT_YEAR}:
- Median price: ${float(suburb_stat['median_price']):,.0f}
- Year-on-year change: {float(suburb_stat['yoy_change_pct']):+.1f}% (${float(suburb_stat['price_change_abs']):,.0f})
- Corridor rank: {suburb_stat['suburb_rank']} of {suburb_stat['total_suburbs']}
- vs corridor average: {float(suburb_stat['vs_corridor_avg_pct']):+.1f}% (corridor avg: ${corridor_avg:,.0f})
- Growth category: {suburb_stat['growth_category'].replace('_',' ').title()}
- Start year / price: {suburb_cagr.get('start_year','N/A')} / ${float(suburb_cagr.get('start_price',0)):,.0f}
- Total gain: ${float(suburb_cagr.get('total_gain',0)):,.0f} ({float(suburb_cagr.get('total_growth_pct',0)):.1f}% total)
- CAGR: {float(suburb_cagr.get('cagr_pct',0)):.2f}% per year
- Weekly rent: ${float(suburb_rent.get('median_weekly_rent',0)):,.0f}
- Gross rental yield: {float(suburb_rent.get('rental_yield_pct',0)):.2f}%
- Vacancy rate: {float(suburb_rent.get('vacancy_rate_pct',0)):.2f}%
- XGBoost predicted: ${float(suburb_ml.get('predicted_price',0)):,.0f}
- Actual price: ${float(suburb_ml.get('actual_price',0)):,.0f}
- Prediction error: {float(suburb_ml.get('prediction_error_pct',0)):+.2f}%
- Model confidence: {float(suburb_ml.get('confidence_score',0)):.2%}"""

    print(f"Generating report for {suburb}...")
    report_body, token_count = call_gemini(prompt)

    if not report_body:
        print(f"  Skipping {suburb} — API error.\n")
        continue

    print(f"  Generated ({token_count} tokens)")
    print(f"  Preview: {report_body[:100]}...\n")

    key_insights = [
        f"Median price {REPORT_YEAR}: ${float(suburb_stat['median_price']):,.0f}",
        f"YoY change: {float(suburb_stat['yoy_change_pct']):+.1f}%",
        f"CAGR: {float(suburb_cagr.get('cagr_pct',0)):.2f}% | "
        f"Yield: {float(suburb_rent.get('rental_yield_pct',0)):.2f}%"
    ]

    cursor.execute("""
        INSERT INTO prop_ai_reports (
            report_type, suburb, year, report_title,
            report_body, key_insights, model_used,
            prompt_version, token_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (
        "annual_suburb_review",
        suburb,
        REPORT_YEAR,
        f"{suburb} Property Market Report — {REPORT_YEAR}",
        report_body,
        key_insights,
        "gemini-2.5-flash",
        "v2.0",
        token_count
    ))
    conn.commit()
    reports_saved += 1
    time.sleep(2)  # Respect Gemini rate limits

# ============================================================
# STEP 7 — CORRIDOR EXECUTIVE SUMMARY
# ============================================================

print("=" * 65)
print("Generating corridor executive summary...")

corridor_data = "\n".join([
    f"- {s['suburb']}: ${float(s['median_price']):,.0f} | "
    f"YoY: {float(s['yoy_change_pct']):+.1f}% | "
    f"Rank: {s['suburb_rank']}/{s['total_suburbs']} | "
    f"Category: {s['growth_category'].replace('_',' ').title()}"
    for s in stats
])

cagr_data = "\n".join([
    f"- {c['suburb']}: CAGR {float(c['cagr_pct']):.2f}% | "
    f"Total growth: {float(c['total_growth_pct']):.1f}%"
    for c in cagr
])

corridor_prompt = f"""Write a professional executive summary of the Melbourne Northern Growth Corridor property market for {REPORT_YEAR}.

Do NOT repeat these instructions. Start directly with a bold headline.
Structure with these 4 bold headings:

**Overall Corridor Performance**
**Top and Bottom Performers**
**Key Market Trends**
**Investment Outlook**

Under 250 words. Use specific numbers. Professional tone.

SUBURB PERFORMANCE {REPORT_YEAR}:
{corridor_data}

LONG-TERM CAGR:
{cagr_data}

CORRIDOR AVERAGE PRICE: ${corridor_avg:,.0f}
TOP SUBURB: {top_suburb} at ${top_price:,.0f}
BEST CAGR: {best_cagr.get('suburb','N/A')} at {float(best_cagr.get('cagr_pct',0)):.2f}%
BEST YIELD: {best_yield.get('suburb','N/A')} at {float(best_yield.get('rental_yield_pct',0)):.2f}%"""

corridor_report, token_count = call_gemini(corridor_prompt)

if corridor_report:
    print(f"Generated ({token_count} tokens)")
    print(f"\nFULL CORRIDOR REPORT:\n")
    print(corridor_report)
    print()

    cursor.execute("""
        INSERT INTO prop_ai_reports (
            report_type, suburb, year, report_title,
            report_body, key_insights, model_used,
            prompt_version, token_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (
        "weekly_summary",
        None,
        REPORT_YEAR,
        f"Melbourne Northern Corridor — Executive Summary {REPORT_YEAR}",
        corridor_report,
        [
            f"Corridor avg: ${corridor_avg:,.0f}",
            f"Top performer: {top_suburb}",
            f"Best CAGR: {best_cagr.get('suburb','N/A')} "
            f"at {float(best_cagr.get('cagr_pct',0)):.2f}%"
        ],
        "gemini-2.5-flash",
        "v2.0",
        token_count
    ))
    conn.commit()
    reports_saved += 1

# ============================================================
# STEP 8 — FINAL SUMMARY
# ============================================================

print("=" * 65)
print(f"Total reports generated and saved : {reports_saved}")
print(f"Model used                        : gemini-2.5-flash")
print("All reports saved to prop_ai_reports in Supabase.")
print("Done.")

cursor.close()
conn.close()