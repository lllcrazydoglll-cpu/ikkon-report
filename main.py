import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

# 頁面配置
st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

# Google Sheets 認證
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"雲端連線失敗：{e}")
        return None

# --- 檔案 ID 配置 (已更換為您提供的網址 ID) ---
KEYS = {
    "REPORT": "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08",  # IKKON_Daily_Report 
    "USERS": "1o42MwMubvNuaAtNzmtHXix_O2-3BC1CR5fGRBlp26tQ",   # Users 
    "SETTINGS": "1b0Gn4b_7lYJSDcAMO8kUNFDjhy4g34xijzLudrayPWQ" # Settings 
}

# 載入雲端配置
def load_configs(client):
    try:
        # 讀取 Users 檔案的第一個工作表 
        user_df = pd.DataFrame(client.open_by_key(KEYS["USERS"]).sheet1.get_all_records())
        # 讀取 Settings 檔案的第一個工作表 
        settings_df = pd.DataFrame(client.open_by_key(KEYS["SETTINGS"]).sheet1.get_all_records())
        return user_df, settings_df
    except Exception as e:
        st.error(f"讀取設定檔失敗，請確認 GCP 帳號是否有權限存取新資料夾。錯誤：{e}")
        return pd.DataFrame(), pd.DataFrame()

# 登入介面
def login_ui(user_df):
    if st.session_state.get("logged_in"):
        return True

    st.title("IKKON 系統登入")
    with st.form("login_form"):
        input_user = st.text_input("帳號名稱")
        input_pwd = st.text_input("密碼", type="password")
        submit = st.form_submit_button("登入")
        
        if submit:
            if not user_df.empty:
                user_df['密碼'] = user_df['密碼'].astype(str)
                # 根據 Users 內容比對 
                match = user_df[(user_df['帳號名稱'] == input_user) & (user_df['密碼'] == input_pwd)]
                if not match.empty:
                    user_info = match.iloc[0]
                    st.session_state.update({
                        "logged_in": True, 
                        "user_role": user_info['權限等級'], 
                        "user_name": user_info['帳號名稱'],
                        "dept_access": user_info['負責部門']
                    })
                    st.rerun()
            st.error("帳號或密碼錯誤")
    return False

# --- 主程式 ---
client = get_gspread_client()

if client:
    user_df, settings_df = load_configs(client)
    
    if login_ui(user_df):
        # 初始化營運參數 
        if not settings_df.empty:
            TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
            HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))
        else:
            st.error("無法載入營運參數。")
            st.stop()

        with st.sidebar:
            st.title(f"您好, {st.session_state['user_name']}")
            mode = st.radio("功能選單", ["數據錄入", "月度損益彙總", "後台參數設定"])
            if st.button("登出"):
                st.session_state.clear()
                st.rerun()

        # 1. 數據錄入
        if mode == "數據錄入":
            st.title("IKKON 營運數據錄入")
            dept_options = list(TARGETS.keys()) if st.session_state['dept_access'] == "ALL" else [st.session_state['dept_access']]
            department = st.selectbox("所屬部門", dept_options)
            # ... (其餘錄入邏輯保持不變，提交時使用 KEYS["REPORT"])
