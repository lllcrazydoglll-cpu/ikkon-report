import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import os

# 🔐 認證邏輯：讀取 key.json
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
    amount_note = st.text_input("金額備註", placeholder="若有特殊溢收/短少請註記")

with col2:
    # ✅ 依照您的要求，圖示已更新為 💹
    st.subheader("💹 營運指標")
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

# 自動計算
total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
avg_spend = total_revenue / total_customers if total_customers > 0 else 0
productivity = total_revenue / total_hours if total_hours > 0 else 0

st.divider()

# 3. 營運與客訴分析
st.subheader("✍️ 營運報告與客訴分析")
ops_note = st.text_area("營運回報、事務宣達", placeholder="今日物料、人力狀況...")

st.markdown("---")
st.markdown("#### 🔍 客訴標籤化系統")
complaint_tags = st.multiselect(
    "客訴分類標籤 (可多選)",
    ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"],
    help="選擇分類有助於後台自動生成經營分析圖表"
)

# 員工填寫的具體原因
complaint_reason = st.text_area("客訴原因詳細說明", placeholder="請描述發生經過、客訴具體內容...")

# 處理結果
complaint_action = st.text_area("處理結果與補償", placeholder="例如：招待肉盤一份、當場致歉並更換食材...")

st.metric("當日總營業額", f"{total_revenue:,} 元")

# 4. 提交邏輯
if st.button("確認提交日報表", type="primary", use_container_width=True):
    with st.spinner('正在同步至雲端試算表...'):
        client = get_gspread_client()
        if client:
            try:
                sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
                
                # 整理標籤字串
                tags_str = ", ".join(complaint_tags) if complaint_tags else "無"
                
                # 嚴格對照試算表欄位順序
                new_row = [
                    str(date),          # A: 日期
                    department,         # B: 部門
                    cash,               # C: 現金
                    credit_card,        # D: 刷卡
                    remittance,         # E: 匯款
                    amount_note,        # F: 金額備註
                    total_revenue,      # G: 總營業額
                    total_customers,    # H: 總來客數
                    round(avg_spend, 1),# I: 客單價
                    kitchen_hours,      # J: 內場工時
                    floor_hours,        # K: 外場工時
                    total_hours,        # L: 總工時
                    round(productivity, 1), # M: 工時產值
                    ops_note,           # N: 營運回報
                    tags_str,           # O: 客訴標籤
                    complaint_reason,   # P: 客訴原因
                    complaint_action    # Q: 處理結果
                ]
                
                sheet.append_row(new_row)
                st.success("✅ 資料已依照標籤化格式存檔成功！")
                st.balloons()
            except Exception as e:
                st.error(f"雲端寫入失敗：{e}")
