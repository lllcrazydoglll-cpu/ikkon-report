import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# 核心：極致穩定版的認證函數
def get_gspread_client():
    try:
        # 1. 取得 Secrets 字典
        s = st.secrets["gcp_service_account"]
        
        # 2. 構建 Google 需要的認證內容
        # 這裡用 info 重新組裝，避免 TOML 格式讀取時產生的任何隱形問題
        info = {
            "type": s["type"],
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": s["private_key"].replace("\\n", "\n").strip(), # 強制清洗字串並去空格
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "auth_uri": s["auth_uri"],
            "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"鑰匙格式不正確，請檢查 Secrets。細節：{e}")
        return None

# 介面設定
st.set_page_config(page_title="IKKON 日報表系統", page_icon="📝")
st.title("IKKON 日報表系統")

# 側邊欄或上方顯示目前狀態
st.info("系統狀態：準備就緒")

# --- 輸入表單 ---
date = st.date_input("報表日期", datetime.date.today())
department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中和牛會所"])

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("💰 營收數據")
    cash = st.number_input("現金收入", min_value=0, step=100)
    credit_card = st.number_input("刷卡收入", min_value=0, step=100)
    remittance = st.number_input("匯款收入", min_value=0, step=100)
with col2:
    st.subheader("👥 營運數據")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

# 計算區
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
productivity = total_revenue / total_hours if total_hours > 0 else 0
avg_spend = total_revenue / total_customers if total_customers > 0 else 0

st.metric("當日總營收", f"{total_revenue:,} 元")

st.divider()

st.subheader("✍️ 營運記事")
ops_note = st.text_area("營運回報、事務宣達", placeholder="請輸入今日店內狀況...")
complaint_note = st.text_area("客訴處理", placeholder="若無則留空")

# --- 提交邏輯 ---
if st.button("確認提交日報表", type="primary", use_container_width=True):
    if total_revenue <= 0:
        st.warning("請輸入正確的營收金額再提交。")
    else:
        with st.spinner('正在連線 Google Sheets...'):
            client = get_gspread_client()
            if client:
                try:
                    # 使用 Secrets 裡的 ID 開啟試算表
                    sheet = client.open_by_key(st.secrets["spreadsheet"]["id"]).sheet1
                    
                    # 整理資料列
                    new_row = [
                        str(date), department, cash, credit_card, remittance, "", 
                        total_revenue, total_customers, round(avg_spend, 2), 
                        kitchen_hours, floor_hours, total_hours, round(productivity, 2), 
                        ops_note, complaint_note
                    ]
                    
                    sheet.append_row(new_row)
                    st.success("✅ 資料已成功存入雲端試算表！")
                    st.balloons()
                except Exception as e:
                    st.error(f"雲端寫入失敗：{e}")
