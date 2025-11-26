import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe

# --- ⚠️ 你的網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"

# --- 設定 ---
ADMIN_PASSWORD = "8888"  # 🔐 管理員密碼
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
        return None

# --- 修正時間格式 ---
def fix_time(t_str):
    if not t_str: return None
    t_str = str(t_str).strip()
    if t_str.count(":") == 1: t_str += ":00"
    try:
        return datetime.strptime(t_str, "%H:%M:%S").strftime("%H:%M:%S")
    except:
        return None

@st.cache_data(ttl=5)
def load_data():
    ws = get_worksheet()
    if ws:
        try:
            # 讀取 7 個欄位 (A~G)，包含「狀態」
            df = get_as_dataframe(ws, usecols=[0,1,2,3,4,5,6], parse_dates=False, dtype=str)
            df = df.dropna(how='all')
            df = df.fillna("")
            df = df[df['日期'].str.len() > 0]
            
            # 如果舊資料沒有狀態欄，自動補上 "核准"
            if '狀態' not in df.columns:
                df['狀態'] = '核准'
            
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["日期", "開始時間", "結束時間", "大名", "預約內容", "登記時間", "狀態"])

def save_data(df):
    ws = get_worksheet()
    if ws:
        try:
            # 🛡️ 防呆機制：存檔前，把所有不該存在的暫存欄位 (如 temp_date) 刪掉
            cols_to_keep = ["日期", "開始時間", "結束時間", "大名", "預約內容", "登記時間", "狀態"]
            # 只保留標準欄位，其他雜質通通丟掉
            df = df[cols_to_keep]
            
            ws.clear()
            set_with_dataframe(ws, df)
            load_data.clear()
        except Exception as e:
            st.error(f"寫入失敗: {e}")

def check_overlap(df, check_date, start_t, end_t):
    if df.empty or '日期' not in df.columns: return None
    
    check_date_str = check_date.strftime("%Y-%m-%d")
    # 這裡產生的 temp_date 只是暫時用，存檔時會被上面的 save_data 過濾掉
    df['temp_date'] = df['日期'].astype(str).str.replace('/', '-').str.strip()
    
    # 檢查衝突：同一天 + (已核准 或 待審核)
    day_bookings = df[
        (df['temp_date'] == check_date_str) & 
        (df['狀態'] != '拒絕')
    ]
    
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
st.title("📅 部門會議系統 (需審核)")

# --- 側邊欄 ---
st.sidebar.header("🔒 管理員專區")
admin_pwd = st.sidebar.text_input("輸入密碼進入審核", type="password")
is_admin = admin_pwd == ADMIN_PASSWORD

# --- 申請區 ---
if not is_admin:
    with st.expander("➕ 申請預約 (需等待主管審核)", expanded=True):
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("預約人")
            date_val = c1.date_input("日期", min_value=datetime.today())
            s_time = c2.selectbox("開始", TIME_OPTIONS, index=0)
            e_time = c2.selectbox("結束", TIME_OPTIONS, index=2)
            content = st.text_input("內容")
            
            if st.form_submit_button("送出申請", use_container_width=True):
                load_data.clear()
                df = load_data()
                if not name or not content:
                    st.error("❌ 資訊不完整")
                elif s_time >= e_time:
                    st.error("❌ 時間錯誤")
                else:
                    conflict = check_overlap(df, date_val, s_time, e_time)
                    if conflict:
                        st.error(f"❌ 無法申請！該時段已被「{conflict}」佔用 (或審核中)。")
                    else:
                        new_row = {
                            "日期": date_val.strftime("%Y-%m-%d"), 
                            "開始時間": s_time.strftime("%H:%M:%S"), 
                            "結束時間": e_time.strftime("%H:%M:%S"), 
                            "大名": name, 
                            "預約內容": content, 
                            "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "狀態": "待審核"
                        }
                        new_df = pd.DataFrame([new_row])
                        updated_df = pd.concat([df, new_df], ignore_index=True)
                        save_data(updated_df)
                        st.success("✅ 申請已送出！請等待主管核准。")
                        st.rerun()

# --- 管理員區 ---
else:
    st.sidebar.success("🔓 管理員已登入")
    st.markdown("### 📋 審核管理")
    load_data.clear()
    df = load_data()
    
    if not df.empty:
        edited_df = st.data_editor(
            df,
            column_config={
                "狀態": st.column_config.SelectboxColumn("狀態", options=["待審核", "核准", "拒絕"], required=True),
                "刪除": st.column_config.CheckboxColumn(required=True)
            },
            num_rows="dynamic",
            key="admin_editor"
        )
        if st.button("💾 儲存變更", type="primary"):
            save_data(edited_df)
            st.success("已更新！")
            st.rerun()

st.markdown("---")

# --- 行事曆 ---
df = load_data()
view_mode = st.radio("模式", ["📱 清單", "💻 週視圖"], horizontal=True)
events = []

if not df.empty and '日期' in df.columns:
    for _, row in df.iterrows():
        try:
            status = row.get('狀態', '核准')
            # 非管理員只能看已核准的
            if not is_admin and status != '核准': continue
            
            clean_date = str(row['日期']).replace('/', '-').strip()
            start_t = fix_time(row['開始時間'])
            end_t = fix_time(row['結束時間'])
            
            if not start_t or not end_t: continue

            bg_color = "#3788d8"
            if status == '待審核': bg_color = "#f39c12"
            elif status == '拒絕': bg_color = "#7f8c8d"

            title_text = f"{row['大名']}: {row['預約內容']}"
            if is_admin: title_text = f"[{status}] {title_text}"

            events.append({
                "title": title_text, 
                "start": f"{clean_date}T{start_t}", 
                "end": f"{clean_date}T{end_t}", 
                "backgroundColor": bg_color,
                "borderColor": bg_color
            })
        except:
            continue
        
calendar(events=events, options={
    "initialView": "listWeek" if view_mode == "📱 清單" else "timeGridWeek", 
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""}, 
    "height": "auto",
    "slotMinTime": "08:00:00",
    "slotMaxTime": "18:00:00"
})

if is_admin:
    st.caption("🟦 核准 | 🟧 待審核 | ⬜ 拒絕")