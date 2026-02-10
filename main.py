import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import os

# 🔐 改用直接讀取檔案的方式，避開文字編碼問題
def get_gspread_client():
    try:
        # 指定讀取剛才上傳的 key.json
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        # 檢查檔案是否存在
        if os.path.exists("key.json"):
            creds = Credentials.from_service_account_file("key.json", scopes=scope)
            return gspread.authorize(creds)
        else:
            st.error("找不到 key.json 檔案，請確認已上傳至 GitHub。")
            return None
    except Exception as e:
        st.error(f"認證失敗：{e}")
        return None

# --- UI 介面 ---
st.set_page_config(page_title="IKKON 日報表系統", page_icon="📝")
st.title("IKKON 日報表系統")

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
    st.subheader("👥 營運指標")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
avg_spend = total_revenue / total_customers if total_customers > 0 else 0
productivity = total_revenue / total_hours if total_hours > 0 else 0

st.divider()

st.subheader("✍️ 營運報告與客訴處理")
ops_note = st.text_area("營運回報、事務宣達", placeholder="今日物料、人力狀況...")
complaint_note = st.text_area("客訴處理 (若無填「無」)", placeholder="客訴原因與處理結果...")

st.metric("當日總營收", f"{total_revenue:,} 元")

if st.button("確認提交日報表", type="primary", use_container_width=True):
    with st.spinner('正在同步至雲端試算表...'):
        client = get_gspread_client()
        if client:
            try:
                # 您的試算表 ID
                sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
                new_row = [
                    str(date), department, cash, credit_card, remittance, 
                    total_revenue, total_customers, round(avg_spend, 1), 
                    kitchen_hours, floor_hours, total_hours, round(productivity, 1),
                    ops_note, complaint_note
                ]
                sheet.append_row(new_row)
                st.success("✅ 存檔成功！您可以安心休息了。")
                st.balloons()
            except Exception as e:
                st.error(f"雲端寫入失敗：{e}")
