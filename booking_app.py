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
    "物流中心": "📦 使命必達！效率就是我們的名字。",
    "線上": "🌐 距離不是問題，網路把我們連在一起。",
    "外部": "🌍 世界那麼大，去外面看看吧！"
}

# --- 心情投票選項 ---
MOOD_OPTIONS = ["😀 超棒", "😐 平靜", "😫 累累"]

# --- 🎨 UI 設定：韓系插畫風配色 ---
THEME_COLOR = "#D4A59A"
ACCENT_COLOR = "#8D6E63"
BG_COLOR = "#FDFBF7"
CARD_COLOR = "#FFFFFF"

TIME_OPTIONS = []
for h in range(8, 18): 
    for m in [0, 30]:
        if h == 17 and m > 0: break
        TIME_OPTIONS.append(time(h, m))

# --- 頁面設定 ---
st.set_page_config(page_title="行銷部會議預約", page_icon="🧸", layout="wide", initial_sidebar_state="collapsed")

# --- 😂 每日笑話資料庫 (更新版) ---
JOKES_DB = [
    "小明對芒果過敏，你知道小明不能吃什麼嗎？    鋼琴",
    "T懷孕會變什麼.........ㄛ？",
    "什麼動物每週二出現？.......美洲鱷",
    "什麼人肚子最印？.........印度人",
    "假日哪裡最多越南人？.......越南",
    "端午節不會找什麼人划龍舟？........客家人，因為划不來"
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
        with col_title: st.title("🧸 行銷部會議預約")
    except:
        st.title("🧸 行銷部會議預約")
else:
    st.title("🧸 行銷部會議預約")

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
        st.image(team_photo, use_container_width=True, caption="Marketing Team ✨")
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

# --- 🔥 笑話管理函數 (加入快取機制) ---
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

# 🔥 關鍵修改：加入 ttl=600 (10分鐘快取)，避免頻繁讀取導致額度超標
@st.cache_data(ttl=600)
def fetch_custom_jokes_from_sheet():
    custom_jokes = []
    try:
        ws = get_jokes_worksheet()
        if ws:
            # 讀取第一欄所有資料
            vals = ws.col_values(1)
            if len(vals) > 1: # 排除標題
                custom_jokes = vals[1:]
    except: pass
    return custom_jokes

def get_all_jokes():
    # 讀取內建笑話
    all_jokes = JOKES_DB.copy()
    # 讀取自訂笑話 (有快取保護)
    custom_jokes = fetch_custom_jokes_from_sheet()
    if custom_jokes:
        all_jokes.extend(custom_jokes)
    return all_jokes

def add_new_joke(joke_text):
    ws = get_jokes_worksheet()
    if ws:
        try:
            ws.append_row([joke_text])
            # 🔥 投稿成功後，清除快取，這樣下次讀取才會看到新的
            fetch_custom_jokes_from_sheet.clear()
            return True
        except: return False
    return False

def get_daily_joke():
    full_db = get_all_jokes()
    if not full_db: return "今天沒有笑話..."
    
    # 🔥 改良：使用「台灣時間」的「日期字串」作為隨機種子
    # 這樣每一天對於所有人來說，選到的笑話都是固定的，而且是隨機挑選，不會受長度影響
    tw_now = datetime.utcnow() + timedelta(hours=8)
    seed_val = tw_now.strftime("%Y%m%d") # 例如: 20231027
    
    # 使用獨立的隨機產生器，不影響全域 random
    rng = random.Random(seed_val)
    return rng.choice(full_db)

# --- 🔥 心情投票函數 ---
def get_mood_worksheet():
    gc = get_gc()
    if gc:
        try:
            sh = gc.open_by_url(SHEET_URL)
            try:
                ws = sh.worksheet("Moods")
            except:
                ws = sh.add_worksheet(title="Moods", rows=10, cols=2)
                ws.update('A1:B1', [['Mood', 'Count']])
                init_data = [[m, 0] for m in MOOD_OPTIONS]
                ws.update('A2:B4', init_data)
            return ws
        except: return None
    return None

def load_mood_data():
    ws = get_mood_worksheet()
    if ws:
        try:
            data = ws.get_all_values()
            mood_dict = {row[0]: int(row[1]) for row in data[1:] if len(row) >= 2 and row[1].isdigit()}
            for m in MOOD_OPTIONS:
                if m not in mood_dict: mood_dict[m] = 0
            return mood_dict
        except: pass
    return {m: 0 for m in MOOD_OPTIONS}

def update_mood_count(mood_to_add):
    ws = get_mood_worksheet()
    if ws:
        try:
            cell = ws.find(mood_to_add)
            if cell:
                current_val = int(ws.cell(cell.row, cell.col + 1).value)
                ws.update_cell(cell.row, cell.col + 1, current_val + 1)
        except: pass

# --- 😂 每日一笑 ---
st.markdown(f"""
    <div style="
        background-color: #FFF3E0; 
        padding: 15px; 
        border-radius: 15px; 
        border: 2px dashed {THEME_COLOR}; 
        color: {ACCENT_COLOR};
        margin-bottom: 20px;
        text-align: center;
        font-family: 'Comic Sans MS', sans-serif;">
        ✨ <b>Daily Smile：</b> {get_daily_joke()} ✨
    </div>
""", unsafe_allow_html=True)

# --- 🙋 前台：同仁投稿笑話 ---
with st.expander("🙋 我也想講笑話！(投稿)", expanded=False):
    new_joke_input = st.text_input("輸入笑話內容", placeholder="範例：為什麼電腦會冷？因為它有 Windows")
    if st.button("➕ 送出笑話", use_container_width=True):
        if new_joke_input:
            if add_new_joke(new_joke_input):
                st.success("笑話已投稿成功！感謝你的幽默感 💖")
                st.balloons()
            else:
                st.error("投稿失敗，請檢查連線")
        else:
            st.warning("請輸入內容")

# --- 🌡️ 心情投票區塊 ---
st.markdown(f"<h3 style='text-align: center; color: {ACCENT_COLOR};'>🌡️ 今天心情如何？</h3>", unsafe_allow_html=True)
mood_counts = load_mood_data()
total_votes = sum(mood_counts.values()) if mood_counts else 0

if "has_voted" not in st.session_state:
    st.session_state["has_voted"] = False

if not st.session_state["has_voted"]:
    c1, c2, c3 = st.columns(3)
    if c1.button("😀 超棒", use_container_width=True):
        update_mood_count("😀 超棒")
        st.session_state["has_voted"] = True
        st.rerun()
    if c2.button("😐 平靜", use_container_width=True):
        update_mood_count("😐 平靜")
        st.session_state["has_voted"] = True
        st.rerun()
    if c3.button("😫 累累", use_container_width=True):
        update_mood_count("😫 累累")
        st.session_state["has_voted"] = True
        st.rerun()
else:
    st.info("✨ 收到你的心情了！來看看大家的狀態：")
    for mood in MOOD_OPTIONS:
        count = mood_counts.get(mood, 0)
        percent = (count / total_votes) if total_votes > 0 else 0
        st.write(f"**{mood}** ({count} 票)")
        st.progress(percent, text=f"{int(percent*100)}%")
    if st.button("🔄 再投一次 (測試用)", type="secondary"):
        st.session_state["has_voted"] = False
        st.rerun()

st.markdown("---")

# --- 🎨 CSS 優化 (韓系 Ins 風) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_COLOR}; }}
    h1, h2, h3, p, label, div {{
        color: {ACCENT_COLOR} !important;
        font-family: 'Helvetica Neue', sans-serif;
    }}
    .stButton>button {{
        background-color: {THEME_COLOR};
        color: white !important;
        border: none;
        border-radius: 20px;
        padding: 10px 24px;
        box-shadow: 2px 2px 0px #BCAaa4;
        transition: all 0.2s;
    }}
    .stButton>button:hover {{
        transform: translateY(2px);
        box-shadow: 0px 0px 0px #BCAaa4;
        background-color: #E6B0AA;
    }}
    div[data-testid="stExpander"] {{
        background-color: {CARD_COLOR};
        border-radius: 15px;
        border: 1px solid #F2E7E6;
        box-shadow: 0 4px 15px rgba(212, 165, 154, 0.15);
    }}
    .stTextInput>div>div>input, .stSelectbox>div>div>div {{
        border-radius: 10px;
        background-color: #FFFDF9;
        border: 1px solid #E0E0E0;
    }}
    a {{ color: {THEME_COLOR}; text-decoration: none; border-bottom: 1px dotted {THEME_COLOR}; }}
    img {{ border-radius: 15px; box-shadow: 5px 5px 0px #F2E7E6; }}
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
    subject = f"【會議預約通知】{booking_data['大名']} 申請了會議"
    
    body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #5D4037; background-color: #FDFBF7;">
        <h3 style="color: {THEME_COLOR};">💌 收到新的會議室預約申請</h3>
        <p>請管理員登入系統進行審核。</p>
        <div style="background-color: #FFFFFF; padding: 20px; border-radius: 15px; border: 2px dashed {THEME_COLOR};">
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
            <a href="https://share.streamlit.io" style="background-color: {THEME_COLOR}; color: white; padding: 12px 25px; text-decoration: none; border-radius: 20px; font-weight: bold; box-shadow: 2px 2px 0px #BCAaa4;">前往審核</a>
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
    subject = f"【會議取消通知】{booking_data['大名']} 取消了會議"
    
    body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #5D4037; background-color: #FDFBF7;">
        <h3 style="color: #E57373;">🗑️ 會議已取消</h3>
        <p>同仁已在前台自行取消以下預約，請知悉。</p>
        <div style="background-color: #FFFFFF; padding: 20px; border-radius: 15px; border: 2px dashed #E57373;">
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
@st.dialog("🎉 申請成功！")
def show_success_message():
    st.subheader("Thank You! 💖")
    st.write("已通知主管進行審核。")
    thank_you_file = None
    for ext in ["jpg", "jpeg", "png"]:
        if os.path.exists(f"thank_you.{ext}"):
            thank_you_file = f"thank_you.{ext}"
            break
    if thank_you_file:
        try:
            img = Image.open(thank_you_file)
            st.image(img, use_container_width=True)
        except: pass
    st.balloons()
    if st.button("好的，我知道了", type="primary"): st.rerun()

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
    
    st.write("---")
    st.caption("⚠️ 操作區")
    if st.button("🗑️ 我要取消這個預約", type="primary", use_container_width=True, help="請確認這是您的預約再刪除"):
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
                st.success("預約已取消！")
                st.rerun()
            else:
                st.error("❌ 找不到此預約，可能已經被刪除了。")

# --- 主程式 ---
st.sidebar.header("🔒 管理員專區")
if "admin_pass_input" not in st.session_state: st.session_state["admin_pass_input"] = ""
def logout(): st.session_state["admin_pass_input"] = ""
admin_pwd = st.sidebar.text_input("輸入密碼", type="password", key="admin_pass_input")
is_admin = admin_pwd == ADMIN_PASSWORD

if is_admin:
    st.sidebar.success("✅ 管理員已登入")
    if st.sidebar.button("🚪 登出 / 回首頁"): logout(); st.rerun()
    
    st.markdown(f"<h3 style='color:{THEME_COLOR}'>📋 審核後台</h3>", unsafe_allow_html=True)
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
            num_rows="dynamic", key="admin", use_container_width=True
        )
        if st.button("💾 儲存變更", type="primary", use_container_width=True):
            final_df = edited_df[edited_df["刪除"] == False]
            final_df = final_df.drop(columns=["刪除"])
            save_data(final_df)
            st.success("已更新")
            st.rerun()
else:
    with st.expander("➕ 申請預約 (需審核)", expanded=True):
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("預約人大名 (必填)")
            attendees = c2.text_input("與會人 (選填)")
            c3, c4 = st.columns(2)
            date_val = c3.date_input("日期", min_value=datetime.today())
            loc = c4.selectbox("地點", LOCATION_OPTIONS)
            
            if loc in LOCATION_SLOGANS:
                st.caption(f"_{LOCATION_SLOGANS[loc]}_")
            
            c5, c6 = st.columns(2)
            s_time = c5.selectbox("開始", TIME_OPTIONS, index=0)
            e_time = c6.selectbox("結束", TIME_OPTIONS, index=2)
            content = st.text_input("內容 (必填)")
            if st.form_submit_button("送出", use_container_width=True):
                load_data.clear(); df = load_data()
                if not name or not content: st.error("❌ 請填寫必填欄位")
                elif s_time >= e_time: st.error("❌ 時間錯誤：結束時間必須晚於開始時間")
                else:
                    conflict = check_overlap(df, date_val, s_time, e_time)
                    if conflict: st.error(f"❌ 衝突：該時段已被「{conflict}」預約")
                    else:
                        new_row = {"日期": date_val.strftime("%Y-%m-%d"), "開始時間": s_time.strftime("%H:%M:%S"), "結束時間": e_time.strftime("%H:%M:%S"), "大名": name, "與會人": attendees, "會議地點": loc, "預約內容": content, "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "狀態": "待審核"}
                        save_data(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        send_notification_email(new_row); show_success_message()

st.markdown(f"<hr style='border-top: 2px dashed {THEME_COLOR};'>", unsafe_allow_html=True)

# --- 行事曆 ---
df = load_data()
current_view = "timeGridWeek"

events = []
if "calendar_date" not in st.session_state:
    st.session_state["calendar_date"] = datetime.today().isoformat()

if not df.empty and '日期' in df.columns:
    for _, row in df.iterrows():
        try:
            status = row.get('狀態', '核准')
            if not is_admin and status != '核准': continue
            clean_date = str(row['日期']).replace('/', '-').strip()
            start_t = fix_time(row['開始時間']); end_t = fix_time(row['結束時間'])
            if not start_t or not end_t: continue
            loc = row.get('會議地點', '未指定'); bg_color = THEME_COLOR
            if status == '待審核': bg_color = "#F39C12"
            elif status == '拒絕': bg_color = "#7F8C8D"
            title_text = f"[{loc}] {row['大名']}"
            if is_admin: title_text = f"({status}) {title_text}"
            
            events.append({
                "title": title_text, "start": f"{clean_date}T{start_t}", "end": f"{clean_date}T{end_t}",
                "backgroundColor": bg_color, "borderColor": bg_color, "textColor": "#FFFFFF",
                "extendedProps": {
                    "location": loc, 
                    "name": row['大名'], 
                    "attendees": row.get('與會人', ''), 
                    "content": row['預約內容'], 
                    "status": status, 
                    "pretty_time": f"{start_t[:5]} - {end_t[:5]}",
                    "raw_date": row['日期'],
                    "raw_start": row['開始時間'],
                    "raw_end": row['結束時間']
                }
            })
        except: continue

calendar_options = {
    "initialView": current_view,
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""},
    "height": "auto", "slotMinTime": "08:00:00", "slotMaxTime": "19:00:00", "allDaySlot": False,
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

if is_admin: st.caption(f"🟦 核准 | 🟧 待審核 | ⬜ 拒絕")
