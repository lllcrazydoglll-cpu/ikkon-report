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

# 🎯 設定各店月目標 (可隨時修改)
TARGETS = {
    "桃園鍋物": 2500000,
    "桃園燒肉": 3500000,
    "台中和牛會所": 5000000
}

st.set_page_config(page_title="IKKON 經營指揮中心", page_icon="💹", layout="wide")
st.title("IKKON 經營指揮中心")

# 1. 基礎資訊
col_head1, col_head2 = st.columns(2)
with col_head1:
    date = st.date_input("報表日期", datetime.date.today())
with col_head2:
    department = st.selectbox("部門", list(TARGETS.keys()))

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
            
            # 過濾當月資料
            m_df = df[(df['部門'] == department) & (df['日期'].dt.month == current_month) & (df['日期'].dt.year == current_year)]
            
            if not m_df.empty:
                mtd_rev = m_df['總營業額'].sum()
                target = TARGETS[department]
                achieve = m_df['總營業額'].sum() / target if target > 0 else 0
                
                # 計算月平均產值與人事占比
                avg_prod = m_df['工時產值'].mean()
                # 人事成本占比需從各行計算：(時薪*工時)/營收
                total_labor_cost = (m_df['平均時薪'] * m_df['總工時']).sum()
                avg_labor_ratio = total_labor_cost / m_df['總營業額'].sum() if m_df['總營業額'].sum() > 0 else 0

                # 顯示看板
                st.subheader(f"📊 {department} {current_month}月 戰報")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("月累計營收", f"{mtd_rev:,} 元", f"{achieve:.1%} 達成")
                m2.metric("目標達成率", f"{achieve:.1%}")
                m3.metric("月平均產值", f"{int(avg_prod):,} 元/小時")
                m4.metric("月人事成本比", f"{avg_labor_ratio:.1%}")
                st.progress(min(achieve, 1.0))
            else:
                st.info("本月尚無數據。")
    except Exception as e:
        st.warning(f"統計看板載入中... (或尚未建立新欄位標題)")

st.divider()

# 2. 數據輸入區
st.subheader("📝 當日營運數據錄入")
col1, col2 = st.columns(2)
with col1:
    st.markdown("#### 💰 營收與成本")
    cash = st.number_input("現金收入", min_value=0, step=100)
    credit_card = st.number_input("刷卡收入", min_value=0, step=100)
    remittance = st.number_input("匯款收入", min_value=0, step=100)
    avg_hourly_rate = st.number_input("當日平均時薪 (含勞健保預估)", min_value=0, value=200, step=5)
    amount_note = st.text_input("金額備註", value="無")

with col2:
    st.markdown("#### 💹 勞動力產出")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

# 3. 核心邏輯計算
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
avg_spend = total_revenue / total_customers if total_customers > 0 else 0
productivity = total_revenue / total_hours if total_hours > 0 else 0

# 【新增】人事成本占比計算
daily_labor_cost = total_hours * avg_hourly_rate
labor_cost_ratio = daily_labor_cost / total_revenue if total_revenue > 0 else 0

# 顯示當日即時分析
c1, c2, c3 = st.columns(3)
c1.metric("今日工時產值", f"{int(productivity):,} 元/時")
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
                
                # 重新校準過的欄位順序 (A-S 欄)
                new_row = [
                    str(date), department, cash, credit_card, remittance, amount_note,
                    total_revenue, total_customers, round(avg_spend, 1),
                    kitchen_hours, floor_hours, total_hours, 
                    avg_hourly_rate,        # 新增：平均時薪
                    round(productivity, 1), # 工時產值
                    f"{labor_cost_ratio:.3%}", # 新增：人事成本占比
                    ops_note, tags_str, complaint_reason, complaint_action
                ]
                sheet.append_row(new_row)
                st.success("✅ 數據已存檔，看板已更新！")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"寫入失敗：{e}")
