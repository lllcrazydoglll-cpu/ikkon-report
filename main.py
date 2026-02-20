import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd
import altair as alt

# 頁面配置
st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

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

# 試算表 ID
SID = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"

# 效能優化：快取機制
@st.cache_data(ttl=600)
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

# 登入介面
def login_ui(user_df):
    if st.session_state.get("logged_in"):
        return True
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
                        "logged_in": True, 
                        "user_role": user_info['權限等級'], 
                        "user_name": user_info['帳號名稱'],
                        "dept_access": user_info['負責部門']
                    })
                    st.rerun()
            st.error("帳號或密碼錯誤")
    return False

# --- 主程式 ---
user_df, settings_df, report_data = load_all_data()

if login_ui(user_df):
    TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
    HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))

    with st.sidebar:
        st.title(f"👤 {st.session_state['user_name']}")
        menu_options = ["數據錄入", "月度損益彙總"]
        if st.session_state['user_name'] == "管理員":
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
        
        col1, col2 = st.columns(2)
        with col1:
            cash = st.number_input("現金收入", min_value=0, step=100)
            card = st.number_input("刷卡收入", min_value=0, step=100)
            remit = st.number_input("匯款收入", min_value=0, step=100)
        with col2:
            customers = st.number_input("總來客數", min_value=1, step=1)
            k_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
            f_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)
        
        total_rev = cash + card + remit
        total_hrs = k_hours + f_hours
        productivity = total_rev / total_hrs if total_hrs > 0 else 0
        labor_ratio = (total_hrs * avg_rate) / total_rev if total_rev > 0 else 0
        
        if st.button("確認提交並產生報表摘要", type="primary", use_container_width=True):
            sheet = get_report_sheet()
            new_row = [str(date), department, cash, card, remit, "無", total_rev, customers, (total_rev/customers if customers > 0 else 0), k_hours, f_hours, total_hrs, avg_rate, productivity, labor_ratio, "無", "無", "無", "已處理", "無"]
            sheet.append_row(new_row)
            st.cache_data.clear()
            
            # --- 恢復功能：LINE 彙總與截圖區 ---
            st.divider()
            st.success("數據已同步雲端！請複製下方文字或截圖至 LINE 群組。")
            
            line_summary = f"""【IKKON 營運日報】
日期：{date}
部門：{department}
--------------------
今日總營收：${total_rev:,.0f}
(現金:{cash:,.0f} / 刷卡:{card:,.0f} / 匯款:{remit:,.0f})
總來客數：{customers}
客單價：${(total_rev/customers if customers > 0 else 0):,.0f}
--------------------
總工時：{total_hrs} hr
工時產值：${productivity:,.0f}/hr
人事成本佔比：{labor_ratio*100:.1f}%
--------------------"""
            st.code(line_summary, language="text") # 點擊右上角即可複製文字

    # 2. 月度損益彙總
    elif mode == "月度損益彙總":
        st.title("📊 月度財務彙總分析")
        raw_df = pd.DataFrame(report_data)
        if not raw_df.empty:
            raw_df['總營業額'] = pd.to_numeric(raw_df['總營業額'], errors='coerce').fillna(0)
            raw_df['總工時'] = pd.to_numeric(raw_df['總工時'], errors='coerce').fillna(0)
            raw_df['平均時薪'] = pd.to_numeric(raw_df['平均時薪'], errors='coerce').fillna(0)
            raw_df['日期'] = pd.to_datetime(raw_df['日期'])
            
            if st.session_state['dept_access'] != "ALL":
                raw_df = raw_df[raw_df['部門'] == st.session_state['dept_access']]
            
            month_list = sorted(raw_df['日期'].dt.strftime('%Y-%m').unique(), reverse=True)
            target_month = st.selectbox("選擇月份", month_list)
            filtered_df = raw_df[raw_df['日期'].dt.strftime('%Y-%m') == target_month].copy()
            
            # 指標卡
            m_rev = filtered_df['總營業額'].sum()
            m_hrs = filtered_df['總工時'].sum()
            m_cost = (filtered_df['總工時'] * filtered_df['平均時薪']).sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("當月總營收", f"${m_rev:,.0f}")
            c2.metric("預估人事支出", f"${m_cost:,.0f}")
            c3.metric("平均工時產值", f"${m_rev/m_hrs:,.0f}/hr" if m_hrs > 0 else "0")
            
            # 專業質感圖表
            chart_data = filtered_df.groupby('部門')['總營業額'].sum().reset_index()
            bar_chart = alt.Chart(chart_data).mark_bar(size=40, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X('部門:N', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('總營業額:Q', title='營收金額'),
                color=alt.value("#4C78A8")
            ).properties(height=350)
            st.altair_chart(bar_chart, use_container_width=True)
            
            # 明細數據
            st.subheader("當月明細數據")
            main_columns = ['日期', '部門', '總營業額', '客單價', '工時產值', '人事成本占比']
            st.dataframe(filtered_df[main_columns], use_container_width=True)
        else:
            st.info("目前尚無數據。")
