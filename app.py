import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. ENHANCED DATA & RESET LOGIC ---
FTR_DATA = {
    'AGNC-L': {'spread': 0.0570,  'reset': '2027-10-15', 'yahoo': 'AGNCL',   'coupon': 0.0775},
    'EFC-B':  {'spread': 0.0569,  'reset': '2024-12-15', 'yahoo': 'EFC-PB',  'coupon': 0.0932},
    'EFC-C':  {'spread': 0.0546,  'reset': '2025-06-15', 'yahoo': 'EFC-PC',  'coupon': 0.08625},
    'RITM-D': {'spread': 0.0622,  'reset': '2026-11-15', 'yahoo': 'RITM-PD', 'coupon': 0.0700},
    'RITM-F': {'spread': 0.0580,  'reset': '2026-10-15', 'yahoo': 'RITM-PF', 'coupon': 0.0875},
    'RWT-A':  {'spread': 0.06278, 'reset': '2028-04-15', 'yahoo': 'RWT-PA',  'coupon': 0.1000},
    'FTAIM':  {'spread': 0.05162, 'reset': '2028-06-15', 'yahoo': 'FTAIM',   'coupon': 0.0950}
}

# Accurate 2026 Cycle Estimates
DATES_DB = {
    'AGNC-L': {'ex': '2026-03-31', 'pay': '2026-04-10'},
    'EFC-B':  {'ex': '2026-03-31', 'pay': '2026-04-30'},
    'EFC-C':  {'ex': '2026-03-31', 'pay': '2026-04-30'},
    'RITM-D': {'ex': '2026-04-06', 'pay': '2026-04-30'}, # RITM common cycle
    'RITM-F': {'ex': '2026-04-06', 'pay': '2026-05-15'}, # RITM-F Specific
    'RWT-A':  {'ex': '2026-04-01', 'pay': '2026-04-15'},
    'FTAIM':  {'ex': '2026-06-08', 'pay': '2026-06-15'}
}

def get_30_360_days(start, end):
    d1 = min(start.day, 30)
    d2 = 30 if (d1 >= 30 and end.day == 31) else end.day
    if start.month == 2 and (start + timedelta(days=1)).month == 3: d1 = 30
    if end.month == 2 and (end + timedelta(days=1)).month == 3: d2 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)

# --- 2. UI SETUP ---
st.set_page_config(page_title="5Y Treasury Reset Dashboard", layout="wide")
st.title("🏛️ 5-Year Treasury Reset Preferreds")
st.markdown("Click any column header to **Sort** by that metric.")

# Sidebar for benchmark rate
st.sidebar.header("Market Benchmarks")
live_5y = st.sidebar.number_input("Current 5Y Treasury Rate (%)", value=3.94, step=0.01) / 100

# 3. LIVE DATA FETCH
tickers = [v['yahoo'] for v in FTR_DATA.values()]
try:
    prices = yf.download(tickers, period="1d")['Close'].iloc[-1].to_dict()
except:
    prices = {t: 25.0 for t in tickers}

# 4. PROCESSING ENGINE
today = datetime.now()
main_list = []
sens_list = []

for ticker, info in FTR_DATA.items():
    price = prices.get(info['yahoo'], 25.0)
    
    # Financial Calculations
    next_pay = datetime.strptime(DATES_DB[ticker]['pay'], '%Y-%m-%d')
    last_pay = next_pay - pd.DateOffset(months=3)
    days_accrued = get_30_360_days(last_pay, today)
    accrued_val = (25 * info['coupon']) * (days_accrued / 360)
    clean_p = price - accrued_val
    curr_yield = (info['coupon'] * 25) / clean_p
    
    # Future/Forward Yield Calculation
    reset_coupon = live_5y + info['spread']
    fwd_yield = (reset_coupon * 25) / clean_p

    main_list.append({
        "Ticker": ticker,
        "Price": round(price, 2),
        "Accrued Dividend": round(accrued_val, 3),
        "Clean Price": round(clean_p, 2),
        "Current Yield (%)": round(curr_yield * 100, 2),
        "Fwd Yield @ Reset (%)": round(fwd_yield * 100, 2),
        "Reset Spread (%)": round(info['spread'] * 100, 3),
        "Next Reset Date": info['reset'],
        "Ex-Dividend Date": DATES_DB[ticker]['ex'],
        "Next Payment": DATES_DB[ticker]['pay']
    })

    # Sensitivity Calculations
    sens_row = {"Ticker": ticker}
    for rate in [0.03, 0.035, 0.04, 0.045, 0.05]:
        s_yield = ((rate + info['spread']) * 25) / clean_p
        sens_row[f"{rate*100:.1f}% UST"] = round(s_yield * 100, 2)
    sens_list.append(sens_row)

# 5. RENDER SORTABLE TABLES
df_main = pd.DataFrame(main_list)
df_sens = pd.DataFrame(sens_list)

st.subheader("Interactive Portfolio View")
st.dataframe(df_main, use_container_width=True, hide_index=True)

st.subheader("Yield-at-Reset Sensitivity Matrix (%)")
st.caption("Forecasted Yield if the 5Y Treasury is at the header rate on the reset date.")
st.dataframe(df_sens, use_container_width=True, hide_index=True)
