import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from PIL import Image
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- ⚠️ 你的網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"
ADMIN_PASSWORD = "8888"

# --- 選項設定 ---
LOCATION_OPTIONS = [
    "小會議室", "大會議室", "洽談室Ａ", "洽談室Ｂ", "行銷部辦公室", 
    "崇德門市", "生產中心", "物流中心", "線上", "外部"
]

# --- 🎨 UI 設定：科技感配色 (Tech Blue) ---
THEME_COLOR = "#2980B9"  # 科技藍 (專業、信任感)
BG_COLOR = "#F8F9FA"     # 極淺灰背景 (護眼)
CARD_COLOR = "#FFFFFF"   # 卡片白底

TIME_OPTIONS = []
# 修改：範圍改成 8 點到 17 點 (包含 17:00)
for h in range(8, 18): 
    for m in [0, 30]:
        if h == 17 and m > 0: break # 17:00 後就不加 17:30 了
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

# --- 🎨 CSS 優化：科技感介面 ---
st.markdown(f"""
    <style>
    /* 全站背景 */
    .stApp {{
        background-color: {BG_COLOR};
    }}
    
    /* 按鈕樣式 (科技藍漸層) */
    .stButton>button {{
        background: linear-gradient(135deg, {THEME_COLOR} 0%, #1A5276 100%);
        color: white;
        border: None;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }}
    
    /* 輸入框與卡片優化 (懸浮感) */
    div[data-testid="stExpander"] {{
        background-color: {CARD_COLOR};
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #E0E0E0;
    }}
    
    /* 連結顏色 */
    a {{ color: {THEME_COLOR}; }}
    
    /* 標題裝飾 */
    h1, h2, h3 {{
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 600;
        color: #2C3E50;
    }}
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

# --- 寄信函數 ---
def send_notification_email(booking_data):
    if "email" not in st.secrets:
        st.error("❌ 系統找不到 Email 設定！")
        return

    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    receiver_email = st.secrets["email"]["receiver"]

    subject = f"【會議預約通知】{booking_data['大名']} 申請了會議"
    
    body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h3 style="color: {THEME_COLOR};">收到新的會議室預約申請</h3>
        <p>請管理員登入系統進行審核。</p>
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid {THEME_COLOR};">
            <ul style="list-style-type: none; padding: 0;">
                <li style="margin-bottom: 8px;"><b>👤 預約人：</b> {booking_data['大名']}</li>
                <li style="margin-bottom: 8px;"><b>📅 日期：</b> {booking_data['日期']}</li>
                <li style="margin-bottom: 8px;"><b>⏰ 時間：</b> {booking_data['開始時間']} ~ {booking_data['結束時間']}</li>
                <li style="margin-bottom: 8px;"><b>📍 地點：</b> {booking_data['會議地點']}</li>
                <li style="margin-bottom: 8px;"><b>📝 內容：</b> {booking_data['預約內容']}</li>
                <li style="margin-bottom: 8px;"><b>👥 與會人：</b> {booking_data['與會人']}</li>
            </ul>
        </div>
        <br>
        <a href="https://share.streamlit.io" style="background-color: {THEME_COLOR}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">前往審核</a>
    </div>
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        st.toast("📧 通知信已發送！", icon="✅")
    except Exception as e:
        st.error(f"❌ Email 發送失敗: {e}")

@st.cache_data(ttl=5)
def load_data():
    ws = get_worksheet()
    if ws:
        try:
            df = get_as_dataframe(ws, usecols=list(range(9)), parse_dates=False, dtype=str)
            df = df.dropna(how='all')
            df = df.fillna("")
            df = df[df['日期'].str.len() > 0]
            if '狀態' not in df.columns: df['狀態'] = '核准'
            if '會議地點' not in df.columns: df['會議地點'] = ''
            if '與會人' not in df.columns: df['與會人'] = ''
            return df
        except: pass
    return pd.DataFrame(columns=["日期", "開始時間", "結束時間", "大名", "與會人", "會議地點", "預約內容", "登記時間", "狀態"])

def save_data(df):
    ws = get_worksheet()
    if ws:
        try:
            cols = ["日期", "開始時間", "結束時間", "大名", "與會人", "會議地點", "預約內容", "登記時間", "狀態"]
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

# --- 彈跳視窗 ---
@st.dialog("🎉 申請成功！")
def show_success_message():
    st.subheader("感謝您的預約")
    st.write("已通知主管進行審核。")
    try:
        img = Image.open("thank_you.jpg")
        st.image(img, use_container_width=True)
    except: pass
    if st.button("好的，我知道了", type="primary"):
        st.rerun()

@st.dialog("📋 會議詳細資訊")
def show_event_details(event_props):
    st.markdown(f"### **{event_props.get('content', '無內容')}**")
    st.write("---")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("📍 地點")
        st.info(event_props.get('location', '未指定'))
        st.caption("👥 與會人")
        st.text(event_props.get('attendees') if event_props.get('attendees') else "（無）")
    with c2:
        st.caption("👤 預約人")
        st.info(event_props.get('name', '未知'))
        st.caption("⏰ 時間")
        st.warning(event_props.get('pretty_time', ''))
    
    if event_props.get('status'):
        st.caption("📌 狀態")
        st.write(event_props.get('status'))

# --- 主程式 ---
st.sidebar.header("🔒 管理員專區")

# 使用 session_state 來管理密碼輸入框的狀態，方便做登出功能
if "admin_pass_input" not in st.session_state:
    st.session_state["admin_pass_input"] = ""

def logout():
    st.session_state["admin_pass_input"] = "" # 清空密碼
    
# 密碼輸入框
admin_pwd = st.sidebar.text_input("輸入密碼", type="password", key="admin_pass_input")
is_admin = admin_pwd == ADMIN_PASSWORD

# --- 1. 管理員介面 ---
if is_admin:
    st.sidebar.success("✅ 管理員已登入")
    # 新增：登出按鈕
    if st.sidebar.button("🚪 登出 / 回首頁"):
        logout()
        st.rerun()

    st.markdown(f"<h3 style='color:{THEME_COLOR}'>📋 審核後台</h3>", unsafe_allow_html=True)
    load_data.clear()
    df = load_data()
    if not df.empty:
        edited_df = st.data_editor(df, column_config={
            "狀態": st.column_config.SelectboxColumn("狀態", options=["待審核", "核准", "拒絕"], required=True),
            "會議地點": st.column_config.TextColumn(disabled=True),
            "與會人": st.column_config.TextColumn("與會人"),
            "刪除": st.column_config.CheckboxColumn(required=True)
        }, num_rows="dynamic", key="admin", use_container_width=True)
        if st.button("💾 儲存變更", type="primary", use_container_width=True):
            save_data(edited_df)
            st.success("已更新")
            st.rerun()

# --- 2. 申請介面 (非管理員顯示) ---
else:
    with st.expander("➕ 申請預約 (需審核)", expanded=True):
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("預約人大名 (必填)")
            attendees = c2.text_input("與會人 (選填)")
            c3, c4 = st.columns(2)
            date_val = c3.date_input("日期", min_value=datetime.today())
            loc = c4.selectbox("地點", LOCATION_OPTIONS)
            c5, c6 = st.columns(2)
            s_time = c5.selectbox("開始", TIME_OPTIONS, index=0)
            # 預設結束時間往後推一點，避免與開始時間相同
            e_time = c6.selectbox("結束", TIME_OPTIONS, index=2)
            content = st.text_input("內容 (必填)")
            
            if st.form_submit_button("送出", use_container_width=True):
                load_data.clear()
                df = load_data()
                if not name or not content: st.error("❌ 請填寫必填欄位")
                elif s_time >= e_time: st.error("❌ 時間錯誤：結束時間必須晚於開始時間")
                else:
                    conflict = check_overlap(df, date_val, s_time, e_time)
                    if conflict: st.error(f"❌ 衝突：該時段已被「{conflict}」預約")
                    else:
                        new_row = {
                            "日期": date_val.strftime("%Y-%m-%d"),
                            "開始時間": s_time.strftime("%H:%M:%S"),
                            "結束時間": e_time.strftime("%H:%M:%S"),
                            "大名": name,
                            "與會人": attendees,
                            "會議地點": loc,
                            "預約內容": content,
                            "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "狀態": "待審核"
                        }
                        save_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        send_notification_email(new_row)
                        show_success_message()

st.markdown(f"<hr style='border-top: 2px solid {THEME_COLOR};'>", unsafe_allow_html=True)

# --- 行事曆 ---
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
            bg_color = THEME_COLOR # 預設科技藍
            if status == '待審核': bg_color = "#F39C12"
            elif status == '拒絕': bg_color = "#7F8C8D"

            title_text = f"[{loc}] {row['大名']}"
            if is_admin: title_text = f"({status}) {title_text}"

            events.append({
                "title": title_text,
                "start": f"{clean_date}T{start_t}",
                "end": f"{clean_date}T{end_t}",
                "backgroundColor": bg_color,
                "borderColor": bg_color,
                "textColor": "#FFFFFF",
                "extendedProps": {
                    "location": loc, "name": row['大名'], "attendees": row.get('與會人', ''),
                    "content": row['預約內容'], "status": status, "pretty_time": f"{start_t[:5]} - {end_t[:5]}"
                }
            })
        except: continue

calendar_options = {
    "initialView": "listWeek" if view_mode == "📱 列表" else "timeGridWeek",
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
    "height": "auto", 
    "slotMinTime": "08:00:00", 
    "slotMaxTime": "19:00:00", 
    "allDaySlot": False,
    # 🔥 關鍵修正：加入這行讓週次切換不亂跳
    "datesSet": None 
}

# 🔥 關鍵修正：加入 key="calendar" 確保元件穩定，不會一直重置
calendar_state = calendar(events=events, options=calendar_options, key="calendar")

if calendar_state.get("eventClick"):
    show_event_details(calendar_state["eventClick"]["event"]["extendedProps"])

if is_admin: st.caption(f"🟦 核准 | 🟧 待審核 | ⬜ 拒絕")
