import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

# 重新定義欄位結構 (共 30 欄)，請務必確保 Google Sheets 的標題列與此一致
SHEET_COLUMNS = [
    "日期", "部門", "現金", "刷卡", "匯款", "現金折價卷", "金額備註",
    "總營業額", "月營業額", "目標占比", "總來客數", "客單價", 
    "內場工時", "外場工時", "總工時", "平均時薪", "工時產值", "人事成本占比",
    "昨日剩", "今日支出", "今日補", "今日剰", 
    "IKKON折抵券", "1000折價券", "總共折抵金",
    "營運回報", "客訴分類標籤", "客訴原因說明", "客訴處理結果", "事項宣達"
]

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

SID = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"

@st.cache_data(ttl=300)
def load_all_data():
    client = get_gspread_client()
    if not client: return None, None, None
    try:
        sh = client.open_by_key(SID)
        user_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
        settings_df = pd.DataFrame(sh.worksheet("Settings").get_all_records())
        report_data = sh.worksheet("Sheet1").get_all_records()
        return user_df, settings_df, report_data
    except Exception as e:
        st.error(f"資料讀取失敗：{e}")
        return None, None, None

def get_report_sheet():
    client = get_gspread_client()
    sh = client.open_by_key(SID)
    return sh.worksheet("Sheet1")

def login_ui(user_df):
    if st.session_state.get("logged_in"): return True
    st.title("IKKON 系統管理登入")
    with st.form("login_form"):
        input_user = st.text_input("帳號名稱")
        input_pwd = st.text_input("密碼", type="password")
        if st.form_submit_button("登入"):
            if user_df is not None and not user_df.empty:
                user_df['密碼'] = user_df['密碼'].astype(str)
                match = user_df[(user_df['帳號名稱'] == input_user) & (user_df['密碼'] == input_pwd)]
                if not match.empty:
                    user_info = match.iloc[0]
                    st.session_state.update({
                        "logged_in": True, "user_role": user_info['權限等級'], 
                        "user_name": user_info['帳號名稱'], "dept_access": user_info['負責部門']
                    })
                    st.rerun()
            st.error("帳號或密碼錯誤")
    return False

user_df, settings_df, report_data = load_all_data()

if login_ui(user_df):
    TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
    HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))

    with st.sidebar:
        st.title(f"{st.session_state['user_name']}")
        mode = st.radio("功能選單", ["數據錄入", "月度損益彙總"])
        if st.button("刷新數據"):
            st.cache_data.clear()
            st.rerun()
        if st.button("安全登出"):
            st.session_state.clear()
            st.rerun()

    if mode == "數據錄入":
        st.title("營運數據錄入")
        dept_options = list(TARGETS.keys()) if st.session_state['dept_access'] == "ALL" else [st.session_state['dept_access']]
        department = st.selectbox("部門", dept_options)
        date = st.date_input("報表日期", datetime.date.today())
        avg_rate = HOURLY_RATES.get(department, 205)
        month_target = TARGETS.get(department, 1000000) # 預設目標，可由 settings_df 取得
        
        # --- 第一區塊：營收與工時輸入 ---
        st.subheader("營收與客數")
        c1, c2, c3 = st.columns(3)
        with c1:
            cash = st.number_input("現金收入", min_value=0, step=100)
            card = st.number_input("刷卡收入", min_value=0, step=100)
        with c2:
            remit = st.number_input("匯款收入", min_value=0, step=100)
            cash_coupon = st.number_input("現金折價卷", min_value=0, step=100)
        with c3:
            customers = st.number_input("總來客數", min_value=1, step=1)
            rev_memo = st.text_input("金額備註", "無")

        st.subheader("工時數據")
        t1, t2 = st.columns(2)
        with t1:
            k_hours = st.number_input("內場工時", min_value=0.0, step=0.5)
        with t2:
            f_hours = st.number_input("外場工時", min_value=0.0, step=0.5)

        # --- 第二區塊：零用金與折抵券輸入 ---
        st.subheader("零用金回報")
        p1, p2, p3 = st.columns(3)
        with p1:
            petty_yesterday = st.number_input("昨日剩", value=0, step=100)
        with p2:
            petty_expense = st.number_input("今日支出", min_value=0, step=100)
        with p3:
            petty_replenish = st.number_input("今日補", min_value=0, step=100)
        
        # 自動計算今日剩餘零用金
        petty_today = petty_yesterday - petty_expense + petty_replenish
        st.info(f"今日剰 (自動計算)：${petty_today:,}")

        st.subheader("折價券統計")
        v1, v2 = st.columns(2)
        with v1:
            ikkon_coupon = st.number_input("IKKON折抵券金額", min_value=0, step=100)
        with v2:
            thousand_coupon = st.number_input("1000折價券金額", min_value=0, step=1000)
        
        # 自動計算總折抵金
        total_coupon = cash_coupon + ikkon_coupon + thousand_coupon

        # --- 第三區塊：文字回報 ---
        st.subheader("營運與客訴回報")
        ops_note = st.text_area("營運狀況回報", height=100)
        announcement = st.text_area("事項宣達", height=60)
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
            tags_str = ", ".join(tags) if tags else "無"
        with col_c2:
            reason_action = st.text_area("原因與處理結果", height=60)

        # --- 核心邏輯計算 ---
        total_rev = cash + card + remit
        total_hrs = k_hours + f_hours
        productivity = total_rev / total_hrs if total_hrs > 0 else 0
        labor_ratio = (total_hrs * avg_rate) / total_rev if total_rev > 0 else 0
        avg_customer_spend = total_rev / customers if customers > 0 else 0

        # 計算月營業額與目標佔比 (撈取歷史資料 + 本日營收)
        current_month_rev = total_rev
        if report_data:
            raw_df = pd.DataFrame(report_data)
            if not raw_df.empty:
                raw_df['日期'] = pd.to_datetime(raw_df['日期'])
                current_month_str = date.strftime('%Y-%m')
                # 篩選同部門且同月份的歷史營收
                mask = (raw_df['部門'] == department) & (raw_df['日期'].dt.strftime('%Y-%m') == current_month_str)
                historical_month_rev = pd.to_numeric(raw_df.loc[mask, '總營業額'], errors='coerce').fillna(0).sum()
                current_month_rev += historical_month_rev
        
        target_ratio = (current_month_rev / month_target) if month_target > 0 else 0

        # --- 提交與截圖區 ---
        if st.button("提交報表", type="primary", use_container_width=True):
            sheet = get_report_sheet()
            new_row = [
                str(date), department, cash, card, remit, cash_coupon, rev_memo,
                total_rev, current_month_rev, f"{target_ratio*100:.1f}%", customers, avg_customer_spend,
                k_hours, f_hours, total_hrs, avg_rate, productivity, f"{labor_ratio*100:.1f}%",
                petty_yesterday, petty_expense, petty_replenish, petty_today,
                ikkon_coupon, thousand_coupon, total_coupon,
                ops_note, tags_str, reason_action, "已提交", announcement
            ]
            sheet.append_row(new_row)
            st.cache_data.clear()
            
            # --- 專業版精簡截圖區 ---
            st.divider()
            st.markdown(f"### 【IKKON 營運日報】 {date} | {department}")
            
            # 使用 Markdown 表格呈現高密度專業排版
            report_md = f"""
| 營收指標 | 金額/數據 | 營運指標 | 數據 |
| :--- | :--- | :--- | :--- |
| **總營業額** | **${total_rev:,.0f}** | **總來客數** | {customers} 人 |
| 現金 | ${cash:,.0f} | 客單價 | ${avg_customer_spend:,.0f} |
| 刷卡 | ${card:,.0f} | 工時產值 | ${productivity:,.0f}/hr |
| 匯款 | ${remit:,.0f} | 人事占比 | {labor_ratio*100:.1f}% |
| 現金折價卷 | ${cash_coupon:,.0f} | 內/外場工時 | {k_hours} / {f_hours} hr |
| **月營業額** | **${current_month_rev:,.0f}** | **目標占比** | **{target_ratio*100:.1f}%** |

| 零用金管理 | 金額 | 折抵券結算 | 金額 |
| :--- | :--- | :--- | :--- |
| 昨日剩 | ${petty_yesterday:,.0f} | IKKON折抵券 | ${ikkon_coupon:,.0f} |
| 今日支出 | ${petty_expense:,.0f} | 1000折價券 | ${thousand_coupon:,.0f} |
| 今日補 | ${petty_replenish:,.0f} | | |
| **今日剰** | **${petty_today:,.0f}** | **總共折抵金** | **${total_coupon:,.0f}** |
"""
            st.markdown(report_md)
            if rev_memo != "無":
                st.caption(f"**金額備註：** {rev_memo}")
            
            st.divider()

            # 文字複製區
            st.subheader("系統文字彙整 (請直接複製)")
            text_summary = f"""【營運回報】
{ops_note}

【事項宣達】
{announcement}

【客訴處理】({tags_str})
{reason_action}"""
            st.code(text_summary, language="text")

    elif mode == "月度損益彙總":
        # ... (保留原有的月度彙總程式碼，此處略過未修改部分以節省篇幅) ...
        st.title("月度財務彙總分析")
        st.info("此區塊保持原樣，待後續需要擴充時再行處理。")
