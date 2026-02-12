import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pandas as pd
from PIL import Image, ImageDraw, ImageFont # 用於生成截圖圖片
import io

# 1. 密碼保護功能
def check_password():
    def password_entered():
        if st.session_state["password"] == "IKKON888": # 你可以在此修改統一密碼
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("請輸入店鋪管理密碼", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("密碼錯誤，請重新輸入", type="password", on_change=password_entered, key="password")
        st.error("😕 密碼不正確")
        return False
    else:
        return True

# 2. 認證邏輯 (改用 Streamlit Secrets)
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # 從 Streamlit Secrets 讀取內容
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"認證失敗，請檢查 Secrets 設定：{e}")
        return None

# 3. 生成截圖圖片功能
def generate_report_image(date, dept, revenue, hours, prod, ratio, note):
    # 創建一張簡單的白底圖片
    img = Image.new('RGB', (600, 800), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # 這裡簡單模擬文字排版 (實際部署時建議上傳一個中文字體檔以防亂碼)
    content = f"""
    IKKON 日回報摘要
    ------------------
    日期: {date}
    部門: {dept}
    
    總營業額: {revenue:,} 元
    總工時: {hours} 小時
    工時產值: {int(prod):,} 元/時
    人事成本比: {ratio}
    
    營運回報:
    {note[:100]}...
    ------------------
    (長按圖片儲存並傳至LINE)
    """
    d.text((50, 50), content, fill=(0, 0, 0))
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 主程式開始 ---
if check_password():
    
    # 經營參數設定
    TARGETS = {"桃園鍋物": 2000000, "桃園燒肉": 2000000, "台中和牛會所": 2000000}
    HOURLY_RATES = {"桃園鍋物": 290, "桃園燒肉": 270, "台中和牛會所": 270}

    st.set_page_config(page_title="IKKON 日回報系統", layout="wide")
    st.title("IKKON 日回報系統")

    # 1. 基礎資訊
    col_head1, col_head2 = st.columns(2)
    with col_head1:
        date = st.date_input("報表日期", datetime.date.today())
    with col_head2:
        department = st.selectbox("部門", list(TARGETS.keys()))

    avg_hourly_rate = HOURLY_RATES[department]

    st.divider()

    # 🚀 數據統計看板
    client = get_gspread_client()
    if client:
        try:
            sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
            all_values = sheet.get_all_values()
            
            if len(all_values) > 1:
                df = pd.DataFrame(all_values[1:], columns=all_values[0])
                df['日期'] = pd.to_datetime(df['日期'])
                m_df = df[(df['部門'] == department) & (df['日期'].dt.month == date.month) & (df['日期'].dt.year == date.year)]
                
                if not m_df.empty:
                    for col in ['總營業額', '工時產值', '平均時薪', '總工時']:
                        m_df[col] = pd.to_numeric(m_df[col].astype(str).str.replace(',', ''), errors='coerce')

                    mtd_rev = m_df['總營業額'].sum()
                    achieve = mtd_rev / TARGETS[department] if TARGETS[department] > 0 else 0
                    avg_prod = m_df['工時產值'].mean()
                    total_labor_cost = (m_df['平均時薪'] * m_df['總工時']).sum()
                    avg_labor_ratio = total_labor_cost / mtd_rev if mtd_rev > 0 else 0

                    st.subheader(f"{department} {date.month}月 營運狀況")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("月累計營收", f"{int(mtd_rev):,} 元", f"{achieve:.1%} 達成")
                    m2.metric("目標達成率", f"{achieve:.1%}")
                    m3.metric("月平均產值", f"{int(avg_prod):,} 元/小時")
                    m4.metric("月人事成本比", f"{avg_labor_ratio:.1%}")
                    st.progress(min(achieve, 1.0))
        except:
            st.warning("數據讀取中...")

    st.divider()

    # 2. 數據輸入與計算
    st.subheader("當日營運數據")
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

    total_revenue = cash + credit_card + remittance
    total_hours = k_hours + f_hours
    productivity = total_revenue / total_hours if total_hours > 0 else 0
    labor_cost_ratio = (total_hours * avg_hourly_rate) / total_revenue if total_revenue > 0 else 0
    avg_spend = total_revenue / total_customers if total_customers > 0 else 0

    st.markdown(f"**今日營收：{total_revenue:,} 元 | 產值：{int(productivity):,} 元/時 | 人事比：{labor_cost_ratio:.1%}**")

    st.divider()

    # 3. 報告區
    ops_note = st.text_area("營運回報")
    tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
    reason = st.text_area("詳細原因")
    action = st.text_area("處理結果")

    # 4. 提交與生成圖卡
    col_btn1, col_btn2 = st.columns(2)
    
    if col_btn1.button("確認提交日報表", type="primary", use_container_width=True):
        if client:
            sheet = client.open_by_key("16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08").sheet1
            new_row = [str(date), department, cash, credit_card, remittance, amount_note, total_revenue, total_customers, round(avg_spend, 1), k_hours, f_hours, total_hours, avg_hourly_rate, round(productivity, 1), f"{labor_cost_ratio:.1%}", ops_note, ", ".join(tags), reason, action]
            
            # 覆蓋邏輯
            all_data = sheet.get_all_values()
            target_row = -1
            for i, row in enumerate(all_data[1:], start=2):
                if row[0] == str(date) and row[1] == department:
                    target_row = i
                    break
            
            if target_row != -1:
                sheet.update(f"A{target_row}:S{target_row}", [new_row])
                st.success("✅ 已更新紀錄！")
            else:
                sheet.append_row(new_row)
                st.success("✅ 已新增紀錄！")
            st.rerun()

    # 截圖按鈕功能：生成摘要文字，方便員工直接截圖手機螢幕
    if col_btn2.button("生成截圖摘要", use_container_width=True):
        st.info("💡 請對下方區域進行手機截圖，並傳至 LINE 群組")
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 2px solid #464e5f;">
            <h2 style="color: #1f77b4; margin-top:0;">IKKON 日報摘要 ({date})</h2>
            <p><b>部門：</b>{department}</p>
            <hr>
            <p><b>今日總營收：</b> {total_revenue:,} 元</p>
            <p><b>工時產值：</b> {int(productivity):,} 元/小時</p>
            <p><b>人事成本比：</b> {labor_cost_ratio:.1%}</p>
            <p><b>總來客數：</b> {total_customers} 位</p>
            <hr>
            <p><b>營運回報：</b><br>{ops_note}</p>
        </div>
        """, unsafe_allow_html=True)
