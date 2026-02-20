import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

# 定義欄位結構 (共 30 欄)
# 🚨 必須確保 Google Sheets 的標題列與此「完全一致」，尤其是「現金折價卷」的位置
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
    is_admin = st.session_state.get("user_role") == "admin"

    with st.sidebar:
        st.title(f"{st.session_state['user_name']}")
        st.caption(f"權限等級：{st.session_state['user_role'].upper()}")
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
        month_target = TARGETS.get(department, 1000000)
        
        # --- 自動抓取前一日零用金邏輯 ---
        last_petty_cash = 0
        if report_data:
            df_history = pd.DataFrame(report_data)
            if not df_history.empty and '今日剰' in df_history.columns:
                df_history['日期'] = pd.to_datetime(df_history['日期'])
                # 排除當前選定日期的資料，確保抓到的是「歷史」最後一筆
                past_history = df_history[(df_history['部門'] == department) & (df_history['日期'] < pd.to_datetime(date))]
                past_history = past_history.sort_values(by='日期', ascending=False)
                if not past_history.empty:
                    last_value = past_history.iloc[0]['今日剰']
                    if pd.notna(last_value) and str(last_value).strip() != "":
                        last_petty_cash = int(float(last_value))

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
            # 依據權限決定是否鎖定輸入框
            petty_yesterday = st.number_input(
                "昨日剩 (系統自動帶入)" if not is_admin else "昨日剩 (管理員解鎖模式)", 
                value=last_petty_cash, 
                step=100, 
                disabled=not is_admin
            )
        with p2:
            petty_expense = st.number_input("今日支出", min_value=0, step=100)
        with p3:
            petty_replenish = st.number_input("今日補", min_value=0, step=100)
        
        petty_today = petty_yesterday - petty_expense + petty_replenish
        st.info(f"今日剰 (自動計算)：${petty_today:,}")

        st.subheader("折價券統計")
        v1, v2 = st.columns(2)
        with v1:
            ikkon_coupon = st.number_input("IKKON折抵券金額", min_value=0, step=100)
        with v2:
            thousand_coupon = st.number_input("1000折價券金額", min_value=0, step=1000)
        
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
        total_rev = float(cash + card + remit)
        total_hrs = float(k_hours + f_hours)
        productivity = float(total_rev / total_hrs) if total_hrs > 0 else 0.0
        labor_ratio = float((total_hrs * avg_rate) / total_rev) if total_rev > 0 else 0.0
        avg_customer_spend = float(total_rev / customers) if customers > 0 else 0.0

        current_month_rev = total_rev
        if report_data:
            raw_df = pd.DataFrame(report_data)
            if not raw_df.empty:
                raw_df['日期'] = pd.to_datetime(raw_df['日期'])
                current_month_str = date.strftime('%Y-%m')
                # 計算當月歷史營收（排除今天，以免重複加總）
                mask = (raw_df['部門'] == department) & (raw_df['日期'].dt.strftime('%Y-%m') == current_month_str) & (raw_df['日期'] < pd.to_datetime(date))
                historical_month_rev = float(pd.to_numeric(raw_df.loc[mask, '總營業額'], errors='coerce').fillna(0).sum())
                current_month_rev += historical_month_rev
        
        target_ratio = float(current_month_rev / month_target) if month_target > 0 else 0.0

        # --- 提交與覆蓋邏輯 ---
        if st.button("提交報表", type="primary", use_container_width=True):
            sheet = get_report_sheet()
            
            new_row = [
                str(date), department, 
                int(cash), int(card), int(remit), int(cash_coupon), rev_memo,
                int(total_rev), int(current_month_rev), f"{target_ratio*100:.1f}%", 
                int(customers), int(avg_customer_spend),
                float(k_hours), float(f_hours), float(total_hrs), 
                int(avg_rate), int(productivity), f"{labor_ratio*100:.1f}%",
                int(petty_yesterday), int(petty_expense), int(petty_replenish), int(petty_today),
                int(ikkon_coupon), int(thousand_coupon), int(total_coupon),
                ops_note, tags_str, reason_action, "已提交", announcement
            ]
            
            # 尋找是否已有同日同部門的資料
            all_values = sheet.get_all_values()
            target_row_idx = None
            
            for i, row in enumerate(all_values):
                if i == 0: continue # 跳過標題列
                if len(row) >= 2 and row[0] == str(date) and row[1] == department:
                    target_row_idx = i + 1 # gspread 行數從 1 開始計算
                    break
            
            if target_row_idx:
                # 若存在，執行覆蓋更新 (使用 update_cells 確保相容性)
                cell_list = sheet.range(f"A{target_row_idx}:AD{target_row_idx}")
                for j, cell in enumerate(cell_list):
                    if j < len(new_row):
                        cell.value = new_row[j]
                sheet.update_cells(cell_list)
                st.success(f"{date} {department} 的營運報表已成功更新。")
            else:
                # 若不存在，新增至最後一行
                sheet.append_row(new_row)
                st.success(f"{date} {department} 的營運報表已成功新增。")
                
            st.cache_data.clear()
            
            # --- 專業版精簡截圖區 ---
            st.divider()
            st.markdown(f"### 【營運日報】 {date} | {department}")
            
            report_md = f"""
| 營收指標 | 金額/數據 | 營運指標 | 數據 |
| :--- | :--- | :--- | :--- |
| **總營業額** | **${int(total_rev):,.0f}** | **總來客數** | {int(customers)} 人 |
| 現金 | ${int(cash):,.0f} | 客單價 | ${int(avg_customer_spend):,.0f} |
| 刷卡 | ${int(card):,.0f} | 工時產值 | ${int(productivity):,.0f}/hr |
| 匯款 | ${int(remit):,.0f} | 人事占比 | {labor_ratio*100:.1f}% |
| 現金折價卷 | ${int(cash_coupon):,.0f} | 內/外場工時 | {k_hours} / {f_hours} hr |
| **月營業額** | **${int(current_month_rev):,.0f}** | **目標占比** | **{target_ratio*100:.1f}%** |

| 零用金管理 | 金額 | 折抵券結算 | 金額 |
| :--- | :--- | :--- | :--- |
| 昨日剩 | ${int(petty_yesterday):,.0f} | IKKON折抵券 | ${int(ikkon_coupon):,.0f} |
| 今日支出 | ${int(petty_expense):,.0f} | 1000折價券 | ${int(thousand_coupon):,.0f} |
| 今日補 | ${int(petty_replenish):,.0f} | | |
| **今日剰** | **${int(petty_today):,.0f}** | **總共折抵金** | **${int(total_coupon):,.0f}** |
"""
            st.markdown(report_md)
            if rev_memo != "無":
                st.caption(f"**金額備註：** {rev_memo}")
            
            st.divider()

            st.subheader("系統文字彙整 (請直接複製)")
            text_summary = f"""【營運回報】
{ops_note}

【事項宣達】
{announcement}

【客訴處理】({tags_str})
{reason_action}"""
            st.code(text_summary, language="text")

    elif mode == "月度損益彙總":
        st.title("月度財務彙總分析")
        raw_df = pd.DataFrame(report_data)
        if not raw_df.empty:
            raw_df['日期'] = pd.to_datetime(raw_df['日期'])
            if st.session_state['dept_access'] != "ALL":
                raw_df = raw_df[raw_df['部門'] == st.session_state['dept_access']]
            
            month_list = sorted(raw_df['日期'].dt.strftime('%Y-%m').unique(), reverse=True)
            target_month = st.selectbox("選擇月份", month_list)
            filtered_df = raw_df[raw_df['日期'].dt.strftime('%Y-%m') == target_month].copy()
            
            for col in ['總營業額', '總工時', '平均時薪', '現金', '刷卡', '匯款']:
                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0)
            
            m_rev = filtered_df['總營業額'].sum()
            m_hrs = filtered_df['總工時'].sum()
            m_cost = (filtered_df['總工時'] * filtered_df['平均時薪']).sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("當月總營收", f"${m_rev:,.0f}")
            c2.metric("預估人事支出", f"${m_cost:,.0f}")
            c3.metric("平均工時產值", f"${m_rev/m_hrs:,.0f}/hr" if m_hrs > 0 else "0")
            
            st.subheader("當月明細數據")
            display_cols = ['日期', '部門', '現金', '刷卡', '匯款', '總營業額', '金額備註', '營運回報', '客訴分類標籤']
            st.dataframe(filtered_df[display_cols], use_container_width=True)
        else:
            st.info("尚未有數據。")
