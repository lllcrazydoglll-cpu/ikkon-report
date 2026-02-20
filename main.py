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

# 試算表 ID
SID = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"

# 載入所有配置
def load_all_data(client):
    try:
        sh = client.open_by_key(SID)
        user_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
        settings_df = pd.DataFrame(sh.worksheet("Settings").get_all_records())
        report_sheet = sh.worksheet("Sheet1")
        return user_df, settings_df, report_sheet
    except Exception as e:
        st.error(f"讀取分頁失敗，請確認分頁名稱為 Sheet1, Settings, Users。錯誤：{e}")
        return None, None, None

# 登入介面
def login_ui(user_df):
    if st.session_state.get("logged_in"):
        return True

    st.title("IKKON 系統管理登入")
    with st.form("login_form"):
        input_user = st.text_input("帳號名稱")
        input_pwd = st.text_input("密碼", type="password")
        submit = st.form_submit_button("登入")
        
        if submit:
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

# --- 主程式執行區 ---
client = get_gspread_client()

if client:
    user_df, settings_df, report_sheet = load_all_data(client)
    
    if login_ui(user_df):
        # 初始化參數
        TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
        HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))

        with st.sidebar:
            st.title(f"您好，{st.session_state['user_name']}")
            
            # --- 權限控管選單 ---
            menu_options = ["數據錄入", "月度損益彙總"]
            # 只有「管理員」帳號可以看到後台參數設定
            if st.session_state['user_name'] == "管理員":
                menu_options.append("後台參數設定")
                
            mode = st.radio("功能選單", menu_options)
            
            st.divider()
            if st.button("安全登出"):
                st.session_state.clear()
                st.rerun()

        # 1. 數據錄入功能
        if mode == "數據錄入":
            st.title("IKKON 營運數據錄入")
            
            if st.session_state['dept_access'] == "ALL":
                dept_options = list(TARGETS.keys())
            else:
                dept_options = [st.session_state['dept_access']]
            
            department = st.selectbox("所屬部門", dept_options)
            date = st.date_input("報表日期", datetime.date.today())
            avg_rate = HOURLY_RATES.get(department, 205)
            
            st.subheader("財務與工時錄入")
            col1, col2 = st.columns(2)
            with col1:
                cash = st.number_input("現金收入", min_value=0, step=100)
                card = st.number_input("刷卡收入", min_value=0, step=100)
                remit = st.number_input("匯款收入", min_value=0, step=100)
            with col2:
                customers = st.number_input("總來客數", min_value=1, step=1)
                k_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
                f_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)
            
            memo = st.text_area("金額備註", "無")
            
            # 計算數據
            total_rev = cash + card + remit
            total_hrs = k_hours + f_hours
            
            if st.button("提交今日報表", type="primary", use_container_width=True):
                # 這裡的欄位順序必須完全對應您 Sheet1 的 A 到 T 欄
                new_row = [
                    str(date), department, cash, card, remit, memo, 
                    total_rev, customers, (total_rev/customers if customers > 0 else 0),
                    k_hours, f_hours, total_hrs, avg_rate, 
                    (total_rev/total_hrs if total_hrs > 0 else 0),
                    ((total_hrs * avg_rate)/total_rev if total_rev > 0 else 0),
                    "無", "無", "無", "已處理", "無" # 補齊後續營運回報與客訴欄位
                ]
                report_sheet.append_row(new_row)
                st.success(f"{department} {date} 數據已成功存入雲端！")

        # 2. 月度損益彙總
        elif mode == "月度損益彙總":
            st.title("📊 月度財務彙總分析")
            raw_df = pd.DataFrame(report_sheet.get_all_records())
            
            if not raw_df.empty:
                # 關鍵修正：將欄位名稱與試算表同步
                # 將「總營業額」轉為數值處理
                raw_df['總營業額'] = pd.to_numeric(raw_df['總營業額'], errors='coerce').fillna(0)
                raw_df['總工時'] = pd.to_numeric(raw_df['總工時'], errors='coerce').fillna(0)
                raw_df['平均時薪'] = pd.to_numeric(raw_df['平均時薪'], errors='coerce').fillna(0)
                raw_df['日期'] = pd.to_datetime(raw_df['日期'])
                
                month_list = raw_df['日期'].dt.strftime('%Y-%m').unique()
                target_month = st.selectbox("選擇月份", month_list)
                
                filtered_df = raw_df[raw_df['日期'].dt.strftime('%Y-%m') == target_month]
                
                # 計算指標 (修正為「總營業額」)
                m_rev = filtered_df['總營業額'].sum()
                m_hrs = filtered_df['總工時'].sum()
                m_cost = (filtered_df['總工時'] * filtered_df['平均時薪']).sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("當月總營收", f"${m_rev:,.0f}")
                c2.metric("預估人事支出", f"${m_cost:,.0f}")
                c3.metric("平均工時產值", f"${m_rev/m_hrs:,.0f}/hr" if m_hrs > 0 else "0")
                
                st.subheader("部門營收分佈")
                st.bar_chart(filtered_df.groupby('部門')['總營業額'].sum())
                
                st.subheader("當月明細數據")
                st.dataframe(filtered_df)
            else:
                st.info("目前尚無數據。")

        # 3. 後台參數設定 (僅限「管理員」)
        elif mode == "後台參數設定":
            st.title("⚙️ 營運參數設定")
            st.write("目前系統連結之雲端 ID:", SID)
            st.dataframe(settings_df)
            st.info("如需修改月目標或時薪，請直接開啟 Google Sheets 的『Settings』分頁修改。")
