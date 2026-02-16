import streamlit as st

# 假設你已經有了這些變數：cash_income, card_income, transfer_income, remarks, etc.

# --- 區塊一：財務日報（詳細版） ---
st.markdown("### 💰 IKKON 財務日報 (細項)")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**今日總營收：** {total_revenue:,} 元")
        st.write(f"**現金收入：** {cash_income:,} 元")
        st.write(f"**刷卡收入：** {card_income:,} 元")
    with col2:
        st.write(f"**匯款收入：** {transfer_income:,} 元")
        st.write(f"**金額備註：** {remarks if remarks else '無'}")
    
    st.divider()
    st.write(f"**工時產值：** {productivity} 元/時")
    st.write(f"**人事成本比：** {labor_cost_ratio}%")

# --- 區塊二：營運回報（防止溢出） ---
st.markdown("### 📝 營運與客訴摘要")
with st.expander("展開完整回報內容", expanded=True):
    st.info(ops_report_text) # 使用 st.info 會有漂亮的背景色且自動換行
    st.write(f"**客訴分類：** {complaint_type}")

# --- 區塊三：一鍵複製功能（解決截圖問題） ---
st.divider()
st.markdown("### 🚀 快速發送報表")

# 建立純文字格式，方便 LINE 轉傳
report_template = f"""
【IKKON 財務日報 - {selected_date}】
部門：{department}
------------------------
今日總營收：{total_revenue:,} 元
- 現金：{cash_income:,} 元
- 刷卡：{card_income:,} 元
- 匯款：{transfer_income:,} 元
備註：{remarks}

工時產值：{productivity} 元/時
人事成本比：{labor_cost_ratio}%
------------------------
營運回報：
{ops_report_text}
"""

st.code(report_template, language="text") # 這格在手機上點擊右上角即可一鍵複製
st.caption("💡 提示：點擊上方框框右上角的圖示即可複製全文，直接貼到 LINE 群組。")
