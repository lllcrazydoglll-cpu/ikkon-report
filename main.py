import streamlit as st
import datetime
import pandas as pd
import os

# 設置檔案路徑
DATA_FILE = "daily_reports.csv"

# 標題 (對應 IKKON 日報表)
st.title("IKKON 日報表系統")

# 1. 基礎資訊
date = st.date_input("報表日期", datetime.date.today())
# 更新部門選項
department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中和牛會所"])

# 2. 營運數據輸入
st.header("圖 營運數據")
st.caption("輸入今日營收與工時資料")

col1, col2 = st.columns(2)

with col1:
    cash = st.number_input("現金收入", min_value=0)
    credit_card = st.number_input("刷卡收入", min_value=0)
    remittance = st.number_input("匯款收入", min_value=0)
    # 新增：金額備註
    revenue_remark = st.text_input("金額備註 (例如：退款原因或差異說明)")

with col2:
    total_customers = st.number_input("總來客數", min_value=0)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0)
    floor_hours = st.number_input("外場總工時", min_value=0.0)

# 3. 計算邏輯
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
productivity = total_revenue / total_hours if total_hours > 0 else 0
avg_spend = total_revenue / total_customers if total_customers > 0 else 0

# 4. 營運回報 (PDF 底部內容)
st.header("營運回報")
ops_note = st.text_area("營運回報、事務宣達")
complaint_note = st.text_area("客訴、危機處理")

# 5. 提交與儲存
if st.button("提交日報表並儲存"):
    # 建立一筆資料紀錄
    new_data = {
        "日期": date,
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
    }
    
    # 轉成 Pandas DataFrame
    df_new = pd.DataFrame([new_data])
    
    # 檢查檔案是否存在
    if not os.path.isfile(DATA_FILE):
        df_new.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    else:
        # 存在則附加在最後一行 (append)
        df_new.to_csv(DATA_FILE, mode='a', index=False, header=False, encoding="utf-8-sig")
    
    st.success(f"? {date} {department} 的數據已成功存入系統！")

# 6. 預覽已存檔數據 (供你檢查)
if st.checkbox("查看歷史存檔紀錄"):
    if os.path.isfile(DATA_FILE):
        history_df = pd.read_csv(DATA_FILE)
        st.write(history_df)
    else:
        st.info("目前尚無存檔紀錄。")
