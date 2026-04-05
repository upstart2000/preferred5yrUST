import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
# Note: Ensure 'pip install python-dateutil' is run in your environment
import dateutil.relativedelta as rd

# --- 1. THE DATA ENGINE (CORE CONSTANTS ONLY) ---
# No "Next" dates here. Only the repeating DNA of the security.
FTR_DATA = {
    'AGNCL':  {'spread': 0.0570,  'reset': '10/15/2027', 'yahoo': 'AGNCL',   'coupon': 0.0775,  'ref_ex': '03/31/2024', 'pay_day': 10},
    'EFC-B':  {'spread': 0.0569,  'reset': '01/30/2027', 'yahoo': 'EFC-PB',  'coupon': 0.0625,  'ref_ex': '03/31/2024', 'pay_day': 30}, 
    'EFC-C':  {'spread': 0.0546,  'reset': '04/30/2028', 'yahoo': 'EFC-PC',  'coupon': 0.08625, 'ref_ex': '03/31/2024', 'pay_day': 30},
    'RITM-D': {'spread': 0.0622,  'reset': '11/15/2026', 'yahoo': 'RITM-PD', 'coupon': 0.0700,  'ref_ex': '02/01/2024', 'pay_day': 15},
    'RITM-F': {'spread': 0.0580,  'reset': '02/15/2031', 'yahoo': 'RITM-PF', 'coupon': 0.0875,  'ref_ex': '02/01/2024', 'pay_day': 15},
    'RWT-A':  {'spread': 0.06278, 'reset': '04/15/2028', 'yahoo': 'RWT-PA',  'coupon': 0.1000,  'ref_ex': '04/01/2024', 'pay_day': 15},
    'FTAIM':  {'spread': 0.05162, 'reset': '06/15/2028', 'yahoo': 'FTAIM',   'coupon': 0.0950,  'ref_ex': '03/01/2024', 'pay_day': 15}
}

def get_next_dates(ref_ex_str, pay_day_target):
    """Computes the NEXT Ex-Date and Pay-Date dynamically based on Today."""
    today = datetime.now()
    current_ex = datetime.strptime(ref_ex_str, '%m/%d/%Y')
    
    # Logic: Roll forward by 3 months until current_ex is strictly in the future
    while current_ex <= today:
        current_ex += rd.relativedelta(months=3)
    
    # Logic: Set payment date based on the target day of the month
    next_pay = current_ex.replace(day=pay_day_target)
    if next_pay < current_ex:
        next_pay += rd.relativedelta(months=1)
        
    return current_ex, next_pay

def get_30_360_days(start, end):
    """Standard 30/360 bond basis math."""
    d1 = min(start.day, 30)
    d2 = 30 if (d1 >= 30 and end.day == 31) else end.day
    if start.month == 2 and (start + timedelta(days=1)).month == 3: d1 = 30
    if end.month == 2 and (end + timedelta(days=1)).month == 3: d2 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)

# --- 2. UI SETUP ---
st.set_page_config(page_title="5Y Treasury Tracker", layout="wide")
st.title("🏛️ 5-Year Treasury Reset Preferreds")

# Top-level dynamic inputs (No sidebar, no wasted space)
col_a, col_b, col_c = st.columns([1.5, 1.5, 3])
with col_a:
    pivot_rate = st.number_input("Pivot 5Y Treasury Rate (%)", value=3.94, step=0.01)
with col_b:
    increment_bps = st.number_input("Increment (Basis Points)", value=50, step=10)

inc_dec = increment_bps / 10000  
today = datetime.now()

# 3. LIVE DATA & CALCS
main_list = []
sens_list = []
target_rates = [(pivot_rate/100) + (i * inc_dec) for i in range(-2, 3)]

for ticker, info in FTR_DATA.items():
    # Fetch Price
    try:
        price = float(yf.Ticker(info['yahoo']).history(period="1d")['Close'].iloc[-1])
    except:
        price = 25.0
    
    # Get Dynamic Dates
    next_ex, next_pay = get_next_dates(info['ref_ex'], info['pay_day'])
    
    # Accrual logic: Prior Ex-Date is exactly 3 months before the Next Ex-Date
    prior_ex = next_ex - rd.relativedelta(months=3)
    days_accrued = get_30_360_days(prior_ex, today)
    
    # Financial Formulas
    full_q_div = (25 * info['coupon']) / 4
    accrued_val = (25 * info['coupon']) * (days_accrued / 360)
    clean_p = price - accrued_val
    curr_yield = (info['coupon'] * 25) / clean_p if clean_p > 0 else 0
    fwd_yield_pivot = ((pivot_rate/100) + info['spread']) * 25 / clean_p if clean_p > 0 else 0

    main_list.append({
        "Ticker": ticker,
        "Coupon (%)": f"{info['coupon']*100:.2f}",
        "Price": f"{price:.2f}",
        "Accrued Div": f"{accrued_val:.2f}",
        "Full Qtr Div": f"{full_q_div:.2f}",
        "Clean Price": f"{clean_p:.2f}",
        "Curr Yield (%)": f"{curr_yield*100:.2f}",
        "Fwd Yield (%)": f"{fwd_yield_pivot*100:.2f}",
        "Reset Spread (%)": f"{info['spread']*100:.3f}",
        "Next Ex-Div": next_ex.strftime('%m/%d/%Y'),
        "Next Payment": next_pay.strftime('%m/%d/%Y'),
        "Next Reset": info['reset'] 
    })

    sens_row = {"Ticker": ticker}
    for r in target_rates:
        label = f"{r*100:.2f}% UST"
        s_yield = ((r + info['spread']) * 25) / clean_p if clean_p > 0 else 0
        sens_row[label] = f"{s_yield*100:.2f}"
    sens_list.append(sens_row)

# 4. FINAL OUTPUT
st.subheader("Sortable Portfolio Dashboard")
st.dataframe(pd.DataFrame(main_list), use_container_width=True, hide_index=True)
st.divider()
st.subheader(f"Yield Sensitivity (Centered @ {pivot_rate:.2f}%)")
st.dataframe(pd.DataFrame(sens_list), use_container_width=True, hide_index=True)
