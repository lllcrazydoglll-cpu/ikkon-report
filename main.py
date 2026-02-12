import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import os
import pandas as pd

# 🔐 認證邏輯
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        if os.path.exists("key.json"):
            creds = Credentials.from_service_account_file("key.json", scopes=scope)
            return gspread.authorize(creds)
        else:
            st.error("找不到 key.json 檔案。")
            return None
    except Exception as e:
        st.error(f"認證失敗：{e}")
        return None

# 🎯 設定各店本月目標 (你可以隨時修改這裡的數字)
TARGETS = {
    "桃園鍋物": 2000000,
    "桃園燒肉": 2000000,
    "台中和牛會所": 2000000
}

# --- UI 介面 ---
st.set_page_config(page_title="IKKON 日報表系統", page_icon="📝", layout="wide")
st.title("IKKON 日報表系統")

# 1. 基礎資訊
col_head1, col_head2 = st.columns(2)
with col_head1:
    date = st.date_input("報表日期", datetime.date.today())
with col_head2:
    department = st.selectbox("部門", list(TARGETS.keys()))

st.divider()

# 🚀 數據統計看板 (MTD 累積與目標達成)
client = get_gspread_client()
if client:
    try:
        sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            # 轉換日期格式以便計算
            df['日期'] = pd.to_datetime(df['日期'])
            current_month = datetime.date.today().month
            current_year = datetime.date.today().year
            
            # 過濾出：該部門 + 該月份 + 該年度 的資料
            monthly_df = df[
                (df['部門'] == department) & 
                (df['日期'].dt.month == current_month) & 
                (df['日期'].dt.year == current_year)
            ]
            
            mtd_revenue = monthly_df['總營業額'].sum()
            target = TARGETS[department]
            achievement_rate = (mtd_revenue / target) if target > 0 else 0
            
            # 顯示看板
            st.subheader(f"📊 {department} {current_month}月 營運進度")
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("本月累計營收", f"{mtd_revenue:,} 元")
            m_col2.metric("本月目標", f"{target:,} 元")
            m_col3.metric("目標達成率", f"{achievement_rate:.1%}")
            
            # 進度條
            progress_color = "green" if achievement_rate >= 1 else "orange"
            st.progress(min(achievement_rate, 1.0))
            if achievement_rate >= 1:
                st.success("🎉 恭喜！已達成月目標！")
        else:
            st.info("目前尚無歷史數據，開始輸入第一筆吧！")
    except Exception as e:
        st.warning(f"暫時無法讀取統計數據：{e}")

st.divider()

# 2. 數據輸入 (保持原有功能)
col1, col2 = st.columns(2)
with col1:
    st.subheader("💰 營收數據")
    cash = st.number_input("現金收入", min_value=0, step=100)
    credit_card = st.number_input("刷卡收入", min_value=0, step=100)
    remittance = st.number_input("匯款收入", min_value=0, step=100)
    amount_note = st.text_input("金額備註", value="無")

with col2:
    st.subheader("💹 營運指標")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
avg_spend = total_revenue / total_customers if total_customers > 0 else 0
productivity = total_revenue / total_hours if total_hours > 0 else 0

st.divider()

# 3. 營運與客訴分析
st.subheader("✍️ 營運報告與客訴分析")
ops_note = st.text_area("營運回報、事務宣達")
complaint_tags = st.multiselect("客訴分類標籤", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
complaint_reason = st.text_area("客訴原因詳細說明")
complaint_action = st.text_area("處理結果與補償")

if st.button("確認提交日報表", type="primary", use_container_width=True):
    with st.spinner('正在同步至雲端...'):
        if client:
            try:
                sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
                tags_str = ", ".join(complaint_tags) if complaint_tags else "無"
                new_row = [
                    str(date), department, cash, credit_card, remittance, amount_note,
                    total_revenue, total_customers, round(avg_spend, 1),
                    kitchen_hours, floor_hours, total_hours, round(productivity, 1),
                    ops_note, tags_str, complaint_reason, complaint_action
                ]
                sheet.append_row(new_row)
                st.success("✅ 資料存檔成功！")
                st.balloons()
                st.rerun() # 提交後重新整理，更新上方進度條
            except Exception as e:
                st.error(f"寫入失敗：{e}")
