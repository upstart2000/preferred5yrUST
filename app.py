import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import dateutil.relativedelta as rd

# --- 1. VERIFIED HARD DATA ---
FTR_DATA = {
    'AGNCL':  {'spread': 0.0570,  'reset': '10/15/2027', 'yahoo': 'AGNCL',   'coupon': 0.0775,  'ref_ex': '03/31/2024', 'pay_day': 10},
    'EFC-B':  {'spread': 0.0569,  'reset': '01/30/2027', 'yahoo': 'EFC-PB',  'coupon': 0.0625,  'ref_ex': '03/31/2024', 'pay_day': 30}, 
    'EFC-C':  {'spread': 0.0546,  'reset': '04/30/2028', 'yahoo': 'EFC-PC',  'coupon': 0.08625, 'ref_ex': '03/31/2024', 'pay_day': 30},
    'RITM-D': {'spread': 0.0622,  'reset': '11/15/2026', 'yahoo': 'RITM-PD', 'coupon': 0.0700,  'ref_ex': '02/01/2024', 'pay_day': 15},
    'RITM-F': {'spread': 0.0580,  'reset': '02/15/2031', 'yahoo': 'RITM-PF', 'coupon': 0.0875,  'ref_ex': '02/01/2024', 'pay_day': 15}, # FIXED
    'RWT-A':  {'spread': 0.06278, 'reset': '04/15/2028', 'yahoo': 'RWT-PA',  'coupon': 0.1000,  'ref_ex': '04/01/2024', 'pay_day': 15},
    'FTAIM':  {'spread': 0.05162, 'reset': '06/15/2028', 'yahoo': 'FTAIM',   'coupon': 0.0950,  'ref_ex': '03/01/2024', 'pay_day': 15}
}

def get_next_dates(ref_ex_str, pay_day_target):
    today = datetime.now()
    current_ex = datetime.strptime(ref_ex_str, '%m/%d/%Y')
    while current_ex <= today:
        current_ex += rd.relativedelta(months=3)
    next_pay = current_ex.replace(day=pay_day_target)
    if next_pay < current_ex:
        next_pay += rd.relativedelta(months=1)
    return current_ex.date(), next_pay.date()

def get_30_360_days(start, end):
    d1 = min(start.day, 30)
    d2 = 30 if (d1 >= 30 and end.day == 31) else end.day
    if start.month == 2 and (start + timedelta(days=1)).month == 3: d1 = 30
    if end.month == 2 and (end + timedelta(days=1)).month == 3: d2 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)

# --- 2. UI SETUP ---
st.set_page_config(page_title="5Y Treasury Tracker", layout="wide")
st.title("🏛️ 5-Year Treasury Reset Preferreds")

col_a, col_b, _ = st.columns([1.5, 1.5, 3])
with col_a:
    pivot_rate = st.number_input("Pivot 5Y Treasury Rate (%)", value=3.94, step=0.01)
with col_b:
    increment_bps = st.number_input("Increment (Basis Points)", value=50, step=10)

inc_dec = increment_bps / 10000  
today = datetime.now()

# 3. CALCULATIONS (RAW NUMBERS ONLY)
main_data = []
target_rates = [(pivot_rate/100) + (i * inc_dec) for i in range(-2, 3)]

for ticker, info in FTR_DATA.items():
    try:
        price = float(yf.Ticker(info['yahoo']).history(period="1d")['Close'].iloc[-1])
    except:
        price = 25.0
    
    next_ex, next_pay = get_next_dates(info['ref_ex'], info['pay_day'])
    prior_ex = next_ex - rd.relativedelta(months=3)
    days_accrued = get_30_360_days(prior_ex, today.date())
    
    accrued_val = (25 * info['coupon']) * (days_accrued / 360)
    clean_p = price - accrued_val
    curr_yield = (info['coupon'] * 25) / clean_p if clean_p > 0 else 0
    fwd_yield = ((pivot_rate/100) + info['spread']) * 25 / clean_p if clean_p > 0 else 0

    main_data.append({
        "Ticker": ticker,
        "Coupon": info['coupon'],
        "Price": price,
        "Accrued": accrued_val,
        "Clean Price": clean_p,
        "Curr Yield": curr_yield,
        "Fwd Yield": fwd_yield,
        "Spread": info['spread'],
        "Next Ex-Div": next_ex,
        "Next Pay": next_pay,
        "Next Reset": datetime.strptime(info['reset'], '%m/%d/%Y').date()
    })

df = pd.DataFrame(main_data)

# 4. RENDER WITH COLUMN CONFIG (FOR SORTING)
st.subheader("Sortable Portfolio Dashboard")
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Coupon": st.column_config.NumberColumn(format="%.2f%%"),
        "Price": st.column_config.NumberColumn(format="$%.2f"),
        "Accrued": st.column_config.NumberColumn(format="$%.3f"),
        "Clean Price": st.column_config.NumberColumn(format="$%.2f"),
        "Curr Yield": st.column_config.NumberColumn(format="%.2f%%"),
        "Fwd Yield": st.column_config.NumberColumn(format="%.2f%%"),
        "Spread": st.column_config.NumberColumn(format="%.3f%%"),
        "Next Ex-Div": st.column_config.DateColumn(format="MM/DD/YYYY"),
        "Next Pay": st.column_config.DateColumn(format="MM/DD/YYYY"),
        "Next Reset": st.column_config.DateColumn(format="MM/DD/YYYY"),
    }
)
