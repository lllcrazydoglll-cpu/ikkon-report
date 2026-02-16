import streamlit as st
from datetime import datetime

# --- 基礎設定 ---
st.set_page_config(page_title="IKKON 營運回報系統", layout="wide")
st.title("🏮 IKKON 營運數據錄入")

# --- 管理員參數 (後台填寫處) ---
# 桃園店、台中店可以根據不同店鋪設定不同時薪，目前先統一設為 220
FIXED_HOURLY_WAGE = 220 

# --- 第一區塊：營收與成本細項 ---
st.header("💰 營收與成本")
col_a, col_b = st.columns(2)

with col_a:
    department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中燒肉"])
    selected_date = st.date_input("日期", datetime.now())
    cash_income = st.number_input("現金收入", min_value=0, step=100)
    card_income = st.number_input("刷卡收入", min_value=0, step=100)
    transfer_income = st.number_input("匯款收入", min_value=0, step=100)
    remarks = st.text_area("金額備註", placeholder="例如：匯款包含昨日訂金...")

with col_b:
    customer_count = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

# --- 邏輯計算 ---
total_revenue = cash_income + card_income + transfer_income
total_hours = kitchen_hours + floor_hours
productivity = round(total_revenue / total_hours, 0) if total_hours > 0 else 0
labor_cost = total_hours * FIXED_HOURLY_WAGE
labor_cost_ratio = round((labor_cost / total_revenue) * 100, 1) if total_revenue > 0 else 0
avg_spending = round(total_revenue / customer_count, 0) if customer_count > 0 else 0

# --- 第二區塊：營運回報 ---
st.header("📝 營運回報")
ops_report_text = st.text_area("今日營運摘要 (請詳述)", height=150)
complaint_type = st.selectbox("客訴分類", ["無", "餐點問題", "服務問題", "環境衛生", "其他"])

# --- 第三區塊：結果顯示與複製區 ---
st.divider()
st.header("📊 報表生成 (財務專用)")

# 畫面顯示
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("今日總營收", f"{total_revenue:,} 元")
    c2.metric("工時產值", f"{productivity:,.0f} 元/時")
    c3.metric("人事成本比", f"{labor_cost_ratio}%")
    
    st.write(f"**細項報表：** 現金 {cash_income:,} | 刷卡 {card_income:,} | 匯款 {transfer_income:,}")
    st.write(f"**備註：** {remarks if remarks else '無'}")

# --- 核心解決方案：一鍵複製文字框 ---
st.subheader("🚀 LINE 回報專用 (點擊右上角圖示複製)")

# 組合出要發送的文字
report_for_line = f"""【IKKON 財務日報 - {selected_date}】
部門：{department}
------------------------
今日總營收：{total_revenue:,} 元
- 現金收入：{cash_income:,} 元
- 刷卡收入：{card_income:,} 元
- 匯款收入：{transfer_income:,} 元
- 金額備註：{remarks if remarks else "無"}
------------------------
總來客數：{customer_count} 位
平均客單：{avg_spending:,.0f} 元
工時產值：{productivity:,.0f} 元/時
人事成本比：{labor_cost_ratio}%
------------------------
營運回報：
{ops_report_text}
客訴分類：{complaint_type}
"""

st.code(report_for_line, language="text")
st.caption("💡 提示：在手機上直接點擊上方灰色框框，即可複製整段文字到 LINE 群組，解決截圖不全的問題。")
