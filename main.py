import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# 認證函數：終極解法
def get_gspread_client():
    try:
        # 直接獲取原始 Secrets 內容
        info = dict(st.secrets["gcp_service_account"])
        
        # 強制修復：將 "\n" 符號轉化為真正的換行符
        # 這是為了解決 Windows 記事本與 Web 傳輸間的編碼落差
        raw_key = info["private_key"]
        if "\\n" in raw_key:
            info["private_key"] = raw_key.encode().decode('unicode_escape')
            
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"認證模組啟動失敗: {e}")
        return None

st.title("IKKON 日報表系統")

# ... (中間的輸入欄位代碼保持不變，略) ...

if st.button("提交日報表"):
    client = get_gspread_client()
    if client:
        try:
            # 確保使用 Secrets 中的 ID
            sheet = client.open_by_key(st.secrets["spreadsheet"]["id"]).sheet1
            
            # 資料準備與寫入
            new_row = [str(date), department, cash, credit_card, remittance, "", 
                       total_revenue, total_customers, round(avg_spend, 2), 
                       kitchen_hours, floor_hours, total_hours, round(productivity, 2), 
                       ops_note, complaint_note]
            
            sheet.append_row(new_row)
            st.success("✅ 數據已成功存入雲端！")
            st.balloons()
        except Exception as e:
            st.error(f"寫入失敗，請確認試算表共用設定。錯誤: {e}")
