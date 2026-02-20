import streamlit as st
import datetime
import pandas as pd
from database import DatabaseManager

st.set_page_config(page_title="IKKON 採購與叫貨系統", layout="wide")

# 這裡共用你原本的 Google Sheets ID 與 DatabaseManager
SID = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"
db = DatabaseManager(SID, st.secrets)

@st.cache_data(ttl=300)
def load_procurement_data():
    if not db.client: return None, None
    try:
        sh = db.client.open_by_key(SID)
        user_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
        # 假設你有一個 Vendors 工作表來管理廠商與預設品項，初期也可先用手動輸入
        # vendor_df = pd.DataFrame(sh.worksheet("Vendors").get_all_records())
        return user_df, None
    except Exception as e:
        st.error(f"資料讀取錯誤：{e}")
        return None, None

user_df, vendor_df = load_procurement_data()

# 簡化的登入邏輯 (共用原本的 Users 資料表)
def login_ui():
    if st.session_state.get("logged_in"): return True
    st.title("IKKON 內場叫貨系統登入")
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
                        "user_name": user_info['帳號名稱'], 
                        "dept_access": user_info['負責部門']
                    })
                    st.rerun()
            st.error("帳號或密碼錯誤")
    return False

if login_ui():
    with st.sidebar:
        st.title(f"叫貨人：{st.session_state['user_name']}")
        if st.button("安全登出"):
            st.session_state.clear()
            st.rerun()

    st.title("建立採購叫貨單")
    
    # 部門選擇防呆 (若為店長或主廚，只能選自己的店)
    dept = st.session_state['dept_access']
    if dept == "ALL":
        department = st.selectbox("選擇叫貨分店", ["桃園鍋物", "桃園燒肉", "和牛會所"])
    else:
        department = dept
        st.info(f"當前叫貨分店：{department}")

    date = st.date_input("叫貨日期", datetime.date.today())
    
    st.subheader("廠商與品項輸入")
    c1, c2 = st.columns(2)
    with c1:
        vendor = st.text_input("廠商名稱 (例如：美福肉品、信功豬肉)")
        item_name = st.text_input("叫貨品項 (例如：A5和牛肋眼、伊比利豬梅花)")
    with c2:
        unit_price = st.number_input("預估單價 (系統計算成本用)", min_value=0, step=10)
        quantity = st.number_input("叫貨數量", min_value=0.0, step=1.0)
    
    total_cost = unit_price * quantity
    st.metric("此品項預估總價", f"${total_cost:,.0f}")

    if st.button("新增至今日叫貨清單", type="primary"):
        if vendor and item_name and quantity > 0:
            new_order = [
                str(date), department, vendor, item_name, 
                unit_price, quantity, total_cost, st.session_state['user_name'], "已叫貨"
            ]
            
            # 使用我們強大的 DatabaseManager 寫入新的 Procurement 工作表
            try:
                sh = db.client.open_by_key(SID)
                sheet = sh.worksheet("Procurement")
                sheet.append_row(new_order)
                st.success(f"{item_name} 已成功加入叫貨清單！")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"寫入失敗：{e}")
        else:
            st.warning("請填寫完整的廠商、品項與數量。")

    st.divider()
    st.markdown("### 叫貨單預覽與發送")
    st.caption("未來可在此處新增一鍵複製文字或自動發送 Line 給廠商的功能，提升內場工作效率。")
