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

# 🎯 經營參數設定 (由你本人在此修改，員工看不到此設定區)
# 月營業額目標
TARGETS = {
    "桃園鍋物": 2000000,
    "桃園燒肉": 2000000,
    "台中和牛會所": 2000000
}

# 各店平均時薪 (含勞健保預估)
HOURLY_RATES = {
    "桃園鍋物": 290,
    "桃園燒肉": 270,
    "台中和牛會所": 270
}

st.set_page_config(page_title="IKKON 日回報系統", page_icon="💹", layout="wide")
st.title("IKKON 日回報系統")

# 1. 基礎資訊
col_head1, col_head2 = st.columns(2)
with col_head1:
    date = st.date_input("報表日期", datetime.date.today())
with col_head2:
    department = st.selectbox("部門", list(TARGETS.keys()))

# 根據選擇的部門，自動帶入你設定的時薪
avg_hourly_rate = HOURLY_RATES[department]

st.divider()

# 🚀 數據統計看板 (MTD 月累計分析)
client = get_gspread_client()
if client:
    try:
        sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            df['日期'] = pd.to_datetime(df['日期'])
            current_month, current_year = datetime.date.today().month, datetime.date.today().year
            
            m_df = df[(df['部門'] == department) & (df['日期'].dt.month == current_month) & (df['日期'].dt.year == current_year)]
            
            if not m_df.empty:
                m_df['總營業額'] = pd.to_numeric(m_df['總營業額'], errors='coerce')
                m_df['工時產值'] = pd.to_numeric(m_df['工時產值'], errors='coerce')
                m_df['平均時薪'] = pd.to_numeric(m_df['平均時薪'], errors='coerce')
                m_df['總工時'] = pd.to_numeric(m_df['總工時'], errors='coerce')

                mtd_rev = m_df['總營業額'].sum()
                target = TARGETS[department]
                achieve = mtd_rev / target if target > 0 else 0
                avg_prod = m_df['工時產值'].mean()
                
                # 計算月累計人事成本
                total_labor_cost = (m_df['平均時薪'] * m_df['總工時']).sum()
                avg_labor_ratio = total_labor_cost / mtd_rev if mtd_rev > 0 else 0

                st.subheader(f"📊 {department} {current_month}月 營運狀況")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("月累計營收", f"{mtd_rev:,} 元", f"{achieve:.1%} 達成")
                m2.metric("目標達成率", f"{achieve:.1%}")
                m3.metric("月平均產值", f"{int(avg_prod):,} 元/小時")
                m4.metric("月人事成本比", f"{avg_labor_ratio:.1%}")
                st.progress(min(achieve, 1.0))
            else:
                st.info("本月尚無歷史數據。")
    except Exception as e:
        st.warning("統計看板更新中...")

st.divider()

# 2. 數據輸入區
st.subheader("📝 當日營運數據")
col1, col2 = st.columns(2)
with col1:
    st.markdown("#### 💰 營業數據")
    cash = st.number_input("現金收入", min_value=0, step=100)
    credit_card = st.number_input("刷卡收入", min_value=0, step=100)
    remittance = st.number_input("匯款收入", min_value=0, step=100)
    amount_note = st.text_input("金額備註", value="無")

with col2:
    st.markdown("#### 💹 人力成本")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

# 3. 核心邏輯計算
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
avg_spend = total_revenue / total_customers if total_customers > 0 else 0
productivity = total_revenue / total_hours if total_hours > 0 else 0

# 人事成本占比 (使用後台預設的 avg_hourly_rate)
daily_labor_cost = total_hours * avg_hourly_rate
labor_cost_ratio = daily_labor_cost / total_revenue if total_revenue > 0 else 0

# 顯示當日即時分析
st.markdown("#### 🔍 今日即時診斷")
c1, c2, c3 = st.columns(3)
c1.metric("今日工時產值", f"{int(productivity):,} 元/小時")
c2.metric("今日人事成本比", f"{labor_cost_ratio:.1%}")
c3.metric("今日總營收", f"{total_revenue:,} 元")

st.divider()

# 4. 報告區
st.subheader("✍️ 營運報告與客訴")
ops_note = st.text_area("營運回報")
complaint_tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
complaint_reason = st.text_area("詳細原因")
complaint_action = st.text_area("處理結果")

if st.button("確認提交日報表", type="primary", use_container_width=True):
    with st.spinner('正在同步至雲端...'):
        if client:
            try:
                sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
                tags_str = ", ".join(complaint_tags) if complaint_tags else "無"
                
                # 寫入 Excel (欄位順序維持 A-S 不變)
                new_row = [
                    str(date), department, cash, credit_card, remittance, amount_note,
                    total_revenue, total_customers, round(avg_spend, 1),
                    kitchen_hours, floor_hours, total_hours, 
                    avg_hourly_rate,        # 這裡會寫入你預設的時薪
                    round(productivity, 1), 
                    f"{labor_cost_ratio:.1%}", 
                    ops_note, tags_str, complaint_reason, complaint_action
                ]
                sheet.append_row(new_row)
                st.success("✅ 數據存檔成功！")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"寫入失敗：{e}")


