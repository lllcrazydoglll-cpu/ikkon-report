import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import os

# 🔐 認證邏輯：維持目前成功的 key.json 讀取模式
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        if os.path.exists("key.json"):
            creds = Credentials.from_service_account_file("key.json", scopes=scope)
            return gspread.authorize(creds)
        else:
            st.error("找不到 key.json 檔案，請確認檔案已上傳至 GitHub。")
            return None
    except Exception as e:
        st.error(f"認證失敗：{e}")
        return None

# --- UI 介面設定 ---
st.set_page_config(page_title="IKKON 日報表系統", page_icon="📝")
st.title("IKKON 日報表系統")

# 1. 基礎資訊
date = st.date_input("報表日期", datetime.date.today())
department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中和牛會所"])

st.divider()

# 2. 數據輸入
col1, col2 = st.columns(2)
with col1:
    st.subheader("💰 營收數據")
    cash = st.number_input("現金收入", min_value=0, step=100)
    credit_card = st.number_input("刷卡收入", min_value=0, step=100)
    remittance = st.number_input("匯款收入", min_value=0, step=100)
    # 📝 新增：金額備註欄位
    amount_note = st.text_input("金額備註", placeholder="若有特殊溢收/短少請註記")

with col2:
    st.subheader("💹 營運指標")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

# 3. 自動計算
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
avg_spend = total_revenue / total_customers if total_customers > 0 else 0
productivity = total_revenue / total_hours if total_hours > 0 else 0

st.divider()

# 4. 營運報告
st.subheader("✍️ 營運報告與客訴處理")
ops_note = st.text_area("營運回報、事務宣達", placeholder="今日物料、人力狀況...")
complaint_note = st.text_area("客訴處理 (若無填「無」)", placeholder="客訴原因與處理結果...")

# 營收顯示
st.metric("當日總營業額", f"{total_revenue:,} 元")

# 5. 提交邏輯
if st.button("確認提交日報表", type="primary", use_container_width=True):
    with st.spinner('正在同步至雲端試算表...'):
        client = get_gspread_client()
        if client:
            try:
                # 連結試算表
                sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
                
                # 嚴格對照您的試算表欄位順序
                # 日期, 部門, 現金, 刷卡, 匯款, 金額備註, 總營業額, 總來客數, 客單價, 內場工時, 外場工時, 總工時, 工時產值, 營運回報, 客訴處理
                new_row = [
                    str(date),          # 日期
                    department,         # 部門
                    cash,               # 現金
                    credit_card,        # 刷卡
                    remittance,         # 匯款
                    amount_note,        # 金額備註 (新增項)
                    total_revenue,      # 總營業額
                    total_customers,    # 總來客數
                    round(avg_spend, 1),# 客單價
                    kitchen_hours,      # 內場工時
                    floor_hours,        # 外場工時
                    total_hours,        # 總工時
                    round(productivity, 1), # 工時產值
                    ops_note,           # 營運回報
                    complaint_note      # 客訴處理
                ]
                
                sheet.append_row(new_row)
                st.success("✅ 資料已依照完整格式存檔成功！")
                st.balloons()
            except Exception as e:
                st.error(f"雲端寫入失敗：{e}")

