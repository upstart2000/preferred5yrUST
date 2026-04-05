import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. VERIFIED HARD DATA (NO ASSUMPTIONS) ---
FTR_DATA = {
    'AGNCL':  {'spread': 0.0570,  'reset': '10/15/2027', 'yahoo': 'AGNCL',   'coupon': 0.0775},
    'EFC-B':  {'spread': 0.0569,  'reset': '01/30/2027', 'yahoo': 'EFC-PB',  'coupon': 0.0625}, 
    'EFC-C':  {'spread': 0.0546,  'reset': '04/30/2028', 'yahoo': 'EFC-PC',  'coupon': 0.08625},
    'RITM-D': {'spread': 0.0622,  'reset': '11/15/2026', 'yahoo': 'RITM-PD', 'coupon': 0.0700},
    'RITM-F': {'spread': 0.0580,  'reset': '10/15/2026', 'yahoo': 'RITM-PF', 'coupon': 0.0875},
    'RWT-A':  {'spread': 0.06278, 'reset': '04/15/2028', 'yahoo': 'RWT-PA',  'coupon': 0.1000},
    'FTAIM':  {'spread': 0.05162, 'reset': '06/15/2028', 'yahoo': 'FTAIM',   'coupon': 0.0950}
}

DATES_DB = {
    'AGNCL':  {'next_ex': '06/30/2026', 'pay': '07/10/2026'},
    'EFC-B':  {'next_ex': '06/30/2026', 'pay': '07/30/2026'},
    'EFC-C':  {'next_ex': '06/30/2026', 'pay': '07/30/2026'},
    'RITM-D': {'next_ex': '05/01/2026', 'pay': '05/15/2026'},
    'RITM-F': {'next_ex': '05/01/2026', 'pay': '05/15/2026'},
    'RWT-A':  {'next_ex': '07/01/2026', 'pay': '07/15/2026'},
    'FTAIM':  {'next_ex': '06/01/2026', 'pay': '06/15/2026'}
}

def get_30_360_days(start, end):
    d1 = min(start.day, 30)
    d2 = 30 if (d1 >= 30 and end.day == 31) else end.day
    if start.month == 2 and (start + timedelta(days=1)).month == 3: d1 = 30
    if end.month == 2 and (end + timedelta(days=1)).month == 3: d2 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)

# --- 2. UI SETUP ---
st.set_page_config(page_title="5Y Treasury Tracker", layout="wide")
st.title("🏛️ 5-Year Treasury Reset Preferreds")

# TOP ROW CONTROLS
col_a, col_b, col_c = st.columns([1.5, 1.5, 3])
with col_a:
    pivot_rate = st.number_input("Pivot 5Y Treasury Rate (%)", value=3.94, step=0.01)
with col_b:
    increment_bps = st.number_input("Increment (Basis Points)", value=50, step=10) # Set to 50 bps default

inc_dec = increment_bps / 10000  

# 3. LIVE PRICE FETCH
prices = {}
for ticker_key, info in FTR_DATA.items():
    try:
        val = yf.Ticker(info['yahoo']).history(period="1d")['Close']
        prices[ticker_key] = val.iloc[-1] if not val.empty else 25.0
    except:
        prices[ticker_key] = 25.0

# 4. CALCULATION ENGINE
today = datetime.now()
main_list = []
sens_list = []

# Target rates centered on pivot
target_rates = [
    (pivot_rate/100) - (2 * inc_dec),
    (pivot_rate/100) - (1 * inc_dec),
    (pivot_rate/100),
    (pivot_rate/100) + (1 * inc_dec),
    (pivot_rate/100) + (2 * inc_dec)
]

for ticker, info in FTR_DATA.items():
    price = float(prices.get(ticker, 25.0))
    next_ex = datetime.strptime(DATES_DB[ticker]['next_ex'], '%m/%d/%Y')
    
    # Accrual Logic (Prior Ex-Date Anchor)
    prior_ex = next_ex - pd.DateOffset(months=3)
    days_accrued = get_30_360_days(prior_ex, today)
    accrued_val = (25 * info['coupon']) * (days_accrued / 360)
    clean_p = price - accrued_val
    
    # Main Dashboard Data
    curr_yield = (info['coupon'] * 25) / clean_p if clean_p > 0 else 0
    fwd_yield_pivot = ((pivot_rate/100) + info['spread']) * 25 / clean_p if clean_p > 0 else 0

    main_list.append({
        "Ticker": ticker,
        "Coupon (%)": f"{info['coupon']*100:.2f}",
        "Price": f"{price:.2f}",
        "Accrued Div": f"{accrued_val:.2f}",
        "Full Qtr Div": f"{(25 * info['coupon']) / 4:.2f}",
        "Clean Price": f"{clean_p:.2f}",
        "Curr Yield (%)": f"{curr_yield*100:.2f}",
        "Fwd Yield (%)": f"{fwd_yield_pivot*100:.2f}",
        "Reset Spread (%)": f"{info['spread']*100:.3f}",
        "Next Ex-Div": next_ex.strftime('%m/%d/%Y'),
        "Next Payment": DATES_DB[ticker]['pay'],
        "Next Reset": info['reset'] 
    })

    # Sensitivity Logic
    sens_row = {"Ticker": ticker}
    for r in target_rates:
        label = f"{r*100:.2f}% UST"
        s_yield = ((r + info['spread']) * 25) / clean_p if clean_p > 0 else 0
        sens_row[label] = f"{s_yield*100:.2f}"
    sens_list.append(sens_row)

# 5. RENDER TABLES
st.subheader("Sortable Portfolio Dashboard")
st.dataframe(pd.DataFrame(main_list), use_container_width=True, hide_index=True)

st.divider()

st.subheader(f"Yield Sensitivity Analysis (Centered @ {pivot_rate:.2f}%)")
st.dataframe(pd.DataFrame(sens_list), use_container_width=True, hide_index=True)
