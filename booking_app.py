import streamlit as st
import pandas as pd
from datetime import datetime, time
from streamlit_calendar import calendar
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from PIL import Image # 引入圖片處理模組

# --- ⚠️ 你的網址 (請確認不用改) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mpVm9tTWO3gmFx32dKqtA5_xcLrbCmGN6wDMC1sSjHs/edit"
ADMIN_PASSWORD = "8888"

# --- 新增：地點選項 ---
LOCATION_OPTIONS = ["小會議室", "大會議室", "洽談室Ａ", "洽談室Ｂ", "行銷部辦公室"]

# --- 新增：主題色設定 (從 Logo 吸取的粉藕色) ---
THEME_COLOR = "#D4A59A"

# --- 設定時間選項 ---
TIME_OPTIONS = []
for h in range(8, 17):
    for m in [0, 30]:
        if h == 16 and m > 30: break
        TIME_OPTIONS.append(time(h, m))

# --- 頁面基礎設定 (設定網頁標題、圖示、佈局) ---
st.set_page_config(
    page_title="行銷部會議預約系統",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 新增：載入並顯示 Logo 與標題 ---
# 嘗試載入 logo.png，如果找不到就不顯示
try:
    logo = Image.open("logo.png")
    # 使用 columns 來排版，讓 Logo 和標題並排
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image(logo, width=100) # 調整寬度以適應你的 Logo
    with col_title:
        st.title("📅 行銷部會議預約系統")
except FileNotFoundError:
    # 如果沒上傳圖片，就只顯示標題
    st.title("📅 行銷部會議預約系統")

# --- 新增：套用主題色的 CSS ---
# 這段 CSS 會把按鈕、連結等元素改成你的主題色
st.markdown(f"""
    <style>
    .stButton>button {{
        background-color: {THEME_COLOR};
        color: white;
        border: None;
    }}
    .stButton>button:hover {{
        background-color: #B88B81; /*稍微深一點的顏色作為懸停效果*/
    }}
    a {{
        color: {THEME_COLOR};
    }}
    .st-emotion-cache-16txtl3 {{ /* 側邊欄標題顏色 */
        color: {THEME_COLOR};
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
    except Exception as e:
        st.error(f"連線失敗: {e}")
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
            # 修改：現在要讀取 8 個欄位 (A~H)
            df = get_as_dataframe(ws, usecols=[0,1,2,3,4,5,6,7], parse_dates=False, dtype=str)
            df = df.dropna(how='all')
            df = df.fillna("")
            df = df[df['日期'].str.len() > 0]
            
            # 確保必要欄位存在
            if '狀態' not in df.columns: df['狀態'] = '核准'
            if '會議地點' not in df.columns: df['會議地點'] = '' # 舊資料地點留空
            
            return df
        except Exception:
            pass
    # 修改：DataFrame 結構增加「會議地點」
    return pd.DataFrame(columns=["日期", "開始時間", "結束時間", "大名", "會議地點", "預約內容", "登記時間", "狀態"])

def save_data(df):
    ws = get_worksheet()
    if ws:
        try:
            # 修改：存檔時保留 8 個欄位
            cols_to_keep = ["日期", "開始時間", "結束時間", "大名", "會議地點", "預約內容", "登記時間", "狀態"]
            df = df[cols_to_keep]
            ws.clear()
            set_with_dataframe(ws, df)
            load_data.clear()
        except Exception as e:
            st.error(f"寫入失敗: {e}")

# --- 檢查衝突 (邏輯不變) ---
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

# --- 側邊欄 ---
st.sidebar.header("🔒 管理員專區")
admin_pwd = st.sidebar.text_input("輸入密碼進入審核", type="password")
is_admin = admin_pwd == ADMIN_PASSWORD

# --- 申請區 (一般人) ---
if not is_admin:
    # 使用 expander 讓表單可以收合，標題加上主題色
    with st.expander("➕ 申請預約會議 (需審核)", expanded=True):
        with st.form("booking_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("預約人大名")
            date_val = c1.date_input("日期", min_value=datetime.today())
            s_time = c2.selectbox("開始時間", TIME_OPTIONS, index=0)
            e_time = c2.selectbox("結束時間", TIME_OPTIONS, index=2)
            
            # 新增：地點下拉選單
            location = st.selectbox("會議地點", LOCATION_OPTIONS)
            
            content = st.text_input("會議內容/目的")
            
            # 送出按鈕會自動套用 CSS 的主題色
            if st.form_submit_button("送出申請", use_container_width=True):
                load_data.clear()
                df = load_data()
                if not name or not content:
                    st.error("❌ 資訊不完整，請填寫大名和內容。")
                elif s_time >= e_time:
                    st.error("❌ 時間錯誤，結束時間必須晚於開始時間。")
                else:
                    conflict = check_overlap(df, date_val, s_time, e_time)
                    if conflict:
                        st.error(f"❌ 無法申請！該時段已被「{conflict}」佔用 (或審核中)。")
                    else:
                        # 修改：寫入新資料時加入地點
                        new_row = {
                            "日期": date_val.strftime("%Y-%m-%d"), 
                            "開始時間": s_time.strftime("%H:%M:%S"), 
                            "結束時間": e_time.strftime("%H:%M:%S"), 
                            "大名": name,
                            "會議地點": location,
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
    st.markdown(f"<h3 style='color:{THEME_COLOR}'>📋 審核管理後台</h3>", unsafe_allow_html=True)
    load_data.clear()
    df = load_data()
    
    if not df.empty:
        # 修改：管理員介面也要顯示地點欄位，但不允許編輯地點 (只審核狀態)
        edited_df = st.data_editor(
            df,
            column_config={
                "狀態": st.column_config.SelectboxColumn("審核狀態", options=["待審核", "核准", "拒絕"], required=True),
                "刪除": st.column_config.CheckboxColumn(required=True),
                "會議地點": st.column_config.TextColumn("會議地點", disabled=True) # 鎖定地點欄位
            },
            num_rows="dynamic",
            key="admin_editor",
            use_container_width=True
        )
        # 按鈕會自動套用主題色
        if st.button("💾 儲存所有變更", type="primary", use_container_width=True):
            save_data(edited_df)
            st.success("已更新！")
            st.rerun()
    else:
        st.info("目前沒有任何預約資料。")

st.markdown(f"<hr style='border-top: 2px solid {THEME_COLOR};'>", unsafe_allow_html=True) # 分隔線也用主題色

# --- 行事曆 ---
df = load_data()
# 使用自定義 CSS 美化 Radio Button (選項切換)
st.markdown(f"""
    <style>
    div[role="radiogroup"] > label > div:first-child {{
        background-color: {THEME_COLOR} !important;
    }}
    </style>
""", unsafe_allow_html=True)
view_mode = st.radio("檢視模式", ["📱 清單列表", "💻 完整週視圖"], horizontal=True)

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
            
            # 取得地點，如果沒有就顯示未指定
            loc = row.get('會議地點', '未指定')

            # 設定顏色：核准=主題色, 待審核=橘, 拒絕=灰
            bg_color = THEME_COLOR # 使用主題色作為預設核准顏色
            if status == '待審核': bg_color = "#F39C12"
            elif status == '拒絕': bg_color = "#7F8C8D"

            # 修改：行事曆標題格式 -> [地點] 大名: 內容
            title_text = f"[{loc}] {row['大名']}: {row['預約內容']}"
            if is_admin: title_text = f"({status}) {title_text}"

            events.append({
                "title": title_text, 
                "start": f"{clean_date}T{start_t}", 
                "end": f"{clean_date}T{end_t}", 
                "backgroundColor": bg_color,
                "borderColor": bg_color,
                "textColor": "#FFFFFF" # 文字用白色比較清楚
            })
        except:
            continue
        
calendar(events=events, options={
    "initialView": "listWeek" if view_mode == "📱 清單列表" else "timeGridWeek", 
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": ""}, 
    "height": "auto",
    "slotMinTime": "08:00:00",
    "slotMaxTime": "19:00:00", # 延長到晚上7點
    "allDaySlot": False # 隱藏全天行程欄位，讓畫面更清爽
})

if is_admin:
    st.caption(f"🟦 核准 ({THEME_COLOR}) | 🟧 待審核 | ⬜ 拒絕")