import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe

# --- ⚠️ 你的網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"

# --- 設定 ---
TIME_OPTIONS = []
for h in range(8, 17):
    for m in [0, 30]:
        if h == 16 and m > 30: break
        TIME_OPTIONS.append(time(h, m))

# --- 連線函數 ---
def get_worksheet():
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            creds = st.secrets["connections"]["gsheets"]["service_account"]
        else:
            creds = st.secrets["service_account"]
        gc = gspread.service_account_from_dict(creds)
        sh = gc.open_by_url(SHEET_URL)
        return sh.worksheet("Sheet1")
    except Exception as e:
        # 暫時忽略連線錯誤，避免洗版，交由 load_data 處理
        return None

# 👇 改良點：加上快取功能 (ttl=10 代表資料會暫存 10 秒)
# 這樣就算你狂按按鈕，也不會一直消耗 Google 的額度
@st.cache_data(ttl=10)
def load_data():
    ws = get_worksheet()
    if ws:
        try:
            # 讀取資料
            df = get_as_dataframe(ws, usecols=[0,1,2,3,4,5], parse_dates=False, dtype=str)
            df = df.dropna(how='all') # 刪除空行
            df = df.fillna("") # 填補空值
            df = df[df['日期'] != ""] # 過濾無效日期
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["日期", "開始時間", "結束時間", "大名", "預約內容", "登記時間"])

def save_data(df):
    ws = get_worksheet()
    if ws:
        try:
            ws.clear()
            set_with_dataframe(ws, df)
            # 👇 關鍵：寫入後，立刻清除快取，這樣才會馬上看到新資料
            load_data.clear()
        except Exception as e:
            st.error(f"寫入失敗: {e}")

def check_overlap(df, check_date, start_t, end_t):
    if df.empty or '日期' not in df.columns: return None
    
    check_date_str = check_date.strftime("%Y-%m-%d")
    
    # 建立臨時欄位統一格式
    # 這裡加上 .astype(str) 確保不會因為資料格式問題報錯
    df['temp_date'] = df['日期'].astype(str).str.replace('/', '-').str.strip()
    
    day_bookings = df[df['temp_date'] == check_date_str]
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
            # 這裡我們不讀取快取，強制重新抓一次最新資料來檢查衝突
            load_data.clear() 
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
                    new_row = {
                        "日期": date_val.strftime("%Y-%m-%d"), 
                        "開始時間": s_time.strftime("%H:%M:%S"), 
                        "結束時間": e_time.strftime("%H:%M:%S"), 
                        "大名": name, 
                        "預約內容": content, 
                        "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    new_df = pd.DataFrame([new_row])
                    updated_df = pd.concat([df, new_df], ignore_index=True)
                    save_data(updated_df)
                    st.success("✅ 預約成功！")
                    st.rerun()

st.markdown("---")

# 讀取資料 (這裡會使用快取，不會一直扣額度)
df = load_data()

# 除錯用：如果還是 429，可以把這行打開看是不是資料有進來
# st.write(f"資料筆數: {len(df)}")

view_mode = st.radio("模式", ["📱 清單", "💻 週視圖"], horizontal=True)
events = []

if not df.empty and '日期' in df.columns:
    for _, row in df.iterrows():
        try:
            clean_date = str(row['日期']).replace('/', '-').strip()
            if not clean_date: continue 
            
            start_iso = f"{clean_date}T{row['開始時間']}"
            end_iso = f"{clean_date}T{row['結束時間']}"
            
            events.append({
                "title": f"{row['大名']}: {row['預約內容']}", 
                "start": start_iso, 
                "end": end_iso, 
                "backgroundColor": "#3788d8"
            })
        except:
            continue
        
calendar(events=events, options={
    "initialView": "listWeek" if view_mode == "📱 清單" else "timeGridWeek", 
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""}, 
    "height": "auto"
})

with st.expander("🗑️ 刪除"):
    if not df.empty:
        df['刪除'] = False
        edited = st.data_editor(df, column_config={"刪除": st.column_config.CheckboxColumn(required=True)})
        if st.button("確認刪除"):
            items_to_keep = edited[edited['刪除'] == False]
            final_df = items_to_keep.drop(columns=['刪除'])
            save_data(final_df)
            st.rerun()