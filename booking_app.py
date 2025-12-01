import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from PIL import Image

# --- ⚠️ 你的網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"
ADMIN_PASSWORD = "8888"

# --- 選項設定 ---
LOCATION_OPTIONS = ["小會議室", "大會議室", "洽談室Ａ", "洽談室Ｂ", "行銷部辦公室"]
THEME_COLOR = "#D4A59A" # 主題色

TIME_OPTIONS = []
for h in range(8, 17):
    for m in [0, 30]:
        if h == 16 and m > 30: break
        TIME_OPTIONS.append(time(h, m))

# --- 頁面設定 ---
st.set_page_config(page_title="行銷部會議預約", page_icon="📅", layout="wide", initial_sidebar_state="collapsed")

# --- 樣式與 Logo ---
try:
    logo = Image.open("logo.png")
    col_logo, col_title = st.columns([1, 5])
    with col_logo: st.image(logo, width=100)
    with col_title: st.title("📅 行銷部會議預約系統")
except:
    st.title("📅 行銷部會議預約系統")

st.markdown(f"""
    <style>
    .stButton>button {{ background-color: {THEME_COLOR}; color: white; border: None; }}
    .stButton>button:hover {{ background-color: #B88B81; }}
    a {{ color: {THEME_COLOR}; }}
    </style>
""", unsafe_allow_html=True)

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
    except Exception: return None

def fix_time(t_str):
    if not t_str: return None
    t_str = str(t_str).strip()
    if t_str.count(":") == 1: t_str += ":00"
    try: return datetime.strptime(t_str, "%H:%M:%S").strftime("%H:%M:%S")
    except: return None

@st.cache_data(ttl=5)
def load_data():
    ws = get_worksheet()
    if ws:
        try:
            df = get_as_dataframe(ws, usecols=[0,1,2,3,4,5,6,7], parse_dates=False, dtype=str)
            df = df.dropna(how='all')
            df = df.fillna("")
            df = df[df['日期'].str.len() > 0]
            if '狀態' not in df.columns: df['狀態'] = '核准'
            if '會議地點' not in df.columns: df['會議地點'] = ''
            return df
        except: pass
    return pd.DataFrame(columns=["日期", "開始時間", "結束時間", "大名", "會議地點", "預約內容", "登記時間", "狀態"])

def save_data(df):
    ws = get_worksheet()
    if ws:
        try:
            cols = ["日期", "開始時間", "結束時間", "大名", "會議地點", "預約內容", "登記時間", "狀態"]
            df = df[cols]
            ws.clear()
            set_with_dataframe(ws, df)
            load_data.clear()
        except Exception as e: st.error(f"寫入失敗: {e}")

def check_overlap(df, check_date, start_t, end_t):
    if df.empty or '日期' not in df.columns: return None
    check_date_str = check_date.strftime("%Y-%m-%d")
    df['temp_date'] = df['日期'].astype(str).str.replace('/', '-').str.strip()
    day_bookings = df[(df['temp_date'] == check_date_str) & (df['狀態'] != '拒絕')]
    if day_bookings.empty: return None
    start_str = start_t.strftime("%H:%M:%S")
    end_str = end_t.strftime("%H:%M:%S")
    overlap = day_bookings[(day_bookings['開始時間'] < end_str) & (day_bookings['結束時間'] > start_str)]
    if not overlap.empty: return overlap.iloc[0]['大名']
    return None

# --- 🔥 新增：彈跳視窗函數 (顯示詳情用) ---
@st.dialog("📋 會議詳細資訊")
def show_event_details(event_props):
    st.markdown(f"### **{event_props.get('content', '無內容')}**")
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("📍 會議地點")
        st.info(event_props.get('location', '未指定'))
    with col2:
        st.caption("👤 預約人")
        st.info(event_props.get('name', '未知'))
        
    st.caption("⏰ 會議時間")
    # 這裡顯示美化過的時間
    time_range = event_props.get('pretty_time', '')
    st.warning(time_range if time_range else "時間未定")
    
    if event_props.get('status'):
        st.caption("📌 狀態")
        st.write(event_props.get('status'))

# --- 主程式 ---
st.sidebar.header("🔒 管理員專區")
admin_pwd = st.sidebar.text_input("輸入密碼", type="password")
is_admin = admin_pwd == ADMIN_PASSWORD

if not is_admin:
    with st.expander("➕ 申請預約 (需審核)", expanded=True):
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("預約人大名")
            date_val = c1.date_input("日期", min_value=datetime.today())
            s_time = c2.selectbox("開始", TIME_OPTIONS, index=0)
            e_time = c2.selectbox("結束", TIME_OPTIONS, index=2)
            loc = st.selectbox("地點", LOCATION_OPTIONS)
            content = st.text_input("內容")
            if st.form_submit_button("送出", use_container_width=True):
                load_data.clear()
                df = load_data()
                if not name or not content: st.error("❌ 請填寫完整資訊")
                elif s_time >= e_time: st.error("❌ 時間錯誤")
                else:
                    conflict = check_overlap(df, date_val, s_time, e_time)
                    if conflict: st.error(f"❌ 衝突：該時段已被「{conflict}」預約")
                    else:
                        new_row = {"日期": date_val.strftime("%Y-%m-%d"), "開始時間": s_time.strftime("%H:%M:%S"), "結束時間": e_time.strftime("%H:%M:%S"), "大名": name, "會議地點": loc, "預約內容": content, "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "狀態": "待審核"}
                        save_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        st.success("✅ 申請已送出！")
                        st.rerun()
else:
    st.sidebar.success("管理員已登入")
    st.markdown(f"<h3 style='color:{THEME_COLOR}'>📋 審核後台</h3>", unsafe_allow_html=True)
    load_data.clear()
    df = load_data()
    if not df.empty:
        edited_df = st.data_editor(df, column_config={"狀態": st.column_config.SelectboxColumn("狀態", options=["待審核", "核准", "拒絕"], required=True), "會議地點": st.column_config.TextColumn(disabled=True)}, num_rows="dynamic", key="admin", use_container_width=True)
        if st.button("💾 儲存變更", type="primary", use_container_width=True):
            save_data(edited_df)
            st.success("已更新")
            st.rerun()

st.markdown(f"<hr style='border-top: 2px solid {THEME_COLOR};'>", unsafe_allow_html=True)

# --- 行事曆準備 ---
df = load_data()
view_mode = st.radio("檢視", ["📱 列表", "💻 週視圖"], horizontal=True)
events = []

if not df.empty and '日期' in df.columns:
    for _, row in df.iterrows():
        try:
            status = row.get('狀態', '核准')
            if not is_admin and status != '核准': continue
            
            clean_date = str(row['日期']).replace('/', '-').strip()
            start_t = fix_time(row['開始時間'])
            end_t = fix_time(row['結束時間'])
            if not start_t or not end_t: continue
            
            loc = row.get('會議地點', '未指定')
            bg_color = THEME_COLOR
            if status == '待審核': bg_color = "#F39C12"
            elif status == '拒絕': bg_color = "#7F8C8D"

            # 簡化標題，避免太擠
            title_text = f"[{loc}] {row['大名']}"
            if is_admin: title_text = f"({status}) {title_text}"

            events.append({
                "title": title_text,
                "start": f"{clean_date}T{start_t}",
                "end": f"{clean_date}T{end_t}",
                "backgroundColor": bg_color,
                "borderColor": bg_color,
                "textColor": "#FFFFFF",
                # 🔥 這裡埋入詳細資料，給彈跳視窗用
                "extendedProps": {
                    "location": loc,
                    "name": row['大名'],
                    "content": row['預約內容'],
                    "status": status,
                    "pretty_time": f"{start_t[:5]} - {end_t[:5]}" # 只顯示 HH:MM
                }
            })
        except: continue

# --- 顯示行事曆並監聽點擊 ---
calendar_options = {
    "initialView": "listWeek" if view_mode == "📱 列表" else "timeGridWeek",
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
    "height": "auto",
    "slotMinTime": "08:00:00",
    "slotMaxTime": "19:00:00",
    "allDaySlot": False
}

calendar_state = calendar(events=events, options=calendar_options)

# 🔥 偵測點擊事件，彈出視窗
if calendar_state.get("eventClick"):
    event_data = calendar_state["eventClick"]["event"]
    props = event_data.get("extendedProps", {})
    # 呼叫彈跳視窗函數
    show_event_details(props)

if is_admin: st.caption(f"🟦 核准 | 🟧 待審核 | ⬜ 拒絕")