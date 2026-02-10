import streamlit as st
import datetime
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 標題
st.title("IKKON 日報表系統")

# 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 基礎資訊
date = st.date_input("報表日期", datetime.date.today())
department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中和牛會所"])

# 2. 營運數據輸入
st.header("圖 營運數據")
col1, col2 = st.columns(2)

with col1:
    cash = st.number_input("現金收入", min_value=0)
    credit_card = st.number_input("刷卡收入", min_value=0)
    remittance = st.number_input("匯款收入", min_value=0)
    revenue_remark = st.text_input("金額備註")

with col2:
    total_customers = st.number_input("總來客數", min_value=0)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0)
    floor_hours = st.number_input("外場總工時", min_value=0.0)

# 3. 計算邏輯
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
productivity = total_revenue / total_hours if total_hours > 0 else 0
avg_spend = total_revenue / total_customers if total_customers > 0 else 0

# 4. 營運回報
st.header("營運回報")
ops_note = st.text_area("營運回報、事務宣達")
complaint_note = st.text_area("客訴、危機處理")

# 5. 提交與儲存
if st.button("提交日報表至 Google Sheets"):
    try:
        # 使用服務帳號連線
        existing_data = conn.read(worksheet="Sheet1")
        existing_data = existing_data.dropna(how="all")
        
        # [cite_start]建立新資料 (欄位順序對齊 PDF) [cite: 1]
        new_report = pd.DataFrame([{
            "日期": str(date),
            "部門": department,
            "現金": cash,
            "刷卡": credit_card,
            "匯款": remittance,
            "金額備註": revenue_remark,
            "總營業額": total_revenue,
            "總來客數": total_customers,
            "客單價": round(avg_spend, 2),
            "內場工時": kitchen_hours,
            "外場工時": floor_hours,
            "總工時": total_hours,
            "工時產值": round(productivity, 2),
            "營運回報": ops_note,
            "客訴處理": complaint_note
        }])

        # 合併與更新
        updated_df = pd.concat([existing_data, new_report], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
        
        st.success("✅ 數據已安全存入 IKKON 雲端系統！")
        st.balloons() # 成功的小慶祝
    except Exception as e:
        st.error(f"連線失敗，請檢查權限設定。錯誤訊息：{e}")
