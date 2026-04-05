import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. THE REFINED GROUND TRUTH (Reflecting your specific corrections) ---
FTR_DATA = {
    'AGNCL':  {'spread': 0.0570,  'reset': '10/15/2027', 'yahoo': 'AGNCL',   'coupon': 0.0775},
    'EFC-B':  {'spread': 0.0569,  'reset': '12/15/2024', 'yahoo': 'EFC-PB',  'coupon': 0.0932},
    'EFC-C':  {'spread': 0.0546,  'reset': '06/15/2025', 'yahoo': 'EFC-PC',  'coupon': 0.08625},
    'RITM-D': {'spread': 0.0622,  'reset': '11/15/2026', 'yahoo': 'RITM-PD', 'coupon': 0.0700},
    'RITM-F': {'spread': 0.0580,  'reset': '10/15/2026', 'yahoo': 'RITM-PF', 'coupon': 0.0875},
    'RWT-A':  {'spread': 0.06278, 'reset': '04/15/2028', 'yahoo': 'RWT-PA',  'coupon': 0.1000},
    'FTAIM':  {'spread': 0.05162, 'reset': '06/15/2028', 'yahoo': 'FTAIM',   'coupon': 0.0950}
}

# Corrected 2026 Dividend Calendar
DATES_DB = {
    'AGNCL':  {'ex': '03/31/2026', 'pay': '04/10/2026'},
    'EFC-B':  {'ex': '03/31/2026', 'pay': '04/30/2026'},
    'EFC-C':  {'ex': '03/31/2026', 'pay': '04/30/2026'},
    'RITM-D': {'ex': '05/01/2026', 'pay': '05/15/2026'},
    'RITM-F': {'ex': '05/01/2026', 'pay': '05/15/2026'},
    'RWT-A':  {'ex': '04/01/2026', 'pay': '04/15/2026'},
    'FTAIM':  {'ex': '06/01/2026', 'pay': '06/15/2026'}
}

def get_30_360_days(start, end):
    """US 30/360 bond basis calculation."""
    d1 = min(start.day, 30)
    d2 = 30 if (d1 >= 30 and end.day == 31) else end.day
    if start.month == 2 and (start + timedelta(days=1)).month == 3: d1 = 30
    if end.month == 2 and (end + timedelta(days=1)).month == 3: d2 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)

# --- 2. STREAMLIT UI ---
st.set_page_config(page_title="5Y Treasury Tracker", layout="wide")
st.title("🏛️ 5-Year Treasury Reset Preferreds")

st.sidebar.header("Market Benchmarks")
live_5y = st.sidebar.number_input("Current 5Y Treasury Rate (%)", value=3.94, step=0.01) / 100

# 3. LIVE DATA FETCHING
tickers_to_fetch = [v['yahoo'] for v in FTR_DATA.values()]
prices = {}
with st.spinner('Fetching live prices...'):
    for t in tickers_to_fetch:
        try:
            val = yf.Ticker(t).history(period="1d")['Close']
            prices[t] = val.iloc[-1] if not val.empty else 25.0
        except:
            prices[t] = 25.0

# 4. CALCULATION ENGINE
today = datetime.now()
main_list = []
sens_list = []

for ticker, info in FTR_DATA.items():
    price = float(prices.get(info['yahoo'], 25.0))
    
    # Ex-Date Logic: Check if we are past the ex-date
    orig_ex = datetime.strptime(DATES_DB[ticker]['ex'], '%m/%d/%Y')
    orig_pay = datetime.strptime(DATES_DB[ticker]['pay'], '%m/%d/%Y')
    
    if today > orig_ex:
        # BUYER DOES NOT GET CURRENT DIVIDEND. Accrual starts from the current Ex-Date.
        # Next payday is 3 months later.
        accrual_start_date = orig_ex
        display_ex = orig_ex + pd.DateOffset(months=3)
        display_pay = orig_pay + pd.DateOffset(months=3)
    else:
        # BUYER GETS CURRENT DIVIDEND. Accrual includes the previous full quarter.
        accrual_start_date = orig_pay - pd.DateOffset(months=3)
        display_ex = orig_ex
        display_pay = orig_pay

    days_accrued = get_30_360_days(accrual_start_date, today)
    
    # Financial Calculations
    full_q_div = (25 * info['coupon']) / 4
    accrued_val = (25 * info['coupon']) * (days_accrued / 360)
    
    clean_p = price - accrued_val
    curr_yield = (info['coupon'] * 25) / clean_p if clean_p > 0 else 0
    
    # Future Yield Projection
    reset_coupon = live_5y + info['spread']
    fwd_yield = (reset_coupon * 25) / clean_p if clean_p > 0 else 0

    main_list.append({
        "Ticker": ticker,
        "Coupon (%)": f"{info['coupon']*100:.2f}",
        "Price": f"{price:.2f}",
        "Accrued Div": f"{accrued_val:.2f}",
        "Full Qtr Div": f"{full_q_div:.2f}",
        "Clean Price": f"{clean_p:.2f}",
        "Curr Yield (%)": f"{curr_yield*100:.2f}",
        "Reset Spread (%)": f"{info['spread']*100:.3f}",
        "Next Reset": info['reset'],
        "Next Ex-Div": display_ex.strftime('%m/%d/%Y'),
        "Next Payment": display_pay.strftime('%m/%d/%Y')
    })

    # Sensitivity Table
    sens_row = {"Ticker": ticker}
    for rate in [0.03, 0.035, 0.04, 0.045, 0.05]:
        s_yield = ((rate + info['spread']) * 25) / clean_p if clean_p > 0 else 0
        sens_row[f"{rate*100:.1f}% UST"] = f"{s_yield*100:.2f}"
    sens_list.append(sens_row)

# 5. RENDER TABLES
df_main = pd.DataFrame(main_list)
df_sens = pd.DataFrame(sens_list)

st.subheader("Sortable Portfolio Dashboard")
st.dataframe(df_main, use_container_width=True, hide_index=True)

st.subheader("Yield Sensitivity (At Future Reset)")
st.dataframe(df_sens, use_container_width=True, hide_index=True)
