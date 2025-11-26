import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# --- 1. 設定區 ---
# 你的 Google 試算表網址 (請確認這是對的)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"

# 產生時間選項 (08:00 - 16:30)
TIME_OPTIONS = []
for h in range(8, 17):
    for m in [0, 30]:
        if h == 16 and m > 30: break
        TIME_OPTIONS.append(time(h, m))

# --- 2. 函數區 (這裡是電腦的大腦) ---

def load_data():
    """讀取 Google 試算表資料"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 指定讀取 Sheet1
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
        return df
    except Exception as e:
        # 如果讀取失敗，回傳一個空的格式，避免程式當機
        st.warning(f"⚠️ 讀取資料時發生狀況 (可能是空表或連線問題): {e}")
        return pd.DataFrame(columns=["日期", "開始時間", "結束時間", "大名", "預約內容", "登記時間"])

def save_data(df):
    """寫入資料回 Google 試算表"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
    except Exception as e:
        st.error(f"❌ 寫入失敗，請檢查權限: {e}")

def check_overlap(df, check_date, start_t, end_t):
    """檢查時間是否衝突 (這個函數之前不見了，現在加回來)"""
    # 如果資料表是空的，或者沒有日期欄位，直接通過
    if df.empty or '日期' not in df.columns:
        return None
    
    # 轉換格式以便比對
    check_date_str = check_date.strftime("%Y-%m-%d")
    # 確保日期欄位是字串格式
    df['日期'] = df['日期'].astype(str)
    
    # 篩選出同一天的預約
    day_bookings = df[df['日期'] == check_date_str]