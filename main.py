import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

# 1. 系統登入與安全性 (密碼：IKKON888)
def check_password():
    def password_entered():
        if st.session_state["password"] == "IKKON888":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("IKKON 系統管理登入")
        st.text_input("請輸入管理密碼", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("IKKON 系統管理登入")
        st.text_input("密碼錯誤，請重新輸入", type="password", on_change=password_entered, key="password")
        return False
    return True

# 2. Google Sheets 認證邏輯
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"雲端連線失敗：{e}")
        return None

# --- 主程式執行 ---
if check_password():
    # 經營參數 (可依店鋪彈性調整)
    TARGETS = {"桃園鍋物": 2000000, "桃園燒肉": 2000000, "台中和牛會所": 2000000}
    HOURLY_RATES = {"桃園鍋物": 290, "桃園燒肉": 270, "台中和牛會所": 270}

    st.set_page_config(page_title="IKKON Management System", layout="wide")
    st.title("IKKON 營運數據管理系統")

    # 1. 基礎設定
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        date = st.date_input("報表日期", datetime.date.today())
    with col_h2:
        department = st.selectbox("所屬部門", list(TARGETS.keys()))

    avg_hourly_rate = HOURLY_RATES[department]
    st.divider()

    # 2. 數據輸入區
    st.subheader("核心數據錄入")
    c_in1, c_in2 = st.columns(2)
    with c_in1:
        cash = st.number_input("現金收入", min_value=0, step=100)
        credit_card = st.number_input("刷卡收入", min_value=0, step=100)
        remittance = st.number_input("匯款收入", min_value=0, step=100)
        amount_note = st.text_input("金額備註 (例如：訂金轉入或特殊支付)", value="無")
    with c_in2:
        total_customers = st.number_input("總來客數", min_value=1, step=1)
        k_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
        f_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

    # 邏輯計算
    total_revenue = cash + credit_card + remittance
    total_hours = k_hours + f_hours
    productivity = total_revenue / total_hours if total_hours > 0 else 0
    labor_cost_ratio = (total_hours * avg_hourly_rate) / total_revenue if total_revenue > 0 else 0
    avg_spend = total_revenue / total_customers if total_customers > 0 else 0

    st.divider()

    # 3. 營運與客訴文字區
    st.subheader("營運細節摘要")
    ops_note = st.text_area("營運狀況回報", height=100)
    announcement = st.text_area("事項宣達 (針對內部同仁)", height=60)
    
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
    with col_c2:
        reason = st.text_input("客訴原因與處理結果")

    # 4. 資料傳輸
    if st.button("提交報表至雲端資料庫", type="primary", use_container_width=True):
        client = get_gspread_client()
        if client:
            try:
                sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
                tags_str = ", ".join(tags) if tags else "無"
                new_row = [str(date), department, cash, credit_card, remittance, amount_note, total_revenue, total_customers, round(avg_spend, 1), k_hours, f_hours, total_hours, avg_hourly_rate, round(productivity, 1), f"{labor_cost_ratio:.1%}", ops_note, tags_str, reason, "已處理", announcement]
                
                # 自動更新或新增
                all_data = sheet.get_all_values()
                target_row = -1
                for i, row in enumerate(all_data[1:], start=2):
                    if row[0] == str(date) and row[1] == department:
                        target_row = i
                        break
                
                if target_row != -1:
                    sheet.update(f"A{target_row}:T{target_row}", [new_row])
                    st.success("✅ 數據已更新至雲端")
                else:
                    sheet.append_row(new_row)
                    st.success("✅ 數據已新增至雲端")
            except Exception as e:
                st.error(f"提交失敗：{e}")

    st.divider()

    # 5. 專業截圖區
    if st.checkbox("開啟截圖模式"):
        # 區塊 A: 財務專用 (詳細列出所有金流細項)
        st.subheader("📍 財務截圖區 (請傳至財務群組)")
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 25px; border: 1px solid #333; color: #000000; font-family: sans-serif;">
            <div style="font-size: 20px; font-weight: bold; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px;">
                IKKON 財務日報表 - {date}
            </div>
            <p><b>部門：</b>{department}</p>
            <table style="width:100%; border-collapse: collapse; margin-bottom: 15px;">
                <tr style="border-bottom: 1px solid #ddd;"><td>今日總營收</td><td style="text-align:right;"><b>{total_revenue:,} 元</b></td></tr>
                <tr><td style="padding-left: 15px; font-size: 0.9em; color: #555;">- 現金收入</td><td style="text-align:right;">{cash:,} 元</td></tr>
                <tr><td style="padding-left: 15px; font-size: 0.9em; color: #555;">- 刷卡收入</td><td style="text-align:right;">{credit_card:,} 元</td></tr>
                <tr><td style="padding-left: 15px; font-size: 0.9em; color: #555;">- 匯款收入</td><td style="text-align:right;">{remittance:,} 元</td></tr>
                <tr style="border-top: 1px solid #ddd;"><td>工時產值</td><td style="text-align:right;">{int(productivity):,} 元/時</td></tr>
                <tr><td>人事成本比</td><td style="text-align:right;">{labor_cost_ratio:.1%}</td></tr>
            </table>
            <p style="font-size: 14px; background: #f9f9f9; padding: 10px;"><b>財務備註：</b><br>{amount_note}</p>
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        # 區塊 B: 營運專用 (文字回報為主)
        st.subheader("📍 營運截圖區 (請傳至全體同仁群組)")
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 25px; border: 1px solid #333; color: #000000; font-family: sans-serif;">
            <div style="font-size: 20px; font-weight: bold; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px;">
                IKKON 營運狀況摘要 - {date}
            </div>
            <p><b>部門：</b>{department}</p>
            <div style="margin-top: 10px; padding: 10px; border-left: 4px solid #333; background: #f9f9f9;">
                <b>📝 營運回報：</b><br>
                <span style="white-space: pre-wrap;">{ops_note if ops_note else "無特別狀況"}</span>
            </div>
            <div style="margin-top: 10px; padding: 10px; border-left: 4px solid #333; background: #f9f9f9;">
                <b>📢 事項宣達：</b><br>
                <span style="white-space: pre-wrap;">{announcement if announcement else "無"}</span>
            </div>
            <div style="margin-top: 10px; padding: 10px; border-left: 4px solid #d32f2f; background: #fff5f5;">
                <b>⚠️ 客訴分類：</b>{", ".join(tags) if tags else "無"}<br>
                <b>原因與處理：</b>{reason if reason else "無"}
            </div>
        </div>
        """, unsafe_allow_html=True)
