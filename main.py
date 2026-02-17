import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

# 1. 頁面配置 (必須放在程式碼最上方)
st.set_page_config(page_title="IKKON Management System", layout="wide")

# 2. 雙軌登入邏輯修正
def check_password():
    """回傳 True 代表已成功登入"""
    def password_entered():
        pwd = st.session_state["password_input"]
        if pwd == "IKKONADMIN":
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "admin"
        elif pwd == "IKKON888":
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "staff"
        else:
            st.session_state["password_correct"] = False
        # 清除輸入框
        st.session_state["password_input"] = ""

    if st.session_state.get("password_correct"):
        return True

    st.title("IKKON 系統管理登入")
    st.text_input("請輸入管理或員工密碼", type="password", on_change=password_entered, key="password_input")
    
    if st.session_state.get("password_correct") == False:
        st.error("😕 密碼錯誤，請重新輸入。")
    return False

# 3. Google Sheets 認證
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
    client = get_gspread_client()
    spreadsheet_key = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"
    
    # 預設參數 (若雲端讀取失敗時使用)
    TARGETS = {"桃園鍋物": 2000000, "桃園燒肉": 2000000, "台中和牛會所": 2000000}
    HOURLY_RATES = {"桃園鍋物": 205, "桃園燒肉": 205, "台中和牛會所": 205}
    target_sheet = None

    # 嘗試讀取雲端 Settings
    if client:
        try:
            target_sheet = client.open_by_key(spreadsheet_key).worksheet("Settings")
            settings_df = pd.DataFrame(target_sheet.get_all_records())
            if not settings_df.empty:
                TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
                HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))
        except Exception:
            st.warning("⚠️ 尚未偵測到 Settings 工作表，目前使用預設參數。")

    # --- 管理者後台 (側邊欄) ---
    # 使用 .get() 確保不會出現 KeyError
    current_role = st.session_state.get("user_role", "staff")

    with st.sidebar:
        st.title("IKKON 控制中心")
        st.info(f"👤 當前權限：{'管理者' if current_role == 'admin' else '一般員工'}")
        
        if current_role == "admin":
            admin_mode = st.checkbox("開啟參數編輯")
            if admin_mode and target_sheet:
                st.subheader("⚙️ 編輯營運參數")
                new_targets = {}
                new_rates = {}
                for dept in TARGETS.keys():
                    new_targets[dept] = st.number_input(f"{dept} 月目標", value=int(TARGETS[dept]), step=100000)
                    new_rates[dept] = st.number_input(f"{dept} 時薪", value=int(HOURLY_RATES[dept]), step=5)
                
                if st.button("💾 永久儲存設定至雲端"):
                    try:
                        update_data = [["部門", "月目標", "平均時薪"]]
                        for dept in TARGETS.keys():
                            update_data.append([dept, new_targets[dept], new_rates[dept]])
                        target_sheet.update("A1", update_data)
                        st.success("✅ 設定已永久儲存")
                        st.rerun()
                    except Exception as e:
                        st.error(f"儲存失敗：{e}")
            
            if st.button("登出系統"):
                st.session_state.clear()
                st.rerun()
        else:
            st.write("---")
            st.caption("員工權限僅供數據錄入，若需調整時薪請聯繫管理者。")
            if st.button("登出"):
                st.session_state.clear()
                st.rerun()

    # --- 數據輸入主介面 ---
    st.title("IKKON 營運數據錄入")

    # 1. 基礎設定
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        date = st.date_input("報表日期", datetime.date.today())
    with col_h2:
        department = st.selectbox("所屬部門", list(TARGETS.keys()))

    avg_hourly_rate = HOURLY_RATES.get(department, 205)
    st.divider()

    # 2. 數據輸入區
    st.subheader("📊 財務與工時錄入")
    c_in1, c_in2 = st.columns(2)
    with c_in1:
        cash = st.number_input("現金收入", min_value=0, step=100)
        credit_card = st.number_input("刷卡收入", min_value=0, step=100)
        remittance = st.number_input("匯款收入", min_value=0, step=100)
        amount_note = st.text_input("金額備註", value="無")
    with c_in2:
        total_customers = st.number_input("總來客數", min_value=1, step=1)
        k_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
        f_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

    # 邏輯計算
    total_revenue = cash + credit_card + remittance
    total_hours = k_hours + f_hours
    productivity = total_revenue / total_hours if total_hours > 0 else 0
    labor_cost_ratio = (total_hours * avg_hourly_rate) / total_revenue if total_revenue > 0 else 0

    st.divider()

    # 3. 營運回報區
    st.subheader("📝 營運與客訴摘要")
    ops_note = st.text_area("營運狀況回報", height=100, placeholder="請詳述今日現場狀況...")
    announcement = st.text_area("事項宣達", height=60, placeholder="需讓全體同仁知悉的事項...")
    
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
    with col_c2:
        reason_action = st.text_area("客訴原因與處理結果", height=60, placeholder="例如：招待肉盤乙份...")

    # 4. 提交
    if st.button("🚀 確認提交報表至雲端", type="primary", use_container_width=True):
        if client:
            try:
                main_sheet = client.open_by_key(spreadsheet_key).sheet1
                tags_str = ", ".join(tags) if tags else "無"
                new_row = [str(date), department, cash, credit_card, remittance, amount_note, total_revenue, total_customers, 0, k_hours, f_hours, total_hours, avg_hourly_rate, round(productivity, 1), f"{labor_cost_ratio:.1%}", ops_note, tags_str, reason_action, "已處理", announcement]
                
                # 檢查是否重複提交
                all_data = main_sheet.get_all_values()
                target_row = -1
                for i, row in enumerate(all_data[1:], start=2):
                    if row[0] == str(date) and row[1] == department:
                        target_row = i
                        break
                
                if target_row != -1:
                    main_sheet.update(f"A{target_row}:T{target_row}", [new_row])
                    st.success("✅ 數據已成功覆蓋更新")
                else:
                    main_sheet.append_row(new_row)
                    st.success("✅ 數據已成功新增")
                st.balloons()
            except Exception as e:
                st.error(f"提交失敗：{e}")

    # 5. 回報模式
    if st.checkbox("🔍 開啟回報預覽 (截圖用)"):
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border: 1px solid #000; color: #000; width: 100%; max-width: 400px; margin-top:10px;">
            <h3 style="margin-top:0;">IKKON 財務日報 - {date}</h3>
            <p>部門：{department}</p>
            <hr>
            <table style="width:100%;">
                <tr><td>今日總營收</td><td style="text-align:right;"><b>{total_revenue:,}</b></td></tr>
                <tr><td> - 現金</td><td style="text-align:right;">{cash:,}</td></tr>
                <tr><td> - 刷卡</td><td style="text-align:right;">{credit_card:,}</td></tr>
                <tr><td> - 匯款</td><td style="text-align:right;">{remittance:,}</td></tr>
                <tr style="border-top: 1px solid #eee;"><td>工時產值</td><td style="text-align:right;">{int(productivity):,} 元/時</td></tr>
                <tr><td>人事成本比</td><td style="text-align:right;">{labor_cost_ratio:.1%}</td></tr>
            </table>
            <div style="margin-top: 10px; font-size: 12px; background: #f5f5f5; padding: 5px;">備註：{amount_note}</div>
        </div>
        """, unsafe_allow_html=True)
