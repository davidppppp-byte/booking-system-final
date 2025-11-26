import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
# 👇 關鍵修改：改用舊版套件名稱，配合 requirements.txt
from st_gsheets_connection import GSheetsConnection

# --- ⚠️ 這裡填入你的網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"

# --- 設定 ---
TIME_OPTIONS = []
for h in range(8, 17):
    for m in [0, 30]:
        if h == 16 and m > 30: break
        TIME_OPTIONS.append(time(h, m))

# --- 函數區 ---
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 指定讀取 Sheet1
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
        return df
    except Exception as e:
        st.error(f"讀取失敗，請檢查試算表分頁名稱是否為 Sheet1。錯誤：{e}")
        return pd.DataFrame()

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
    except Exception as e:
        st.error(f"寫入失敗：{e}")

def check_overlap(df, check_date, start_t, end_t):
    if df.empty or '日期' not in df.columns: return None
    check_date_str = check_date.strftime("%Y-%m-%d")
    df['日期'] = df['日期'].astype(str)
    day_bookings = df[df['日期'] == check_date_str]
    if day_bookings.empty: return None
    
    start_str = start_t.strftime("%H:%M:%S")
    end_str = end_t.strftime("%H:%M:%S")
    overlap = day_bookings[
        (day_bookings['開始時間'] < end_str) & 
        (day_bookings['結束時間'] > start_str)
    ]
    if not overlap.empty: return overlap.iloc[0]['大名']
    return None

# --- 頁面 ---
st.set_page_config(page_title="會議預約系統", layout="wide", page_icon="📅")
st.title("📅 部門會議系統")

with st.expander("➕ 新增預約", expanded=True):
    with st.form("booking_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("預約人")
        date_val = c1.date_input("日期", min_value=datetime.today())
        s_time = c2.selectbox("開始", TIME_OPTIONS, index=0)
        e_time = c2.selectbox("結束", TIME_OPTIONS, index=2)
        content = st.text_input("內容")
        if st.form_submit_button("送出預約", use_container_width=True):
            df = load_data()
            if not name or not content:
                st.error("❌ 資訊不完整")
            elif s_time >= e_time:
                st.error("❌ 時間錯誤")
            else:
                conflict = check_overlap(df, date_val, s_time, e_time)
                if conflict:
                    st.error(f"❌ 衝突！已被 {conflict} 預約")
                else:
                    new_row = {"日期": date_val.strftime("%Y-%m-%d"), "開始時間": s_time.strftime("%H:%M:%S"), "結束時間": e_time.strftime("%H:%M:%S"), "大名": name, "預約內容": content, "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    save_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                    st.success("✅ 預約成功！")
                    st.rerun()

st.markdown("---")
# 顯示行事曆
view_mode = st.radio("模式", ["📱 清單", "💻 週視圖"], horizontal=True)
df = load_data()
events = []
if not df.empty and '日期' in df.columns:
    for _, row in df.iterrows():
        events.append({"title": f"{row['大名']}: {row['預約內容']}", "start": f"{row['日期']}T{row['開始時間']}", "end": f"{row['日期']}T{row['結束時間']}", "backgroundColor": "#3788d8"})
calendar(events=events, options={"initialView": "listWeek" if view_mode == "📱 清單" else "timeGridWeek", "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""}, "height": "auto"})

# 刪除區
with st.expander("🗑️ 刪除"):
    if not df.empty:
        df['刪除'] = False
        edited = st.data_editor(df, column_config={"刪除": st.column_config.CheckboxColumn(required=True)})
        if st.button("確認刪除"):
            save_data(edited[edited['刪除'] == False].drop(columns=['刪除']))
            st.rerun()