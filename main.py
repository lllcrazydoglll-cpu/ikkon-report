import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd
import altair as alt

# 頁面配置
st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

# 1. 定義資料結構主表 (Source of Truth)
# 嚴格對齊 Sheet1 的 A 到 T 欄位名稱，避免任何 KeyError
SHEET_COLUMNS = [
    "日期", "部門", "現金", "刷卡", "匯款", "金額備註",
    "總營業額", "總來客數", "客單價", "內場工時", "外場工時",
    "總工時", "平均時薪", "工時產值", "人事成本占比",
    "營運回報", "客訴分類標籤", "客訴原因說明", "客訴處理結果", "事項宣達"
]

# Google Sheets 認證
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

# 登入邏輯
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

# --- 主執行區 ---
user_df, settings_df, report_data = load_all_data()

if login_ui(user_df):
    TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
    HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))

    with st.sidebar:
        st.title(f"{st.session_state['user_name']}")
        menu_options = ["數據錄入", "月度損益彙總"]
        if st.session_state['user_name'] == "管理員" or st.session_state['user_role'] == 'admin':
            menu_options.append("後台參數設定")
        mode = st.radio("功能選單", menu_options)
        if st.button("刷新數據"):
            st.cache_data.clear()
            st.rerun()
        if st.button("安全登出"):
            st.session_state.clear()
            st.rerun()

    # 1. 數據錄入功能
    if mode == "數據錄入":
        st.title("IKKON 營運數據錄入")
        dept_options = list(TARGETS.keys()) if st.session_state['dept_access'] == "ALL" else [st.session_state['dept_access']]
        department = st.selectbox("所屬部門", dept_options)
        date = st.date_input("報表日期", datetime.date.today())
        avg_rate = HOURLY_RATES.get(department, 205)
        
        st.subheader("一、財務與工時")
        c1, c2 = st.columns(2)
        with c1:
            cash = st.number_input("現金收入", min_value=0, step=100)
            card = st.number_input("刷卡收入", min_value=0, step=100)
            remit = st.number_input("匯款收入", min_value=0, step=100)
            rev_memo = st.text_input("金額備註", "無")
        with c2:
            customers = st.number_input("總來客數", min_value=1, step=1)
            k_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
            f_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

        # 3. 營運回報區 (採用你要求的多選標籤架構)
        st.subheader("營運與客訴摘要")
        ops_note = st.text_area("營運狀況回報", height=100, placeholder="請詳述今日現場狀況...")
        announcement = st.text_area("事項宣達", height=60, placeholder="需讓全體同仁知悉的事項...")
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
            tags_str = ", ".join(tags) if tags else "無"
            comp_status = st.selectbox("處理狀態", ["已處理", "處理中", "無需處理"])
        with col_c2:
            reason_action = st.text_area("客訴原因與處理結果", height=60, placeholder="例如：招待肉盤乙份...")

        total_rev = cash + card + remit
        total_hrs = k_hours + f_hours
        productivity = total_rev / total_hrs if total_hrs > 0 else 0
        labor_ratio = (total_hrs * avg_rate) / total_rev if total_rev > 0 else 0
        
        if st.button("提交報表並產生 LINE 摘要", type="primary", use_container_width=True):
            sheet = get_report_sheet()
            
            # 確保輸入雲端的資料順序與 SHEET_COLUMNS 完全一致
            new_row = [
                str(date), department, cash, card, remit, rev_memo,
                total_rev, customers, (total_rev/customers if customers > 0 else 0),
                k_hours, f_hours, total_hrs, avg_rate, productivity, f"{labor_ratio*100:.1f}%",
                ops_note, tags_str, reason_action, comp_status, announcement
            ]
            sheet.append_row(new_row)
            st.cache_data.clear()
            
            st.success("數據已成功同步雲端！")
            line_summary = f"""【IKKON 營運日報】
日期：{date} | 部門：{department}
--------------------
今日總營收：${total_rev:,.0f}
(現金:{cash:,.0f} / 刷卡:{card:,.0f} / 匯款:{remit:,.0f})
總來客數：{customers} | 客單價：${(total_rev/customers if customers > 0 else 0):,.0f}
--------------------
總工時：{total_hrs} hr
工時產值：${productivity:,.0f}/hr
人事成本佔比：{labor_ratio*100:.1f}%
--------------------
營運回報：
{ops_note}

事項宣達：
{announcement}

客訴處理 ({tags_str})：
{reason_action}
狀態：{comp_status}
--------------------
(本訊息由 IKKON 管理系統自動生成)"""
            st.code(line_summary, language="text")

    # 2. 月度損益彙總
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
            
            # 指標計算
            filtered_df['總營業額'] = pd.to_numeric(filtered_df['總營業額'], errors='coerce').fillna(0)
            m_rev = filtered_df['總營業額'].sum()
            m_hrs = pd.to_numeric(filtered_df['總工時'], errors='coerce').sum()
            m_cost = (pd.to_numeric(filtered_df['總工時']) * pd.to_numeric(filtered_df['平均時薪'])).sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("當月總營收", f"${m_rev:,.0f}")
            c2.metric("預估人事支出", f"${m_cost:,.0f}")
            c3.metric("平均工時產值", f"${m_rev/m_hrs:,.0f}/hr" if m_hrs > 0 else "0")
            
            # 視覺化圖表
            chart_data = filtered_df.groupby('部門')['總營業額'].sum().reset_index()
            bar_chart = alt.Chart(chart_data).mark_bar(size=40, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X('部門:N', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('總營業額:Q', title='營收金額'),
                color=alt.value("#4C78A8")
            ).properties(height=350)
            st.altair_chart(bar_chart, use_container_width=True)
            
            # 明細數據
            st.subheader("當月明細數據")
            # 這裡的欄位名稱已確保存在於 Google Sheets 中
            display_cols = ['日期', '部門', '總營業額', '客單價', '人事成本占比', '營運回報', '事項宣達', '客訴分類標籤']
            
            # 過濾掉不存在的欄位，作為雙重保險
            valid_cols = [col for col in display_cols if col in filtered_df.columns]
            st.dataframe(filtered_df[valid_cols], use_container_width=True)
        else:
            st.info("目前尚無數據。")
