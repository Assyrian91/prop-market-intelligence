# ============================================================
# PROJECT: Melbourne Northern Corridor Property Intelligence
# FILE: prop_dashboard.py
# PURPOSE: Premium 5-page Streamlit dashboard
# AUTHOR: Khoshaba Odeesho | Assyrian AI
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title = "PropMarket Intelligence | Melbourne Northern Corridor",
    page_icon  = "🏠",
    layout     = "wide",
    initial_sidebar_state = "expanded"
)

# ============================================================
# PREMIUM CSS
# ============================================================

st.markdown("""
<style>
    .stApp { background-color: #0a0e1a; }
    .main .block-container { padding: 1.5rem 2rem; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1525 0%, #0a0e1a 100%);
        border-right: 1px solid #1e3a5f;
    }
    .kpi-card {
        background: linear-gradient(135deg, #111827 0%, #1a2540 100%);
        border: 1px solid #1e3a5f;
        border-radius: 14px;
        padding: 20px 16px;
        text-align: center;
        margin: 4px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 800;
        color: #f59e0b;
        letter-spacing: -0.5px;
    }
    .kpi-label {
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 6px;
    }
    .kpi-delta-pos {
        font-size: 12px; color: #10b981;
        margin-top: 4px; font-weight: 600;
    }
    .kpi-delta-neg {
        font-size: 12px; color: #ef4444;
        margin-top: 4px; font-weight: 600;
    }
    .section-title {
        font-size: 17px;
        font-weight: 700;
        color: #f1f5f9;
        margin: 24px 0 14px 0;
        padding-left: 12px;
        border-left: 3px solid #f59e0b;
    }
    .report-body {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        padding: 24px;
        color: #cbd5e1;
        line-height: 1.8;
        font-size: 14px;
    }
    hr { border-color: #1e3a5f; }
    h1, h2, h3 { color: #f1f5f9 !important; }
    p { color: #94a3b8; }
    label { color: #64748b !important; }
    div[data-testid="metric-container"] {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        padding: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# PLOT LAYOUT HELPER — no duplicate keys
# ============================================================

def plot_layout(height=400, tickformat_y=None, dtick_x=None,
                barmode=None, title=None, extra=None):
    layout = dict(
        plot_bgcolor  = "#111827",
        paper_bgcolor = "#0a0e1a",
        font          = dict(color="#94a3b8", family="Inter, sans-serif"),
        height        = height,
        margin        = dict(l=20, r=20, t=40, b=20),
        legend        = dict(
            bgcolor="#111827", bordercolor="#1e3a5f", borderwidth=1
        ),
        xaxis = dict(
            gridcolor="#1e3a5f", linecolor="#1e3a5f",
            zerolinecolor="#1e3a5f",
            **({"dtick": dtick_x} if dtick_x else {})
        ),
        yaxis = dict(
            gridcolor="#1e3a5f", linecolor="#1e3a5f",
            zerolinecolor="#1e3a5f",
            **({"tickformat": tickformat_y} if tickformat_y else {})
        ),
    )
    if barmode: layout["barmode"] = barmode
    if title:   layout["title"]   = dict(
        text=title, font=dict(color="#94a3b8")
    )
    if extra:   layout.update(extra)
    return layout

SUBURB_COLORS = {
    "CRAIGIEBURN"  : "#f59e0b",
    "MICKLEHAM"    : "#3b82f6",
    "BEVERIDGE"    : "#10b981",
    "ROXBURGH PARK": "#8b5cf6",
    "WALLAN"       : "#ef4444",
    "DONNYBROOK"   : "#06b6d4",
    "KALKALLO"     : "#f97316",
}

# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_conn():
    # Try Streamlit Cloud secrets first
    try:
        cfg = st.secrets["database"]
        return psycopg2.connect(
            host     = cfg["DB_HOST"],
            port     = int(cfg["DB_PORT"]),
            dbname   = cfg["DB_NAME"],
            user     = cfg["DB_USER"],
            password = cfg["DB_PASSWORD"],
            sslmode  = "require"
        )
    except KeyError:
        pass

    # Local .env fallback
    load_dotenv()
    return psycopg2.connect(
        host     = os.getenv("DB_HOST"),
        port     = int(os.getenv("DB_PORT", 5432)),
        dbname   = os.getenv("DB_NAME"),
        user     = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        sslmode  = "require"
    )
def query(sql, params=None):
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(rows, columns=cols)

@st.cache_data(ttl=1800)
def load_all():
    hist = query("""
        SELECT suburb, year, median_price, is_estimated
        FROM prop_historical_prices
        WHERE median_price IS NOT NULL ORDER BY suburb, year
    """)
    stats = query("""
        SELECT * FROM prop_suburb_stats ORDER BY year, suburb_rank
    """)
    cagr = query("""
        SELECT * FROM prop_cagr_summary ORDER BY cagr_pct DESC
    """)
    ml = query("""
        SELECT suburb, prediction_year, model_name, predicted_price,
               actual_price, prediction_error_pct, confidence_score
        FROM prop_ml_predictions ORDER BY model_name, suburb
    """)
    rent = query("""
        SELECT * FROM prop_rent_snapshot ORDER BY rental_yield_pct DESC
    """)
    listings = query("""
        SELECT * FROM prop_live_listings ORDER BY scraped_date DESC, suburb
    """)
    reports = query("""
        SELECT report_type, suburb, year, report_title,
               report_body, key_insights, model_used,
               token_count, generated_at
        FROM prop_ai_reports ORDER BY report_type, suburb
    """)
    # Fix numeric types
    for df in [hist, stats, cagr, ml, rent, listings]:
        for col in df.select_dtypes(include="object").columns:
            try:    df[col] = pd.to_numeric(df[col])
            except: pass
    return hist, stats, cagr, ml, rent, listings, reports

# ============================================================
# LOAD DATA
# ============================================================

with st.spinner("Loading market intelligence..."):
    hist, stats, cagr, ml, rent, listings, reports = load_all()

SUBURBS = sorted(hist["suburb"].unique().tolist())

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:20px 0 10px 0;'>
        <div style='font-size:36px;'>🏠</div>
        <div style='font-size:16px; font-weight:800;
                    color:#f59e0b; letter-spacing:0.5px;'>
            PropMarket
        </div>
        <div style='font-size:11px; color:#64748b;
                    text-transform:uppercase; letter-spacing:2px;'>
            Intelligence Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigate",
        options=[
            "🏠  Overview",
            "📈  Price Intelligence",
            "🤖  ML Predictions",
            "🏘️  Live Listings",
            "📋  AI Reports"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    selected_suburbs = st.multiselect(
        "Filter Suburbs", options=SUBURBS, default=SUBURBS
    )

    st.markdown("---")
    st.markdown("""
    <div style='font-size:11px; color:#475569; line-height:2;'>
        <b style='color:#64748b;'>DATA SOURCES</b><br>
        Victorian Government<br>
        Valuer-General VIC<br>
        SKAD Real Estate<br>
        Picki LGA Data<br><br>
        <b style='color:#64748b;'>MODELS</b><br>
        XGBoost v1 ✅ Champion<br>
        Linear Regression v1<br><br>
        <b style='color:#64748b;'>AI ENGINE</b><br>
        Google Gemini 2.0 Flash<br><br>
        <b style='color:#64748b;'>DATABASE</b><br>
        Supabase PostgreSQL
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:11px; color:#475569; text-align:center;'>
        Built by<br>
        <b style='color:#f59e0b;'>Khoshaba Odeesho</b><br>
        <span style='color:#3b82f6;'>Assyrian AI</span><br>
        <a href='https://github.com/Assyrian91'
           style='color:#3b82f6;'>github.com/Assyrian91</a>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# HELPER
# ============================================================

def kpi(label, value, delta=None, pos=True):
    d = ""
    if delta:
        cls = "kpi-delta-pos" if pos else "kpi-delta-neg"
        arr = "▲" if pos else "▼"
        d = f'<div class="{cls}">{arr} {delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {d}
    </div>"""

# ============================================================
# PAGE 1 — OVERVIEW
# ============================================================

if "Overview" in page:

    st.markdown("""
    <h1 style='color:#f1f5f9; font-size:28px; font-weight:800; margin-bottom:4px;'>
        Melbourne Northern Corridor
    </h1>
    <p style='color:#64748b; font-size:14px; margin-top:0;'>
        Property Intelligence Platform · 2014–2026 · 7 Suburbs · Real Data
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    latest_year  = int(stats["year"].max())
    latest       = stats[stats["year"] == latest_year].copy()
    latest["median_price"] = pd.to_numeric(latest["median_price"])
    corridor_avg = float(latest["median_price"].mean())
    top_row      = latest.loc[latest["median_price"].idxmax()]
    best_cagr_r  = cagr.iloc[0]
    best_yield_r = rent.loc[pd.to_numeric(rent["rental_yield_pct"]).idxmax()]

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: st.markdown(kpi(
        "Corridor Avg", f"${corridor_avg:,.0f}", str(latest_year), True
    ), unsafe_allow_html=True)
    with c2: st.markdown(kpi(
        "Top Suburb", str(top_row["suburb"]).title(),
        f"${float(top_row['median_price']):,.0f}", True
    ), unsafe_allow_html=True)
    with c3: st.markdown(kpi(
        "Best CAGR", str(best_cagr_r["suburb"]).title(),
        f"{float(best_cagr_r['cagr_pct']):.2f}% pa", True
    ), unsafe_allow_html=True)
    with c4: st.markdown(kpi(
        "Best Yield", str(best_yield_r["suburb"]).title(),
        f"{float(best_yield_r['rental_yield_pct']):.2f}%", True
    ), unsafe_allow_html=True)
    with c5: st.markdown(kpi(
        "Live Listings", str(len(listings)), "Today", True
    ), unsafe_allow_html=True)
    with c6: st.markdown(kpi(
        "Years of Data", "12", "2014–2026", True
    ), unsafe_allow_html=True)

    st.markdown("---")

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown('<div class="section-title">📊 Price History — All Suburbs</div>',
                    unsafe_allow_html=True)
        filt = hist[hist["suburb"].isin(selected_suburbs)].copy()
        filt["median_price"] = pd.to_numeric(filt["median_price"])
        fig = px.line(
            filt, x="year", y="median_price", color="suburb",
            markers=True, color_discrete_map=SUBURB_COLORS,
            labels={"median_price":"Median Price (AUD)",
                    "year":"Year","suburb":"Suburb"}
        )
        fig.update_traces(line_width=2.5, marker_size=7)
        fig.update_layout(**plot_layout(
            height=380, tickformat_y="$,.0f",
            dtick_x=1, extra={"hovermode":"x unified"}
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-title">🏆 CAGR Leaderboard</div>',
                    unsafe_allow_html=True)
        cagr_plot = cagr.copy()
        cagr_plot["cagr_pct"] = pd.to_numeric(cagr_plot["cagr_pct"])
        fig_c = px.bar(
            cagr_plot, x="cagr_pct", y="suburb",
            orientation="h",
            color="cagr_pct",
            color_continuous_scale=["#1e3a5f","#3b82f6","#f59e0b"],
            text="cagr_pct",
            labels={"cagr_pct":"CAGR (%)","suburb":""}
        )
        fig_c.update_traces(
            texttemplate="%{text:.2f}%", textposition="outside"
        )
        fig_c.update_layout(**plot_layout(
            height=380,
            extra={"coloraxis_showscale": False}
        ))
        st.plotly_chart(fig_c, use_container_width=True)

    st.markdown('<div class="section-title">📋 Suburb Rankings — Latest Year</div>',
                unsafe_allow_html=True)
    disp = latest[[
        "suburb","median_price","yoy_change_pct",
        "suburb_rank","vs_corridor_avg_pct","growth_category"
    ]].rename(columns={
        "suburb"             :"Suburb",
        "median_price"       :"Median Price",
        "yoy_change_pct"     :"YoY %",
        "suburb_rank"        :"Rank",
        "vs_corridor_avg_pct":"vs Corridor %",
        "growth_category"    :"Category"
    }).sort_values("Rank")
    st.dataframe(disp, use_container_width=True,
                 hide_index=True, height=280)

# ============================================================
# PAGE 2 — PRICE INTELLIGENCE
# ============================================================

elif "Price Intelligence" in page:

    st.markdown("""
    <h1 style='color:#f1f5f9; font-size:28px; font-weight:800;'>
        📈 Price Intelligence
    </h1>
    <p style='color:#64748b; font-size:14px;'>
        12-year median price trends, growth heatmap,
        and suburb deep-dives
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    year_min = int(hist["year"].min())
    year_max = int(hist["year"].max())
    year_range = st.slider("Year Range", year_min, year_max,
                           (year_min, year_max))

    fh = hist[
        hist["suburb"].isin(selected_suburbs) &
        (hist["year"] >= year_range[0]) &
        (hist["year"] <= year_range[1])
    ].copy()
    fh["median_price"] = pd.to_numeric(fh["median_price"])

    st.markdown('<div class="section-title">Median Price Trends</div>',
                unsafe_allow_html=True)
    fig_line = px.line(
        fh, x="year", y="median_price", color="suburb",
        markers=True, color_discrete_map=SUBURB_COLORS,
        labels={"median_price":"Median Price (AUD)",
                "year":"Year","suburb":"Suburb"}
    )
    fig_line.update_traces(line_width=2.5, marker_size=8)
    # Mark estimated points
    est = fh[fh["is_estimated"] == True]
    if not est.empty:
        fig_line.add_scatter(
            x=est["year"], y=est["median_price"],
            mode="markers",
            marker=dict(size=10, symbol="diamond",
                        color="white", opacity=0.5),
            showlegend=False, name="Estimated"
        )
    fig_line.update_layout(**plot_layout(
        height=420, tickformat_y="$,.0f",
        dtick_x=1, extra={"hovermode":"x unified"}
    ))
    st.plotly_chart(fig_line, use_container_width=True)
    st.caption("◆ White diamonds = estimated data points")

    col_h, col_c = st.columns([3, 2])

    with col_h:
        st.markdown('<div class="section-title">YoY Growth Heatmap</div>',
                    unsafe_allow_html=True)
        fs = stats[
            stats["suburb"].isin(selected_suburbs) &
            (stats["year"] >= year_range[0]) &
            (stats["year"] <= year_range[1])
        ].copy()
        fs["yoy_change_pct"] = pd.to_numeric(fs["yoy_change_pct"])
        pivot = fs.pivot_table(
            index="suburb", columns="year",
            values="yoy_change_pct"
        ).round(1)
        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=[[0,"#ef4444"],[0.5,"#1e3a5f"],[1,"#10b981"]],
            zmid=0,
            text=pivot.values.round(1),
            texttemplate="%{text}%",
            textfont={"size":10,"color":"white"},
            hoverongaps=False,
        ))
        fig_heat.update_layout(**plot_layout(
            height=320,
            extra={"margin": dict(l=130, r=20, t=20, b=40)}
        ))
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_c:
        st.markdown('<div class="section-title">CAGR Summary</div>',
                    unsafe_allow_html=True)
        st.dataframe(
            cagr[["suburb","start_year","start_price",
                  "end_price","total_growth_pct","cagr_pct"
            ]].rename(columns={
                "suburb"          :"Suburb",
                "start_year"      :"From",
                "start_price"     :"Start $",
                "end_price"       :"End $",
                "total_growth_pct":"Total %",
                "cagr_pct"        :"CAGR %"
            }),
            use_container_width=True, hide_index=True, height=320
        )

    st.markdown("---")
    st.markdown('<div class="section-title">Suburb Deep Dive</div>',
                unsafe_allow_html=True)
    pick = st.selectbox("Select suburb", SUBURBS)
    pick_hist = hist[hist["suburb"] == pick].copy()
    pick_hist["median_price"] = pd.to_numeric(pick_hist["median_price"])
    pick_cagr = cagr[cagr["suburb"] == pick].iloc[0]
    pick_rent = rent[rent["suburb"] == pick].iloc[0]

    d1,d2,d3,d4 = st.columns(4)
    with d1: st.markdown(kpi(
        "Latest Price",
        f"${float(pick_hist.iloc[-1]['median_price']):,.0f}",
        str(int(pick_hist.iloc[-1]["year"])), True
    ), unsafe_allow_html=True)
    with d2: st.markdown(kpi(
        "CAGR", f"{float(pick_cagr['cagr_pct']):.2f}%",
        f"{int(pick_cagr['start_year'])}–2026", True
    ), unsafe_allow_html=True)
    with d3: st.markdown(kpi(
        "Total Gain",
        f"{float(pick_cagr['total_growth_pct']):.1f}%",
        f"+${float(pick_cagr['total_gain']):,.0f}", True
    ), unsafe_allow_html=True)
    with d4: st.markdown(kpi(
        "Rental Yield",
        f"{float(pick_rent['rental_yield_pct']):.2f}%",
        f"${float(pick_rent['median_weekly_rent']):,.0f}/wk", True
    ), unsafe_allow_html=True)

# ============================================================
# PAGE 3 — ML PREDICTIONS
# ============================================================

elif "ML Predictions" in page:

    st.markdown("""
    <h1 style='color:#f1f5f9; font-size:28px; font-weight:800;'>
        🤖 ML Price Predictions
    </h1>
    <p style='color:#64748b; font-size:14px;'>
        XGBoost vs Linear Regression — trained 2014–2023,
        tested on 2024
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    xgb = ml[ml["model_name"] == "XGBoost_v1"].copy()
    lr  = ml[ml["model_name"] == "LinearRegression_v1"].copy()
    for df in [xgb, lr]:
        for c in ["predicted_price","actual_price",
                  "prediction_error_pct","confidence_score"]:
            df[c] = pd.to_numeric(df[c])

    xgb_mae      = (xgb["prediction_error_pct"].abs() *
                    xgb["actual_price"] / 100).mean()
    lr_mae       = (lr["prediction_error_pct"].abs() *
                    lr["actual_price"] / 100).mean()
    xgb_avg_conf = float(xgb["confidence_score"].mean())
    best_pred    = xgb.loc[xgb["prediction_error_pct"].abs().idxmin()]

    m1,m2,m3,m4 = st.columns(4)
    with m1: st.markdown(kpi(
        "XGBoost MAE", f"${xgb_mae:,.0f}", "Champion", True
    ), unsafe_allow_html=True)
    with m2: st.markdown(kpi(
        "LR MAE", f"${lr_mae:,.0f}", "Baseline", False
    ), unsafe_allow_html=True)
    with m3: st.markdown(kpi(
        "Avg Confidence", f"{xgb_avg_conf:.1%}", "XGBoost", True
    ), unsafe_allow_html=True)
    with m4: st.markdown(kpi(
        "Best Prediction",
        str(best_pred["suburb"]).title(),
        f"{float(best_pred['prediction_error_pct']):.2f}% error", True
    ), unsafe_allow_html=True)

    st.markdown("---")

    col_ch, col_tb = st.columns([3, 2])

    with col_ch:
        st.markdown('<div class="section-title">Predicted vs Actual (2024)</div>',
                    unsafe_allow_html=True)
        fig_ml = go.Figure()
        fig_ml.add_trace(go.Bar(
            name="Actual", x=xgb["suburb"], y=xgb["actual_price"],
            marker_color="#64748b", opacity=0.8
        ))
        fig_ml.add_trace(go.Bar(
            name="XGBoost", x=xgb["suburb"], y=xgb["predicted_price"],
            marker_color="#f59e0b"
        ))
        fig_ml.add_trace(go.Bar(
            name="Linear Reg.", x=lr["suburb"], y=lr["predicted_price"],
            marker_color="#ef4444", opacity=0.7
        ))
        fig_ml.update_layout(**plot_layout(
            height=400, tickformat_y="$,.0f", barmode="group"
        ))
        st.plotly_chart(fig_ml, use_container_width=True)

    with col_tb:
        st.markdown('<div class="section-title">XGBoost Results</div>',
                    unsafe_allow_html=True)
        st.dataframe(
            xgb[["suburb","predicted_price","actual_price",
                 "prediction_error_pct","confidence_score"
            ]].rename(columns={
                "suburb"              :"Suburb",
                "predicted_price"     :"Predicted",
                "actual_price"        :"Actual",
                "prediction_error_pct":"Error %",
                "confidence_score"    :"Confidence"
            }),
            use_container_width=True, hide_index=True, height=380
        )

    st.markdown('<div class="section-title">Confidence Scores</div>',
                unsafe_allow_html=True)
    fig_conf = go.Figure()
    fig_conf.add_trace(go.Bar(
        name="XGBoost", x=xgb["suburb"], y=xgb["confidence_score"],
        marker_color="#f59e0b",
        text=xgb["confidence_score"],
        texttemplate="%{text:.1%}", textposition="outside"
    ))
    fig_conf.add_trace(go.Bar(
        name="Linear Reg.", x=lr["suburb"], y=lr["confidence_score"],
        marker_color="#ef4444", opacity=0.7,
        text=lr["confidence_score"],
        texttemplate="%{text:.1%}", textposition="outside"
    ))
    fig_conf.update_layout(**plot_layout(
        height=320, barmode="group",
        extra={"yaxis": dict(
            gridcolor="#1e3a5f", tickformat=".0%", range=[0.8, 1.02]
        )}
    ))
    st.plotly_chart(fig_conf, use_container_width=True)

# ============================================================
# PAGE 4 — LIVE LISTINGS
# ============================================================

elif "Live Listings" in page:

    st.markdown("""
    <h1 style='color:#f1f5f9; font-size:28px; font-weight:800;'>
        🏘️ Live Property Listings
    </h1>
    <p style='color:#64748b; font-size:14px;'>
        Current properties for sale and rent —
        Melbourne northern corridor
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    f1,f2,f3,f4 = st.columns(4)
    with f1: f_type   = st.selectbox("Type", ["All","sale","rent"])
    with f2: f_prop   = st.selectbox("Property", ["All","house","townhouse","unit"])
    with f3: f_suburb = st.selectbox("Suburb", ["All"] + SUBURBS)
    with f4: f_beds   = st.selectbox("Min Beds", ["Any","2","3","4","5"])

    fl = listings.copy()
    fl["price"] = pd.to_numeric(fl["price"])
    if f_type   != "All": fl = fl[fl["listing_type"]  == f_type]
    if f_prop   != "All": fl = fl[fl["property_type"] == f_prop]
    if f_suburb != "All": fl = fl[fl["suburb"]        == f_suburb]
    if f_beds   != "Any": fl = fl[fl["bedrooms"]      >= int(f_beds)]

    sale_l = fl[fl["listing_type"] == "sale"]
    rent_l = fl[fl["listing_type"] == "rent"]

    l1,l2,l3,l4 = st.columns(4)
    with l1: st.markdown(kpi(
        "For Sale", str(len(sale_l)), "listings", True
    ), unsafe_allow_html=True)
    with l2: st.markdown(kpi(
        "For Rent", str(len(rent_l)), "listings", True
    ), unsafe_allow_html=True)
    with l3:
        avg_s = float(sale_l["price"].mean()) if len(sale_l) > 0 else 0
        st.markdown(kpi(
            "Avg Sale", f"${avg_s:,.0f}" if avg_s else "N/A",
            "filtered", True
        ), unsafe_allow_html=True)
    with l4:
        avg_r = float(rent_l["price"].mean()) if len(rent_l) > 0 else 0
        st.markdown(kpi(
            "Avg Rent", f"${avg_r:,.0f}/wk" if avg_r else "N/A",
            "per week", True
        ), unsafe_allow_html=True)

    st.markdown("---")

    col_t, col_c = st.columns([3, 2])

    with col_t:
        st.markdown('<div class="section-title">Listings</div>',
                    unsafe_allow_html=True)
        disp_l = fl[[
            "suburb","listing_type","property_type","price",
            "bedrooms","bathrooms","car_spaces",
            "address","days_on_market"
        ]].rename(columns={
            "suburb"        :"Suburb",
            "listing_type"  :"Type",
            "property_type" :"Property",
            "price"         :"Price",
            "bedrooms"      :"Beds",
            "bathrooms"     :"Baths",
            "car_spaces"    :"Cars",
            "address"       :"Address",
            "days_on_market":"Days"
        }).sort_values("Price", ascending=False)
        st.dataframe(disp_l, use_container_width=True,
                     hide_index=True, height=480)

    with col_c:
        if not sale_l.empty:
            st.markdown('<div class="section-title">Avg Sale Price by Suburb</div>',
                        unsafe_allow_html=True)
            s_avg = sale_l.groupby("suburb")["price"].mean().reset_index()
            fig_s = px.bar(
                s_avg, x="suburb", y="price",
                color="price",
                color_continuous_scale=["#1e3a5f","#f59e0b"],
                text="price",
                labels={"price":"Avg Sale Price","suburb":""}
            )
            fig_s.update_traces(
                texttemplate="$%{text:,.0f}", textposition="outside"
            )
            fig_s.update_layout(**plot_layout(
                height=230, tickformat_y="$,.0f",
                extra={"coloraxis_showscale":False}
            ))
            st.plotly_chart(fig_s, use_container_width=True)

        if not rent_l.empty:
            st.markdown('<div class="section-title">Avg Weekly Rent by Suburb</div>',
                        unsafe_allow_html=True)
            r_avg = rent_l.groupby("suburb")["price"].mean().reset_index()
            fig_r = px.bar(
                r_avg, x="suburb", y="price",
                color="price",
                color_continuous_scale=["#1a3a2a","#10b981"],
                text="price",
                labels={"price":"Avg Weekly Rent","suburb":""}
            )
            fig_r.update_traces(
                texttemplate="$%{text:,.0f}/wk", textposition="outside"
            )
            fig_r.update_layout(**plot_layout(
                height=230,
                extra={"coloraxis_showscale":False}
            ))
            st.plotly_chart(fig_r, use_container_width=True)

# ============================================================
# PAGE 5 — AI REPORTS
# ============================================================

elif "AI Reports" in page:

    st.markdown("""
    <h1 style='color:#f1f5f9; font-size:28px; font-weight:800;'>
        📋 AI Market Reports
    </h1>
    <p style='color:#64748b; font-size:14px;'>
        Generated by Google Gemini 2.0 Flash
        using real market data
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")

    corridor = reports[reports["report_type"] == "weekly_summary"]
    suburb_r = reports[reports["report_type"] == "annual_suburb_review"]

    st.markdown('<div class="section-title">🌐 Corridor Executive Summary</div>',
                unsafe_allow_html=True)
    if not corridor.empty:
        row = corridor.iloc[0]
        st.markdown(
            f'<div class="report-body">{row["report_body"]}</div>',
            unsafe_allow_html=True
        )
        st.caption(
            f"Model: {row['model_used']} · "
            f"Tokens: {row['token_count']} · "
            f"Generated: {str(row['generated_at'])[:16]}"
        )

    st.markdown("---")
    st.markdown('<div class="section-title">📄 Suburb Reports</div>',
                unsafe_allow_html=True)

    if not suburb_r.empty:
        sel = st.selectbox("Select suburb", suburb_r["suburb"].tolist())
        row = suburb_r[suburb_r["suburb"] == sel].iloc[0]
        st.markdown(f"### {row['report_title']}")
        st.markdown(
            f'<div class="report-body">{row["report_body"]}</div>',
            unsafe_allow_html=True
        )
        if row["key_insights"]:
            st.markdown("**Key Data Points:**")
            cols = st.columns(len(row["key_insights"]))
            for i, ins in enumerate(row["key_insights"]):
                with cols[i]: st.info(ins)
        st.caption(
            f"Model: {row['model_used']} · "
            f"Tokens: {row['token_count']} · "
            f"Generated: {str(row['generated_at'])[:16]}"
        )

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#334155;
            padding:16px; font-size:12px;'>
    <b style='color:#475569;'>PropMarket Intelligence Platform</b> ·
    Built by <b style='color:#f59e0b;'>Khoshaba Odeesho</b> ·
    <a href='https://github.com/Assyrian91'
       style='color:#3b82f6;'>Assyrian AI</a><br>
    Data: Victorian Government · REIV · Valuer-General VIC ·
    ML: XGBoost + Linear Regression ·
    AI: Gemini 2.0 Flash · DB: Supabase PostgreSQL
</div>
""", unsafe_allow_html=True)