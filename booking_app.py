import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from streamlit_calendar import calendar
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from PIL import Image
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os
import time as time_module

# --- ⚠️ 你的網址 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"
ADMIN_PASSWORD = "8888"

# --- 選項設定 ---
LOCATION_OPTIONS = [
    "小會議室", "大會議室", "洽談室Ａ", "洽談室Ｂ", "行銷部辦公室", 
    "崇德門市", "生產中心", "物流中心", "線上", "外部"
]

LOCATION_SLOGANS = {
    "小會議室": "💡 空間小，點子大！適合腦力激盪。",
    "大會議室": "🎤 麥克風測試... 這裡是決策的殿堂！",
    "洽談室Ａ": "🤝 談生意、聊合作，這裡氣場最合。",
    "洽談室Ｂ": "☕ 來杯咖啡嗎？輕鬆聊聊的好地方。",
    "行銷部辦公室": "🚀 創意發射基地！",
    "崇德門市": "🏪 前線支援！聽聽顧客的聲音。",
    "生產中心": "🛠️ 這裡產出的不只是產品，還有職人精神。",
    "物流中心": "📦 使命必達！效率針對是我們的名字。",
    "線上": "🌐 距離不是問題，網路把我們連在一起。",
    "外部": "🌍 世界那麼大，去外面看看吧！"
}

# --- 🎨 UI 設定：商務高級感 (Business Premium Light Mode) ---
THEME_COLOR = "#1D4ED8"  # 專業藍 (Corporate Blue - 主色/高亮)
ACCENT_COLOR = "#1E293B" # 深灰黑 (Slate 800 - 文字與重點標示)
BG_COLOR = "#F8FAFC"     # 淺灰白 (Slate 50 - 舒適背景)
CARD_COLOR = "#FFFFFF"   # 純白 (白底卡片，創造層次)

TIME_OPTIONS = []
for h in range(8, 18): 
    for m in [0, 30]:
        if h == 17 and m > 0: break
        TIME_OPTIONS.append(time(h, m))

# --- 頁面設定 ---
st.set_page_config(page_title="David 預約系統", page_icon="💼", layout="wide", initial_sidebar_state="collapsed")

# --- 😂 每日笑話資料庫 ---
JOKES_DB = [
    "積德行善的相反是什麼？柯南行兇 (基德行善)",
    "木魚掉到水裡變什麼?濕木魚 (虱目魚)",
    "為什麼科學園區裡面常常跌倒？因為那裡很多絆倒體(半導體)",
    "白氣球揍了黑氣球一拳，黑氣球很痛很生氣於是決定告白氣球。",
    "翁山蘇姬的哥哥叫什麼？蘇姬大哥",
    "為什麼南部沒有廟宇？因為南無阿彌陀佛"
]

# --- 樣式與 Logo ---
logo_file = None
for ext in ["png", "jpg", "jpeg"]:
    if os.path.exists(f"logo.{ext}"):
        logo_file = f"logo.{ext}"
        break
    elif os.path.exists(f"logo_大頭貼.{ext}"):
        logo_file = f"logo_大頭貼.{ext}"
        break

if logo_file:
    try:
        logo = Image.open(logo_file)
        col_logo, col_title = st.columns([1, 5])
        with col_logo: st.image(logo, width=100)
        with col_title: st.markdown(f"<h1 style='color: {THEME_COLOR};'>💼 David 預約系統</h1>", unsafe_allow_html=True)
    except:
        st.markdown(f"<h1 style='color: {THEME_COLOR};'>💼 David 預約系統</h1>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1 style='color: {THEME_COLOR};'>💼 David 預約系統</h1>", unsafe_allow_html=True)

# --- 📸 部門合照 ---
team_photo_file = None
possible_filenames = ["team_photo.jpg", "team_photo.png", "team_photo.jpeg", "Gemini_Generated_Image_1ammmg1ammmg1amm.jpg"]
for filename in possible_filenames:
    if os.path.exists(filename):
        team_photo_file = filename
        break

if team_photo_file:
    try:
        team_photo = Image.open(team_photo_file) 
        st.image(team_photo, use_container_width=True, caption="SYSTEM ONLINE 🟢")
    except: pass

# --- 連線函數 ---
def get_gc():
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            creds = st.secrets["connections"]["gsheets"]["service_account"]
        else:
            creds = st.secrets["service_account"]
        return gspread.service_account_from_dict(creds)
    except: return None

def get_worksheet():
    gc = get_gc()
    if gc:
        try:
            sh = gc.open_by_url(SHEET_URL)
            return sh.worksheet("Sheet1")
        except: return None
    return None

# --- 🔥 新增：休假管理函數 ---
def get_leaves_worksheet():
    gc = get_gc()
    if gc:
        try:
            sh = gc.open_by_url(SHEET_URL)
            try:
                ws = sh.worksheet("Leaves")
            except:
                ws = sh.add_worksheet(title="Leaves", rows=50, cols=2)
                ws.update('A1:B1', [['Date', 'Reason']])
            return ws
        except: return None
    return None

@st.cache_data(ttl=5)
def load_leaves_data():
    ws = get_leaves_worksheet()
    if ws:
        try:
            df = get_as_dataframe(ws, usecols=[0, 1], parse_dates=False, dtype=str)
            df = df.dropna(how='all'); df = df.fillna("")
            df = df[df['Date'].str.len() > 0]
            return df
        except: pass
    return pd.DataFrame(columns=["Date", "Reason"])

def save_leaves_data(df):
    ws = get_leaves_worksheet()
    if ws:
        try:
            cols = ["Date", "Reason"]
            df = df[cols]
            ws.clear(); set_with_dataframe(ws, df); load_leaves_data.clear()
        except Exception as e: st.error(f"寫入失敗: {e}")

# --- 🔥 笑話管理函數 ---
def get_jokes_worksheet():
    gc = get_gc()
    if gc:
        try:
            sh = gc.open_by_url(SHEET_URL)
            try:
                ws = sh.worksheet("Jokes")
            except:
                ws = sh.add_worksheet(title="Jokes", rows=100, cols=1)
                ws.update('A1', [['Joke Content']])
            return ws
        except: return None
    return None

@st.cache_data(ttl=600)
def fetch_custom_jokes_from_sheet():
    custom_jokes = []
    try:
        ws = get_jokes_worksheet()
        if ws:
            vals = ws.col_values(1)
            if len(vals) > 1: custom_jokes = vals[1:]
    except: pass
    return custom_jokes

def get_all_jokes():
    all_jokes = JOKES_DB.copy()
    custom_jokes = fetch_custom_jokes_from_sheet()
    if custom_jokes: all_jokes.extend(custom_jokes)
    return all_jokes

def add_new_joke(joke_text):
    ws = get_jokes_worksheet()
    if ws:
        try:
            ws.append_row([joke_text])
            fetch_custom_jokes_from_sheet.clear()
            return True
        except: return False
    return False

def get_daily_joke():
    full_db = get_all_jokes()
    if not full_db: return "今天沒有笑話..."
    tw_now = datetime.utcnow() + timedelta(hours=8)
    seed_val = tw_now.strftime("%Y%m%d")
    rng = random.Random(seed_val)
    return rng.choice(full_db)

# --- 😂 每日一笑 (商務質感框) ---
st.markdown(f"""
    <div style="
        background-color: {CARD_COLOR}; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 4px solid {THEME_COLOR}; 
        color: {ACCENT_COLOR};
        margin-bottom: 20px;
        text-align: center;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border-top: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
        border-bottom: 1px solid #E2E8F0;">
        ⚡ <b>Daily Log：</b> {get_daily_joke()}
    </div>
""", unsafe_allow_html=True)

# --- 🙋 前台：同仁投稿笑話 ---
with st.expander("💬 提供系統新笑話 (投稿)", expanded=False):
    new_joke_input = st.text_input("輸入內容", placeholder="Enter your joke here...")
    if st.button("📤 Upload", use_container_width=True):
        if new_joke_input:
            if add_new_joke(new_joke_input):
                st.success("✅ 資料已同步至資料庫。")
            else:
                st.error("❌ 連線異常，請稍後再試。")
        else:
            st.warning("⚠️ 內容不可為空。")

st.markdown("---")

# --- 🎨 CSS 優化 (商務專業風 Light Mode) ---
st.markdown(f"""
    <style>
    /* 全站背景 - 淺灰白 */
    .stApp {{ background-color: {BG_COLOR}; }}
    
    /* 標題與文字 - 深灰黑 */
    h1, h2, h3, p, label, div {{
        color: {ACCENT_COLOR} !important;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }}

    /* 按鈕樣式 - 專業質感藍 */
    .stButton>button {{
        background: linear-gradient(135deg, #1E3A8A, #2563EB);
        color: #FFFFFF !important;
        border: none;
        border-radius: 6px; 
        padding: 10px 24px;
        font-weight: 500;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        transition: all 0.2s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
        background: linear-gradient(135deg, #1E40AF, #1D4ED8);
    }}
    
    /* 卡片區塊 */
    div[data-testid="stExpander"] {{
        background-color: {CARD_COLOR};
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    
    /* 輸入框 */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {{
        border-radius: 6px;
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1;
    }}
    
    /* 游標/聚焦效果 */
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus {{
        border: 1px solid {THEME_COLOR} !important;
        box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.15) !important;
    }}

    /* 行事曆內部字體顏色修復 */
    .fc-event-title, .fc-event-time {{
        color: #FFFFFF !important;
        font-weight: 500;
    }}

    a {{ color: {THEME_COLOR}; text-decoration: none; border-bottom: 1px dotted {THEME_COLOR}; }}
    
    img {{ border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); opacity: 0.95; }}
    </style>
""", unsafe_allow_html=True)

def fix_time(t_str):
    if not t_str: return None
    t_str = str(t_str).strip()
    if t_str.count(":") == 1: t_str += ":00"
    try: return datetime.strptime(t_str, "%H:%M:%S").strftime("%H:%M:%S")
    except: return None

# --- 寄信函數 ---
def send_notification_email(booking_data):
    if "email" not in st.secrets: return
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    receiver_email = st.secrets["email"]["receiver"]
    subject = f"[SYSTEM] 預約申請：{booking_data['大名']}"
    
    body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; color: #1E293B; background-color: #F8FAFC;">
        <h3 style="color: {THEME_COLOR};">🔵 新的預約申請 (New Request)</h3>
        <p>系統已記錄新的預約，請管理員登入系統進行審核。</p>
        <div style="background-color: #FFFFFF; padding: 20px; border-radius: 6px; border-left: 4px solid {THEME_COLOR}; border: 1px solid #E2E8F0; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
            <ul style="list-style-type: none; padding: 0;">
                <li style="margin-bottom: 10px;"><b>👤 預約人：</b> {booking_data['大名']}</li>
                <li style="margin-bottom: 10px;"><b>📅 日期：</b> {booking_data['日期']}</li>
                <li style="margin-bottom: 10px;"><b>⏰ 時間：</b> {booking_data['開始時間']} ~ {booking_data['結束時間']}</li>
                <li style="margin-bottom: 10px;"><b>📍 地點：</b> {booking_data['會議地點']}</li>
                <li style="margin-bottom: 10px;"><b>📝 內容：</b> {booking_data['預約內容']}</li>
                <li style="margin-bottom: 10px; color: {THEME_COLOR};"><b>👥 與會人：</b> {booking_data['與會人']}</li>
            </ul>
        </div>
        <br>
        <center>
            <a href="https://share.streamlit.io" style="background-color: #2563EB; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold; font-family: sans-serif;">登入審核</a>
        </center>
    </div>
    """
    msg = MIMEMultipart()
    msg['From'] = sender_email; msg['To'] = receiver_email; msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        st.toast("📧 通知信已發送！", icon="✅")
    except: pass

def send_deletion_email(booking_data):
    if "email" not in st.secrets: return
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    receiver_email = st.secrets["email"]["receiver"]
    subject = f"[SYSTEM] 預約取消：{booking_data['大名']}"
    
    body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; color: #1E293B; background-color: #F8FAFC;">
        <h3 style="color: #DC2626;">🔴 預約已取消 (Request Canceled)</h3>
        <p>同仁已在前台自行取消以下預約，請知悉。</p>
        <div style="background-color: #FFFFFF; padding: 20px; border-radius: 6px; border-left: 4px solid #DC2626; border: 1px solid #E2E8F0; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
            <ul style="list-style-type: none; padding: 0;">
                <li style="margin-bottom: 10px;"><b>👤 取消人：</b> {booking_data['大名']}</li>
                <li style="margin-bottom: 10px;"><b>📅 原定日期：</b> {booking_data['日期']}</li>
                <li style="margin-bottom: 10px;"><b>⏰ 原定時間：</b> {booking_data['開始時間']} ~ {booking_data['結束時間']}</li>
                <li style="margin-bottom: 10px;"><b>📍 地點：</b> {booking_data['會議地點']}</li>
                <li style="margin-bottom: 10px;"><b>📝 內容：</b> {booking_data['預約內容']}</li>
            </ul>
        </div>
    </div>
    """
    msg = MIMEMultipart()
    msg['From'] = sender_email; msg['To'] = receiver_email; msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        st.toast("📧 取消通知已發送！", icon="✅")
    except: pass

@st.cache_data(ttl=5)
def load_data():
    ws = get_worksheet()
    if ws:
        try:
            df = get_as_dataframe(ws, usecols=list(range(9)), parse_dates=False, dtype=str)
            df = df.dropna(how='all'); df = df.fillna("")
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
            ws.clear(); set_with_dataframe(ws, df); load_data.clear()
        except Exception as e: st.error(f"寫入失敗: {e}")

def check_overlap(df, check_date, start_t, end_t):
    if df.empty or '日期' not in df.columns: return None
    check_date_str = check_date.strftime("%Y-%m-%d")
    df['temp_date'] = df['日期'].astype(str).str.replace('/', '-').str.strip()
    day_bookings = df[(df['temp_date'] == check_date_str) & (df['狀態'] != '拒絕')]
    if day_bookings.empty: return None
    start_str = start_t.strftime("%H:%M:%S"); end_str = end_t.strftime("%H:%M:%S")
    overlap = day_bookings[(day_bookings['開始時間'] < end_str) & (day_bookings['結束時間'] > start_str)]
    if not overlap.empty: return overlap.iloc[0]['大名']
    return None

# --- 彈跳視窗 ---
@st.dialog("✅ 申請成功！")
def show_success_message():
    st.subheader("Data Submitted. 🚀")
    st.write("已通知主管進行審核。")
    if st.button("確認 (OK)", type="primary"): st.rerun()

@st.dialog("📋 預約資訊 (Details)")
def show_event_details(event_props):
    st.markdown(f"<h3 style='color: {THEME_COLOR};'><b>{event_props.get('content', '無內容')}</b></h3>", unsafe_allow_html=True)
    st.write("---")
    
    # 若為系統休假，顯示不同樣式
    if event_props.get('status') == "不可預約":
        st.warning("⚠️ 此日期已鎖定，暫不開放預約。")
        st.caption("📍 地點")
        st.info("全天")
        st.caption("👤 設定人")
        st.info("System Admin")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("📍 地點 (Location)")
            st.info(event_props.get('location', '未指定'))
            st.caption("👥 與會人 (Attendees)")
            st.text(event_props.get('attendees') if event_props.get('attendees') else "（無）")
        with c2:
            st.caption("👤 預約人 (Applicant)")
            st.info(event_props.get('name', '未知'))
            st.caption("⏰ 時間 (Time)")
            st.warning(event_props.get('pretty_time', ''))
        if event_props.get('status'):
            st.caption("📌 狀態 (Status)")
            st.write(event_props.get('status'))
        
        st.write("---")
        st.caption("⚙️ 管理區 (Action)")
        if st.button("🗑️ 取消此筆預約 (Delete)", type="primary", use_container_width=True, help="請確認這是您的預約再刪除"):
            current_df = load_data()
            if not current_df.empty:
                mask = (
                    (current_df['日期'] == event_props.get('raw_date')) & 
                    (current_df['開始時間'] == event_props.get('raw_start')) & 
                    (current_df['結束時間'] == event_props.get('raw_end')) & 
                    (current_df['會議地點'] == event_props.get('location'))
                )
                if not current_df[mask].empty:
                    row_to_delete = current_df[mask].iloc[0]
                    new_df = current_df[~mask]
                    save_data(new_df)
                    with st.spinner("正在取消並發送通知..."):
                        send_deletion_email(row_to_delete)
                    st.success("預約已成功取消。")
                    st.rerun()
                else:
                    st.error("❌ 找不到此預約，可能已被移除。")

# --- 主程式 ---
st.sidebar.header("🔒 管理員專區 (Admin)")
if "admin_pass_input" not in st.session_state: st.session_state["admin_pass_input"] = ""
def logout(): st.session_state["admin_pass_input"] = ""
admin_pwd = st.sidebar.text_input("輸入金鑰 (Password)", type="password", key="admin_pass_input")
is_admin = admin_pwd == ADMIN_PASSWORD

if is_admin:
    st.sidebar.success("✅ Auth Granted.")
    if st.sidebar.button("🚪 登出 (Logout)"): logout(); st.rerun()
    
    st.markdown(f"<h3 style='color:{THEME_COLOR}'>⚙️ 系統後台管理中心</h3>", unsafe_allow_html=True)
    
    # 🔥 管理員新增休假/不可預約日期 區塊
    with st.expander("📅 設定鎖定日期 (Leave/Blocked Dates)", expanded=False):
        st.write("設定後，前台日曆會顯示全天不可預約。")
        c_date, c_reason, c_btn = st.columns([2, 2, 1])
        new_leave_date = c_date.date_input("選擇日期", min_value=datetime.today())
        new_leave_reason = c_reason.text_input("事由 (例: 出差)", placeholder="必填")
        
        if c_btn.button("➕ 新增", use_container_width=True):
            if new_leave_reason:
                l_df = load_leaves_data()
                new_row = {"Date": new_leave_date.strftime("%Y-%m-%d"), "Reason": new_leave_reason}
                if l_df.empty:
                    l_df = pd.DataFrame([new_row])
                else:
                    if "刪除" in l_df.columns: l_df = l_df.drop(columns=["刪除"])
                    l_df = pd.concat([l_df, pd.DataFrame([new_row])], ignore_index=True)
                save_leaves_data(l_df)
                st.success("已新增系統鎖定日！")
                st.rerun()
            else:
                st.warning("請填寫事由")
                
        st.markdown("---")
        st.write("🛠️ **已鎖定日期列表**")
        l_df = load_leaves_data()
        if not l_df.empty:
            l_df["刪除"] = False
            edited_leaves = st.data_editor(
                l_df,
                column_config={
                    "Date": st.column_config.TextColumn("日期 (YYYY-MM-DD)", disabled=True),
                    "Reason": st.column_config.TextColumn("事由"),
                    "刪除": st.column_config.CheckboxColumn("🗑️ 刪除")
                },
                num_rows="dynamic", key="admin_leaves", use_container_width=True
            )
            if st.button("💾 儲存變更 (Save)", type="primary", use_container_width=True):
                final_leaves = edited_leaves[edited_leaves["刪除"] == False].drop(columns=["刪除"])
                save_leaves_data(final_leaves)
                st.success("設定已更新。")
                st.rerun()
        else:
            st.info("No blocked dates.")

    st.write("---")

    load_data.clear(); df = load_data()
    if not df.empty:
        df["刪除"] = False
        edited_df = st.data_editor(
            df, 
            column_config={
                "狀態": st.column_config.SelectboxColumn("狀態", options=["待審核", "核准", "拒絕"], required=True),
                "會議地點": st.column_config.TextColumn(disabled=True),
                "與會人": st.column_config.TextColumn("與會人"),
                "刪除": st.column_config.CheckboxColumn(label="🗑️ 刪除", help="勾選並儲存以刪除資料")
            },
            num_rows="dynamic", key="admin_bookings", use_container_width=True
        )
        if st.button("💾 儲存資料表 (Save Database)", type="primary", use_container_width=True):
            final_df = edited_df[edited_df["刪除"] == False]
            final_df = final_df.drop(columns=["刪除"])
            save_data(final_df)
            st.success("資料庫已同步。")
            st.rerun()
else:
    with st.expander("📝 建立新預約 (Create Booking)", expanded=True):
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("預約人 (Applicant)", placeholder="必填")
            attendees = c2.text_input("與會人 (Attendees)", placeholder="選填")
            c3, c4 = st.columns(2)
            date_val = c3.date_input("日期 (Date)", min_value=datetime.today())
            loc = c4.selectbox("地點 (Location)", LOCATION_OPTIONS)
            
            if loc in LOCATION_SLOGANS:
                st.caption(f"_{LOCATION_SLOGANS[loc]}_")
            
            c5, c6 = st.columns(2)
            s_time = c5.selectbox("開始 (Start)", TIME_OPTIONS, index=0)
            e_time = c6.selectbox("結束 (End)", TIME_OPTIONS, index=2)
            content = st.text_input("會議內容 (Subject)", placeholder="必填")
            if st.form_submit_button("送出申請 (Submit)", use_container_width=True):
                # 載入所有資料
                load_data.clear(); df = load_data()
                leaves_df = load_leaves_data()
                
                # 檢查是否為休假日
                date_str = date_val.strftime("%Y-%m-%d")
                is_leave = False
                leave_reason = ""
                if not leaves_df.empty and date_str in leaves_df['Date'].values:
                    is_leave = True
                    leave_reason = leaves_df[leaves_df['Date'] == date_str].iloc[0]['Reason']

                if not name or not content: 
                    st.error("❌ 請填寫必填欄位 (Required fields missing)")
                elif is_leave:
                    st.error(f"❌ 無法預約：該日期已設定為「{leave_reason}」")
                elif s_time >= e_time: 
                    st.error("❌ 時間設定錯誤 (Invalid Time Range)")
                else:
                    conflict = check_overlap(df, date_val, s_time, e_time)
                    if conflict: st.error(f"❌ 衝突：該時段已被「{conflict}」佔用")
                    else:
                        new_row = {"日期": date_val.strftime("%Y-%m-%d"), "開始時間": s_time.strftime("%H:%M:%S"), "結束時間": e_time.strftime("%H:%M:%S"), "大名": name, "與會人": attendees, "會議地點": loc, "預約內容": content, "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "狀態": "待審核"}
                        save_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        send_notification_email(new_row); show_success_message()

st.markdown(f"<hr style='border-top: 1px solid #CBD5E1;'>", unsafe_allow_html=True)

# --- 行事曆 ---
df = load_data()
leaves_df = load_leaves_data()
current_view = "timeGridWeek"

events = []
if "calendar_date" not in st.session_state:
    st.session_state["calendar_date"] = datetime.today().isoformat()

# 1. 載入一般預約
if not df.empty and '日期' in df.columns:
    for _, row in df.iterrows():
        try:
            status = row.get('狀態', '核准')
            if not is_admin and status != '核准': continue
            clean_date = str(row['日期']).replace('/', '-').strip()
            start_t = fix_time(row['開始時間']); end_t = fix_time(row['結束時間'])
            if not start_t or not end_t: continue
            
            loc = row.get('會議地點', '未指定')
            content = row.get('預約內容', '無內容')
            
            # 🔥 修改 1：讓行事曆方塊直接顯示 會議內容
            title_text = f"[{loc}] {row['大名']}｜{content}"
            if is_admin: title_text = f"({status}) {title_text}"

            bg_color = "#2563EB" # Professional Blue
            if status == '待審核': bg_color = "#F59E0B" # Amber Pending
            elif status == '拒絕': bg_color = "#94A3B8" # Slate Rejected
            
            events.append({
                "title": title_text, "start": f"{clean_date}T{start_t}", "end": f"{clean_date}T{end_t}",
                "backgroundColor": bg_color, "borderColor": bg_color, "textColor": "#FFFFFF",
                "extendedProps": {
                    "location": loc, 
                    "name": row['大名'], 
                    "attendees": row.get('與會人', ''), 
                    "content": content, 
                    "status": status, 
                    "pretty_time": f"{start_t[:5]} - {end_t[:5]}",
                    "raw_date": row['日期'],
                    "raw_start": row['開始時間'],
                    "raw_end": row['結束時間']
                }
            })
        except: continue

# 2. 載入休假/停用日期 (全天事件)
if not leaves_df.empty:
    for _, row in leaves_df.iterrows():
        try:
            clean_date = str(row['Date']).replace('/', '-').strip()
            events.append({
                "title": f"🚫 系統鎖定: {row['Reason']}",
                "start": clean_date, 
                "allDay": True,
                "backgroundColor": "#F1F5F9", # Light Gray
                "borderColor": "#CBD5E1",
                "textColor": "#475569",
                "extendedProps": {
                    "content": f"鎖定事由：{row['Reason']}",
                    "status": "不可預約",
                }
            })
        except: continue

calendar_options = {
    "initialView": current_view,
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
    "height": "auto", "slotMinTime": "08:00:00", "slotMaxTime": "19:00:00", "allDaySlot": True,
    "initialDate": st.session_state["calendar_date"],
}

calendar_state = calendar(events=events, options=calendar_options, key=f"calendar_{current_view}", callbacks=["datesSet", "eventClick"])

if calendar_state.get("datesSet"):
    new_start_date = calendar_state["datesSet"]["startStr"]
    if new_start_date.split("T")[0] != st.session_state["calendar_date"].split("T")[0]:
        st.session_state["calendar_date"] = new_start_date
        st.rerun()

if calendar_state.get("eventClick"):
    show_event_details(calendar_state["eventClick"]["event"]["extendedProps"])

if is_admin: st.caption(f"🔵 核准 (Approved) | 🟠 待審核 (Pending) | ⚪ 拒絕 (Rejected) | 🚫 鎖定 (Blocked)")
