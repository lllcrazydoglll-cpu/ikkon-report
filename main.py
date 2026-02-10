import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import base64  # 必須有這行

def get_gspread_client():
    try:
        info = dict(st.secrets["gcp_service_account"])
        # 解碼 Base64 並放入 private_key
        decoded_key = base64.b64decode(info["private_key_base64"]).decode("utf-8")
        info["private_key"] = decoded_key
        
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"認證失敗: {e}")
        return None
        
# 2. 介面設定
st.set_page_config(page_title="IKKON 日報表系統", page_icon="📝")
st.title("IKKON 日報表系統")

# 3. 輸入欄位（這是你剛才消失的部分）
date = st.date_input("報表日期", datetime.date.today())
department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中和牛會所"])

st.header("營運數據")
col1, col2 = st.columns(2)
with col1:
    cash = st.number_input("現金收入", min_value=0)
    credit_card = st.number_input("刷卡收入", min_value=0)
    remittance = st.number_input("匯款收入", min_value=0)
with col2:
    total_customers = st.number_input("總來客數", min_value=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0)
    floor_hours = st.number_input("外場總工時", min_value=0.0)

# 計算邏輯
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
productivity = total_revenue / total_hours if total_hours > 0 else 0
avg_spend = total_revenue / total_customers if total_customers > 0 else 0

st.write(f"### 當日總營收：{total_revenue:,} 元")

st.header("營運回報")
ops_note = st.text_area("營運回報、事務宣達")
complaint_note = st.text_area("客訴處理")

# 4. 提交邏輯
if st.button("提交日報表"):
    with st.spinner('正在上傳數據至 Google Sheets...'):
        client = get_gspread_client()
        if client:
            try:
                # 取得試算表並寫入第一張工作表
                sheet = client.open_by_key(st.secrets["spreadsheet"]["id"]).sheet1
                
                # 準備要插入的資料列
                new_row = [
                    str(date), department, cash, credit_card, remittance, "", 
                    total_revenue, total_customers, round(avg_spend, 2), 
                    kitchen_hours, floor_hours, total_hours, round(productivity, 2), 
                    ops_note, complaint_note
                ]
                
                sheet.append_row(new_row)
                st.success("✅ 數據已成功存入雲端！")
                st.balloons()
            except Exception as e:
                st.error(f"寫入失敗，請確認試算表 ID 是否正確。錯誤: {e}")


