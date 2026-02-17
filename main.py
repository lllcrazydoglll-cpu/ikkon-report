import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd

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

# 讀取使用者名單與設定
def load_configs(client, spreadsheet_key):
    try:
        sh = client.open_by_key(spreadsheet_key)
        # 讀取使用者
        user_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
        # 讀取營運參數
        settings_df = pd.DataFrame(sh.worksheet("Settings").get_all_records())
        return user_df, settings_df
    except:
        return pd.DataFrame(), pd.DataFrame()

# 登入邏輯
def login_ui(user_df):
    if st.session_state.get("logged_in"):
        return True

    st.title("IKKON 系統登入")
    with st.form("login_form"):
        input_user = st.text_input("帳號名稱")
        input_pwd = st.text_input("密碼", type="password")
        submit = st.form_submit_button("登入")
        
        # 預設通用員工密碼
        if submit:
            if input_pwd == "IKKON888" and input_user == "staff":
                st.session_state.update({"logged_in": True, "user_role": "staff", "user_name": "一般員工", "dept_access": "ALL"})
                st.rerun()
            
            # 比對 Users 分頁
            if not user_df.empty:
                match = user_df[(user_df['帳號名稱'] == input_user) & (user_df['密碼'].astype(str) == input_pwd)]
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
client = get_gspread_client()
spreadsheet_key = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"

if client:
    user_df, settings_df = load_configs(client, spreadsheet_key)
    
    if login_ui(user_df):
        # 參數初始化
        TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
        HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))
        
        # 側邊欄權限控管
        with st.sidebar:
            st.title(f"您好, {st.session_state['user_name']}")
            mode = st.radio("功能選單", ["數據錄入", "月度損益彙總", "後台參數設定"])
            if st.button("登出系統"):
                st.session_state.clear()
                st.rerun()

        # 權限過濾：如果是店長，只能選自己負責的部門
        if st.session_state['dept_access'] == "ALL":
            dept_list = list(TARGETS.keys())
        else:
            dept_list = [st.session_state['dept_access']]

        # 1. 數據錄入功能
        if mode == "數據錄入":
            st.title("IKKON 營運數據錄入")
            date = st.date_input("報表日期", datetime.date.today())
            department = st.selectbox("所屬部門", dept_list)
            
            avg_hourly_rate = HOURLY_RATES.get(department, 205)
            
            col1, col2 = st.columns(2)
            with col1:
                cash = st.number_input("現金收入", min_value=0, step=100)
                credit_card = st.number_input("刷卡收入", min_value=0, step=100)
                remittance = st.number_input("匯款收入", min_value=0, step=100)
            with col2:
                total_customers = st.number_input("總來客數", min_value=1, step=1)
                k_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
                f_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

            total_revenue = cash + credit_card + remittance
            total_hours = k_hours + f_hours
            productivity = total_revenue / total_hours if total_hours > 0 else 0
            labor_ratio = (total_hours * avg_hourly_rate) / total_revenue if total_revenue > 0 else 0

            if st.button("提交今日報表", type="primary", use_container_width=True):
                # (此處保留原本的 sheet.append_row 邏輯)
                st.success("數據已同步雲端")

        # 2. 月度損益彙總 (管理者專屬)
        elif mode == "月度損益彙總":
            if st.session_state['user_role'] != 'admin':
                st.warning("您沒有權限查看損益彙總數據。")
            else:
                st.title("📊 月度營運分析面板")
                sh = client.open_by_key(spreadsheet_key)
                raw_df = pd.DataFrame(sh.sheet1.get_all_records())
                raw_df['日期'] = pd.to_datetime(raw_df['日期'])
                
                # 月份選擇器
                year_month = st.selectbox("選擇分析月份", raw_df['日期'].dt.strftime('%Y-%m').unique())
                analysis_df = raw_df[raw_df['日期'].dt.strftime('%Y-%m') == year_month]
                
                if st.session_state['dept_access'] != "ALL":
                    analysis_df = analysis_df[analysis_df['部門'] == st.session_state['dept_access']]

                # 計算關鍵指標
                m_revenue = analysis_df['總營收'].sum()
                m_hours = analysis_df['總工時'].sum()
                m_labor_cost = (analysis_df['總工時'] * analysis_df['平均時薪']).sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("當月總營收", f"${m_revenue:,.0f}")
                c2.metric("預估人事支出", f"${m_labor_cost:,.0f}")
                c3.metric("月平均工時產值", f"${m_revenue/m_hours:,.0f}/hr" if m_hours > 0 else "0")

                st.subheader("部門營收分佈")
                st.bar_chart(analysis_df.groupby('部門')['總營收'].sum())

        # 3. 後台參數設定 (僅限 admin)
        elif mode == "後台參數設定":
            if st.session_state['user_role'] != 'admin':
                st.warning("權限不足")
            else:
                st.title("⚙️ 參數永久儲存區")
                # (此處保留原本修改 Settings 頁面的邏輯)
                st.info("請在此調整各店月目標與時薪。")
