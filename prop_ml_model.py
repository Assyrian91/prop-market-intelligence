# ============================================================
# PROJECT: Melbourne Northern Corridor Property Intelligence
# FILE: prop_ml_model.py
# PURPOSE: Train Linear Regression + XGBoost price prediction
#          models on 2014-2023 data, test on 2024,
#          write predictions to Supabase prop_ml_predictions
# AUTHOR: Khoshaba Odeesho | Assyrian AI
# ============================================================

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
from dotenv import load_dotenv
import os
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# STEP 1 — DATABASE CONNECTION
# Credentials loaded from .env file — never hardcoded
# ============================================================

load_dotenv()

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
# STEP 2 — LOAD DATA FROM SUPABASE
# Load all confirmed (non-estimated) rows
# ============================================================

print("Loading data from prop_historical_prices...")
query = """
    SELECT suburb, year, median_price
    FROM prop_historical_prices
    WHERE median_price IS NOT NULL
    AND is_estimated = FALSE
    ORDER BY suburb, year;
"""
cursor.execute(query)
rows = cursor.fetchall()
df = pd.DataFrame(rows, columns=["suburb", "year", "median_price"])
df["median_price"] = df["median_price"].astype(float)
df["year"]         = df["year"].astype(int)
print(f"Loaded {len(df)} rows.\n")

# ============================================================
# STEP 3 — FEATURE ENGINEERING
# ============================================================

print("Engineering features...")

le = LabelEncoder()
df["suburb_encoded"] = le.fit_transform(df["suburb"])

df["years_since_start"] = df.groupby("suburb")["year"].transform(
    lambda x: x - x.min()
)

# lag_1: previous year price per suburb
df = df.sort_values(["suburb", "year"]).reset_index(drop=True)
df["lag_1"] = df.groupby("suburb")["median_price"].shift(1)

# Only keep rows where lag_1 exists
df_model = df.dropna(subset=["lag_1"]).copy()
print(f"Model-ready rows: {len(df_model)}\n")

# ============================================================
# STEP 4 — TRAIN / TEST SPLIT
# Train: 2014-2023 | Test: 2024
# ============================================================

FEATURES   = ["year", "suburb_encoded", "years_since_start", "lag_1"]
TARGET     = "median_price"
TRAIN_END  = 2023
TEST_YEAR  = 2024

train = df_model[df_model["year"] <= TRAIN_END].copy()
test  = df_model[df_model["year"] == TEST_YEAR].copy()

print(f"Training rows : {len(train)}")
print(f"Test rows     : {len(test)}")
print(f"Test suburbs  : {list(test['suburb'].unique())}\n")

X_train = train[FEATURES]
y_train = train[TARGET]
X_test  = test[FEATURES]
y_test  = test[TARGET]

# ============================================================
# STEP 5 — TRAIN LINEAR REGRESSION
# ============================================================

print("Training Linear Regression model...")
lr = LinearRegression()
lr.fit(X_train, y_train)
lr_preds = lr.predict(X_test)
lr_mae   = mean_absolute_error(y_test, lr_preds)
lr_r2    = r2_score(y_test, lr_preds)
print(f"Linear Regression — MAE: ${lr_mae:,.0f} | R2: {lr_r2:.4f}\n")

# ============================================================
# STEP 6 — TRAIN XGBOOST
# ============================================================

print("Training XGBoost model...")
xgb = XGBRegressor(
    n_estimators  = 200,
    learning_rate = 0.05,
    max_depth     = 4,
    random_state  = 42,
    verbosity     = 0
)
xgb.fit(X_train, y_train)
xgb_preds = xgb.predict(X_test)
xgb_mae   = mean_absolute_error(y_test, xgb_preds)
xgb_r2    = r2_score(y_test, xgb_preds)
print(f"XGBoost        — MAE: ${xgb_mae:,.0f} | R2: {xgb_r2:.4f}\n")

# ============================================================
# STEP 7 — DETAILED TEST RESULTS
# ============================================================

print("=" * 70)
print(f"PREDICTIONS VS ACTUAL — {TEST_YEAR}")
print("=" * 70)

test = test.copy()
test["lr_predicted"]  = lr_preds.round(0)
test["xgb_predicted"] = xgb_preds.round(0)
test["lr_error_pct"]  = (
    (test["lr_predicted"] - test["median_price"])
    / test["median_price"] * 100
).round(2)
test["xgb_error_pct"] = (
    (test["xgb_predicted"] - test["median_price"])
    / test["median_price"] * 100
).round(2)

for _, row in test.iterrows():
    print(
        f"{row['suburb']:<15} "
        f"Actual: ${row['median_price']:>9,.0f} | "
        f"LR:  ${row['lr_predicted']:>9,.0f} ({row['lr_error_pct']:+.1f}%) | "
        f"XGB: ${row['xgb_predicted']:>9,.0f} ({row['xgb_error_pct']:+.1f}%)"
    )

print()

# ============================================================
# STEP 8 — WRITE PREDICTIONS TO SUPABASE
# ============================================================

print("Writing predictions to Supabase...")

cursor.execute("""
    DELETE FROM prop_ml_predictions
    WHERE model_name IN ('LinearRegression_v1', 'XGBoost_v1')
    AND prediction_year = %s;
""", (TEST_YEAR,))

records = []
for _, row in test.iterrows():
    lr_conf  = float(max(0, 1 - abs(row["lr_error_pct"])  / 100))
    xgb_conf = float(max(0, 1 - abs(row["xgb_error_pct"]) / 100))

    records.append((
        row["suburb"], int(TEST_YEAR),
        float(row["lr_predicted"]),
        None, None, lr_conf,
        "LinearRegression_v1", "1.0",
        ["year", "suburb_encoded", "years_since_start", "lag_1"],
        float(row["median_price"]),
        float(row["lr_error_pct"])
    ))
    records.append((
        row["suburb"], int(TEST_YEAR),
        float(row["xgb_predicted"]),
        None, None, xgb_conf,
        "XGBoost_v1", "1.0",
        ["year", "suburb_encoded", "years_since_start", "lag_1"],
        float(row["median_price"]),
        float(row["xgb_error_pct"])
    ))

insert_sql = """
    INSERT INTO prop_ml_predictions (
        suburb, prediction_year, predicted_price,
        lower_bound, upper_bound, confidence_score,
        model_name, model_version, features_used,
        actual_price, prediction_error_pct
    ) VALUES %s
    ON CONFLICT (suburb, prediction_year, model_name) DO UPDATE SET
        predicted_price      = EXCLUDED.predicted_price,
        confidence_score     = EXCLUDED.confidence_score,
        actual_price         = EXCLUDED.actual_price,
        prediction_error_pct = EXCLUDED.prediction_error_pct,
        run_at               = NOW();
"""

execute_values(cursor, insert_sql, records)
conn.commit()
print(f"Inserted {len(records)} prediction records.\n")

# ============================================================
# STEP 9 — FINAL SUMMARY
# ============================================================

print("=" * 70)
print("MODEL SUMMARY")
print("=" * 70)
print(f"Linear Regression — MAE: ${lr_mae:,.0f} | R2: {lr_r2:.4f}")
print(f"XGBoost           — MAE: ${xgb_mae:,.0f} | R2: {xgb_r2:.4f}")
print()
if xgb_mae < lr_mae:
    print("Champion model: XGBoost")
else:
    print("Champion model: Linear Regression")
print()
print("All predictions written to prop_ml_predictions in Supabase.")
print("Done.")

cursor.close()
conn.close()