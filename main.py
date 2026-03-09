import streamlit as st
import datetime
import pandas as pd
import altair as alt
import os
import io
import urllib.request
import textwrap
from PIL import Image, ImageDraw, ImageFont
from database import DatabaseManager

st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

SHEET_COLUMNS = [
    "日期", "部門", "現金", "刷卡", "匯款", "訂金收入", "沒收訂金", "現金折價卷", "金額備註",
    "總營業額", "月營業額", "目標占比", "總來客數", "客單價", 
    "內場工時", "外場工時", "總工時", "平均時薪", "工時產值", "人事成本占比",
    "昨日剩", "今日支出", "今日補", "今日剰", 
    "IKKON折抵券", "1000折價券", "總共折抵金",
    "85折使用者", "85折對象", 
    "營運回報", "客訴分類標籤", "客訴原因與處理結果", "事項宣達"
]

SID = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"

class EnhancedDatabaseManager(DatabaseManager):
    def upsert_report(self, sheet_name, date_str, department, new_row):
        if not self.client: return False, "連線失敗"
        try:
            sh = self.client.open_by_key(self.sid)
            sheet = sh.worksheet(sheet_name)
            all_values = sheet.get_all_values()
            target_row_idx = None
            
            for i, row in enumerate(all_values):
                if i == 0: continue
                if sheet_name == "WeeklyReports":
                    author = new_row[-1] 
                    if len(row) >= 12 and row[0] == date_str and row[1] == department and str(row[11]).strip() == str(author).strip():
                        target_row_idx = i + 1
                        break
                else:
                    if len(row) >= 2 and row[0] == date_str and row[1] == department:
                        target_row_idx = i + 1
                        break
            
            if target_row_idx:
                def get_col_letter(col_idx):
                    letter = ''
                    while col_idx > 0:
                        col_idx, remainder = divmod(col_idx - 1, 26)
                        letter = chr(65 + remainder) + letter
                    return letter
                
                end_col = get_col_letter(len(new_row))
                cell_list = sheet.range(f"A{target_row_idx}:{end_col}{target_row_idx}")
                
                for j, cell in enumerate(cell_list):
                    if j < len(new_row):
                        cell.value = new_row[j]
                sheet.update_cells(cell_list)
                return True, "updated"
            else:
                sheet.append_row(new_row)
                return True, "inserted"
        except Exception as e:
            return False, str(e)

db = EnhancedDatabaseManager(SID, st.secrets)

@st.cache_data(ttl=300)
def load_cached_data():
    return db.get_all_data()

user_df, settings_df, report_data = load_cached_data()

if user_df is None and settings_df is None:
    st.error("系統初始化失敗：無法連接至核心資料庫，請檢查網路連線或授權設定。")
    st.stop()

@st.cache_resource
def get_chinese_font():
    font_path = "NotoSansCJKtc-Regular.otf"
    if not os.path.exists(font_path):
        try:
            url = "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            return None
    try:
        return ImageFont.truetype(font_path, 28)
    except:
        return None

def get_wrapped_lines(text, max_chars=21):
    if not text:
        return ["無"]
    lines = []
    for paragraph in text.split('\n'):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > max_chars:
            lines.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if paragraph:
            lines.append(paragraph)
    if not lines:
        return ["無"]
    return lines

def render_image(content_lines, theme_color=(180, 50, 50)):
    font = get_chinese_font()
    if font is None:
        font = ImageFont.load_default()

    img_height = len(content_lines) * 45 + 80
    img = Image.new('RGB', (650, img_height), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)

    y_text = 40
    for line in content_lines:
        if "【" in line or "[" in line:
            draw.text((40, y_text), line, font=font, fill=theme_color) 
        else:
            draw.text((40, y_text), line, font=font, fill=(40, 40, 40))  
        y_text += 45

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

def generate_finance_image(date, dept, month_rev, month_cust, month_spend, ratio, 
                           today_rev, today_cust, today_spend, 
                           cash, card, remit, deposit, forfeit, cash_coupon, 
                           petty_y, petty_e, petty_r, petty_t, ikkon_cp, th_cp, tot_cp, emp_display_str):
    lines = [
        "【 IKKON 財務日報 】",
        f"日期：{date} | 分店：{dept}",
        "--------------------------------------",
        "[ 營收指標 ]",
        f"總營業額：${month_rev:,.0f} | 總來客數：{int(month_cust)} 人",
        f"平均客單價：${month_spend:,.0f}",
        f"目標占比：{ratio*100:.1f}%",
        "",
        f"今日營收：${today_rev:,.0f} | 今日來客數：{int(today_cust)} 人",
        f"今日客單價：${today_spend:,.0f}",
        "",
        "[ 支付結構 ]",
        f"現金：${cash:,.0f} | 刷卡：${card:,.0f}",
        f"匯款：${remit:,.0f} | 訂金：${deposit:,.0f}",
        f"沒收：${forfeit:,.0f} | 現金券：${cash_coupon:,.0f}",
        "",
        "[ 零用金結算 ]",
        f"昨日剩餘：${petty_y:,.0f} | 今日支出：${petty_e:,.0f}",
        f"今日補充：${petty_r:,.0f} | 今日剰餘：${petty_t:,.0f}",
        "",
        "[ 行銷與折扣 ]",
        f"IKKON券：${ikkon_cp:,.0f} | 1000折價：${th_cp:,.0f}",
        f"總折抵金：${tot_cp:,.0f}",
    ]
    lines.extend(get_wrapped_lines(f"員工85折：{emp_display_str}"))
    return render_image(lines)

def generate_ops_image(date, dept, prod, labor, k_hours, f_hours, ops_note, announce, tags_str, reason_action):
    lines = [
        "【 IKKON 營運日報 】",
        f"日期：{date} | 分店：{dept}",
        "--------------------------------------",
        "[ 營運指標 ]",
        f"工時產值：${prod:,.0f}/hr | 人事占比：{labor*100:.1f}%",
        f"內場工時：{k_hours} hr | 外場工時：{f_hours} hr",
        "",
        "[ 營運狀況回報 ]"
    ]
    lines.extend(get_wrapped_lines(ops_note))
    lines.extend(["", "[ 事項宣達 ]"])
    lines.extend(get_wrapped_lines(announce))
    lines.extend(["", f"[ 客訴處理 ({tags_str}) ]"])
    lines.extend(get_wrapped_lines(reason_action))
    
    return render_image(lines)

def generate_weekly_image(date, dept, start_d, end_d, rev, spend, prod, review, hr_status, market, act1, act2, act3, author):
    lines = [
        "【 IKKON 值班主管週報 】",
        f"回報日：{date} | 分店：{dept}",
        f"統計區間：{start_d} 至 {end_d}",
        "--------------------------------------",
        "[ 本週核心數據 ]",
        f"本週總營收：${rev:,.0f}",
        f"平均客單價：${spend:,.0f} | 平均工時產值：${prod:,.0f}/hr",
        "",
        "[ 數據與營運檢討 ]"
    ]
    lines.extend(get_wrapped_lines(review))
    lines.extend(["", "[ 團隊與人事狀況 ]"])
    lines.extend(get_wrapped_lines(hr_status))
    lines.extend(["", "[ 行銷觀察與改善建議 ]"])
    lines.extend(get_wrapped_lines(market))
    lines.extend(["", "[ 下週行動方針 ]"])
    
    def append_action(prefix_num, text):
        w_lines = get_wrapped_lines(text, max_chars=18) 
        lines.append(f"{prefix_num}. {w_lines[0]}")
        for wl in w_lines[1:]:
            lines.append(f"   {wl}") 
            
    append_action(1, act1)
    append_action(2, act2)
    append_action(3, act3)
    
    lines.extend(["", "--------------------------------------", f"填寫人：{author}"])
    return render_image(lines, theme_color=(30, 80, 140))

def login_ui(user_df):
    if st.session_state.get("logged_in"): return True
    st.title("IKKON 系統管理登入")
    
    with st.form("login_form"):
        input_user = st.text_input("帳號名稱")
        input_pwd = st.text_input("密碼", type="password")
        if st.form_submit_button("登入"):
            if user_df is not None and not user_df.empty:
                user_df.columns = user_df.columns.astype(str).str.strip()
                
                if '帳號名稱' in user_df.columns and '密碼' in user_df.columns:
                    user_df['帳號名稱_clean'] = user_df['帳號名稱'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    user_df['密碼_clean'] = user_df['密碼'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    
                    input_user_clean = str(input_user).strip()
                    input_pwd_clean = str(input_pwd).strip()
                    
                    match = user_df[(user_df['帳號名稱_clean'] == input_user_clean) & (user_df['密碼_clean'] == input_pwd_clean)]
                    if not match.empty:
                        user_info = match.iloc[0]
                        safe_role = str(user_info.get('權限等級', 'staff')).strip().lower()
                        safe_dept = str(user_info.get('負責部門', '')).strip()
                        
                        st.session_state.update({
                            "logged_in": True, 
                            "user_role": safe_role, 
                            "user_name": str(user_info['帳號名稱']).strip(), 
                            "dept_access": safe_dept
                        })
                        st.rerun()
                    else:
                        st.error("帳號或密碼錯誤。請注意大小寫，並確保無輸入多餘空白。")
                else:
                    st.error("資料庫格式錯誤：找不到『帳號名稱』或『密碼』欄位，請檢查 Google Sheets 標題。")
            else:
                st.error("系統未能讀取到任何帳號資料。")
                
    st.write("")
    if st.button("🔄 無法登入？點此刷新系統資料", use_container_width=True):
        st.cache_data.clear()
        st.success("資料已重新從 Google Sheets 抓取！請再次嘗試登入。")
        st.rerun()
        
    return False

if login_ui(user_df):
    TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
    HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))
    
    user_role = st.session_state.get("user_role").lower()
    
    if user_role == "admin":
        menu_options = ["營運數據登記", "值班主管週報", "月度損益彙總", "系統後台管理"]
    elif user_role == "ceo":
        menu_options = ["月度損益彙總"]
    elif user_role == "manager":
        menu_options = ["營運數據登記", "值班主管週報", "月度損益彙總"]
    else: 
        menu_options = ["營運數據登記", "月度損益彙總"]

    with st.sidebar:
        st.title(f"{st.session_state['user_name']}")
        st.caption(f"權限等級：{user_role.upper()}")
        
        mode = st.radio("功能選單", menu_options)
        
        if st.button("刷新數據"):
            st.cache_data.clear()
            st.rerun()
        if st.button("安全登出"):
            st.session_state.clear()
            st.rerun()

    if mode == "系統後台管理":
        st.title("系統後台管理")
        st.info("此區塊修改將直接覆寫核心資料庫。新增分店、修改目標或新增員工帳號皆在此完成。")
        
        tab_users, tab_settings = st.tabs(["帳號與權限管理", "分店營運設定"])
        
        with tab_users:
            st.subheader("使用者名單")
            st.caption("權限等級規範：admin (管理員) / ceo (執行長) / manager (值班主管) / staff (幹部)。")
            edited_users = st.data_editor(user_df, num_rows="dynamic", use_container_width=True, key="user_editor")
            if st.button("儲存帳號設定", type="primary"):
                success, msg = db.update_backend_sheet("Users", edited_users)
                if success:
                    st.success("帳號資料已成功同步至資料庫。")
                    st.cache_data.clear()
                else:
                    st.error(f"寫入失敗：{msg}")

        with tab_settings:
            st.subheader("各分店目標與時薪基準")
            edited_settings = st.data_editor(settings_df, num_rows="dynamic", use_container_width=True, key="setting_editor")
            if st.button("儲存營運設定", type="primary"):
                success, msg = db.update_backend_sheet("Settings", edited_settings)
                if success:
                    st.success("營運設定已成功同步至資料庫。")
                    st.cache_data.clear()
                else:
                    st.error(f"寫入失敗：{msg}")

    elif mode == "營運數據登記":
        st.title("營運數據登記")
        dept_options = list(TARGETS.keys()) if st.session_state['dept_access'] == "ALL" else [st.session_state['dept_access']]
        department = st.selectbox("部門", dept_options)
        date = st.date_input("報表日期", datetime.date.today())
        avg_rate = HOURLY_RATES.get(department, 205)
        month_target = TARGETS.get(department, 1000000)
        
        last_petty_cash = 0
        df_history = pd.DataFrame() 
        if report_data:
            df_history = pd.DataFrame(report_data)
            if not df_history.empty and '今日剰' in df_history.columns:
                df_history['日期'] = pd.to_datetime(df_history['日期'])
                past_history = df_history[(df_history['部門'] == department) & (df_history['日期'] < pd.to_datetime(date))]
                past_history = past_history.sort_values(by='日期', ascending=False)
                if not past_history.empty:
                    last_value = past_history.iloc[0]['今日剰']
                    if pd.notna(last_value) and str(last_value).strip() != "":
                        last_petty_cash = int(float(last_value))

        data_exists_warning = False
        existing_rev_display = 0
        if not df_history.empty and '總營業額' in df_history.columns:
            check_mask = (df_history['部門'] == department) & (df_history['日期'] == pd.to_datetime(date))
            existing_row = df_history.loc[check_mask]
            
            if not existing_row.empty:
                data_exists_warning = True
                try:
                    existing_rev_display = int(pd.to_numeric(existing_row.iloc[0]['總營業額'], errors='coerce'))
                except:
                    existing_rev_display = 0

        st.subheader("營收數據")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            cash = st.number_input("現金收入", min_value=0, step=100)
        with c2:
            card = st.number_input("刷卡收入", min_value=0, step=100)
        with c3:
            remit = st.number_input("匯款收入", min_value=0, step=100)
            
        c4, c5, c6 = st.columns(3)
        with c4:
            deposit = st.number_input("訂金收入", min_value=0, step=100)
        with c5:
            forfeit = st.number_input("沒收訂金", min_value=0, step=100)
        with c6:
            cash_coupon = st.number_input("現金折價卷", min_value=0, step=100)
            
        c_cust, c_memo = st.columns([1, 3])
        with c_cust:
            customers = st.number_input("總來客數", min_value=1, step=1)
        with c_memo:
            rev_memo = st.text_area("金額備註", "無", height=68)

        st.subheader("工時數據")
        t1, t2 = st.columns(2)
        with t1:
            k_hours = st.number_input("內場工時", min_value=0.0, step=0.5)
        with t2:
            f_hours = st.number_input("外場工時", min_value=0.0, step=0.5)

        st.subheader("零用金回報")
        p1, p2, p3 = st.columns(3)
        with p1:
            petty_yesterday = st.number_input(
                "昨日剩 (系統自動帶入)" if user_role != "admin" else "昨日剩 (管理員解鎖模式)", 
                value=last_petty_cash, 
                step=100, 
                disabled=(user_role != "admin")
            )
        with p2:
            petty_expense = st.number_input("今日支出", min_value=0, step=100)
        with p3:
            petty_replenish = st.number_input("今日補", min_value=0, step=100)
        
        petty_today = petty_yesterday - petty_expense + petty_replenish
        st.info(f"今日剰 (自動計算)：${petty_today:,}")

        st.subheader("折價券與員工優惠統計")
        v1, v2 = st.columns(2)
        with v1:
            ikkon_coupon = st.number_input("IKKON折抵券金額", min_value=0, step=100)
        with v2:
            thousand_coupon = st.number_input("1000折價券金額", min_value=0, step=1000)
        
        total_coupon = cash_coupon + ikkon_coupon + thousand_coupon
        st.caption(f"總共折抵金：${total_coupon:,}")

        st.markdown("**員工85折優惠權利 (當日若有多人使用，請依序填寫)**")
        discount_users = []
        discount_targets = []
        discount_displays = []

        for i in range(1, 4):
            e1, e2 = st.columns(2)
            with e1:
                u = st.text_input(f"使用者 {i} (請輸入姓名)", key=f"emp_u_{i}")
            with e2:
                t = st.selectbox(f"對象 {i}", ["無", "熟客", "親友", "好客人", "其他"], key=f"emp_t_{i}")
            
            if u.strip():
                display_t = t if t != "無" else "未指定"
                discount_users.append(u.strip())
                discount_targets.append(display_t)
                discount_displays.append(f"{u.strip()} ({display_t})")

        emp_user_str = "、".join(discount_users) if discount_users else "無"
        emp_target_str = "、".join(discount_targets) if discount_targets else "無"
        emp_display_str = "、".join(discount_displays) if discount_displays else "無"

        st.subheader("營運與客訴回報")
        ops_note = st.text_area("營運狀況回報", height=120)
        announcement = st.text_area("事項宣達", height=80)
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
            tags_str = ", ".join(tags) if tags else "無"
        with col_c2:
            reason_action = st.text_area("原因與處理結果", height=80)

        total_rev = float(cash + card + remit + deposit + forfeit)
        total_hrs = float(k_hours + f_hours)
        productivity = float(total_rev / total_hrs) if total_hrs > 0 else 0.0
        labor_ratio = float((total_hrs * avg_rate) / total_rev) if total_rev > 0 else 0.0
        avg_customer_spend = float(total_rev / customers) if customers > 0 else 0.0

        current_month_rev = total_rev
        current_month_cust = customers
        
        if report_data:
            raw_df = pd.DataFrame(report_data)
            if not raw_df.empty:
                raw_df['日期'] = pd.to_datetime(raw_df['日期'])
                current_month_str = date.strftime('%Y-%m')
                mask = (raw_df['部門'] == department) & (raw_df['日期'].dt.strftime('%Y-%m') == current_month_str) & (raw_df['日期'] < pd.to_datetime(date))
                
                historical_month_rev = float(pd.to_numeric(raw_df.loc[mask, '總營業額'], errors='coerce').fillna(0).sum())
                historical_month_cust = float(pd.to_numeric(raw_df.loc[mask, '總來客數'], errors='coerce').fillna(0).sum())
                
                current_month_rev += historical_month_rev
                current_month_cust += historical_month_cust
        
        target_ratio = float(current_month_rev / month_target) if month_target > 0 else 0.0
        current_month_spend = float(current_month_rev / current_month_cust) if current_month_cust > 0 else 0.0

        submit_clicked = False
        confirm_overwrite = False
        
        if data_exists_warning:
            st.error(f"⚠️ **警告：系統偵測到 {date} {department} 已經有一筆營收 ${existing_rev_display:,} 的資料！**")
            st.caption("若您確定要覆寫舊資料（例如修正錯誤），請勾選下方確認框後再提交。")
            confirm_overwrite = st.checkbox("✅ 我確認要覆蓋當日舊資料")
            
            if st.button("確認覆寫並提交", type="primary", use_container_width=True, disabled=not confirm_overwrite):
                submit_clicked = True
        else:
            if st.button("提交報表", type="primary", use_container_width=True):
                submit_clicked = True

        if submit_clicked:
            new_row = [
                str(date), department, 
                int(cash), int(card), int(remit), 
                int(deposit), int(forfeit), 
                int(cash_coupon), rev_memo,
                int(total_rev), int(current_month_rev), f"{target_ratio*100:.1f}%", 
                int(customers), int(avg_customer_spend),
                float(k_hours), float(f_hours), float(total_hrs), 
                int(avg_rate), int(productivity), f"{labor_ratio*100:.1f}%",
                int(petty_yesterday), int(petty_expense), int(petty_replenish), int(petty_today),
                int(ikkon_coupon), int(thousand_coupon), int(total_coupon),
                emp_user_str, emp_target_str, 
                ops_note.strip(), tags_str, reason_action.strip(), announcement.strip() 
            ]
            
            success, action = db.upsert_report("Sheet1", str(date), department, new_row)
            
            if success:
                action_text = "更新" if action == "updated" else "新增"
                st.success(f"營運報表已成功{action_text}。")
                st.cache_data.clear()
                
                finance_img_bytes = generate_finance_image(
                    date, department, 
                    current_month_rev, current_month_cust, current_month_spend, target_ratio,
                    total_rev, customers, avg_customer_spend,
                    cash, card, remit, deposit, forfeit, cash_coupon, 
                    petty_yesterday, petty_expense, petty_replenish, petty_today,
                    ikkon_coupon, thousand_coupon, total_coupon, emp_display_str
                )
                
                ops_img_bytes = generate_ops_image(
                    date, department, productivity, labor_ratio, k_hours, f_hours, 
                    ops_note, announcement, tags_str, reason_action
                )
                
                st.divider()
                st.subheader("報表已生成")
                st.info("請直接於下方圖片「長按」並選擇「儲存圖片」，即可存入相簿進行回報。")
                
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    st.markdown("**財務日報 (提供會計群組)**")
                    st.image(finance_img_bytes, use_container_width=True)
                with col_img2:
                    st.markdown("**營運日報 (提供現場群組)**")
                    st.image(ops_img_bytes, use_container_width=True)
                st.divider()
            else:
                st.error(f"報表寫入失敗，請聯絡系統管理員。錯誤訊息：{action}")

    elif mode == "值班主管週報":
        st.title("值班主管週報")
        
        now = datetime.datetime.now()
        logical_today = now.date()
        if now.hour < 6:
            logical_today = logical_today - datetime.timedelta(days=1)
        
        is_sunday = logical_today.weekday() == 6
        
        if is_sunday:
            st.error("⚠️ **今日為系統週報結算日！請值班主管務必於下班前完成本週回報，並下載圖片回報至幹部群組。**")
        else:
            st.info("系統建議：請選擇要結算的那一週（系統已自動為跨夜班次進行校正，亦可手動更改基準日）。")

        dept_options = list(TARGETS.keys()) if st.session_state['dept_access'] == "ALL" else [st.session_state['dept_access']]
        department = st.selectbox("部門", dept_options)
        
        st.markdown("##### 選擇結算基準日")
        selected_date = st.date_input("系統會自動抓取此日期「所屬的星期一至星期日」作為本週數據區間", value=logical_today)
        
        start_of_week = selected_date - datetime.timedelta(days=selected_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        st.success(f"目前統計區間：`{start_of_week}` 至 `{end_of_week}`")
        
        week_rev, week_spend, week_prod = 0, 0, 0
        if report_data:
            df = pd.DataFrame(report_data)
            if not df.empty and '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                mask = (df['部門'] == department) & (df['日期'].dt.date >= start_of_week) & (df['日期'].dt.date <= end_of_week)
                week_df = df.loc[mask].copy()
                
                if not week_df.empty:
                    for col in ['總營業額', '總來客數', '總工時']:
                        week_df[col] = pd.to_numeric(week_df[col], errors='coerce').fillna(0)
                    
                    week_rev = week_df['總營業額'].sum()
                    week_cust = week_df['總來客數'].sum()
                    week_hrs = week_df['總工時'].sum()
                    
                    week_spend = week_rev / week_cust if week_cust > 0 else 0
                    week_prod = week_rev / week_hrs if week_hrs > 0 else 0
                else:
                    st.warning("⚠️ 系統尚未抓取到此區間的任何日報資料。")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("本週累計總營收", f"${week_rev:,.0f}")
        with c2:
            st.metric("本週平均客單價", f"${week_spend:,.0f}")
        with c3:
            st.metric("本週平均工時產值", f"${week_prod:,.0f}/hr")

        st.divider()
        st.subheader("營運深度分析 (請詳細論述)")
        
        st.markdown("**1. 數據與營運檢討**")
        review = st.text_area("1", placeholder="例：本週業績落後目標 5%，主因為寒流來襲，顧客銳減。但在銷售上成功推出高單價商品，拉高了整體客單價...", height=100, label_visibility="collapsed")
        
        st.markdown("**2. 團隊與人事狀況**")
        hr_status = st.text_area("2", placeholder="例：外場新人 A 培訓進度超前，已可獨立點餐；內場 B 預計下月離職，需盡快徵人遞補...", height=100, label_visibility="collapsed")
        
        st.markdown("**3. 行銷觀察與改善建議**")
        market = st.text_area("3", placeholder="例：顧客對於新推出的A商品相當喜歡，建議可成為常備商品；下週藝文特區有啤酒節，預計會帶來人潮...", height=100, label_visibility="collapsed")
        
        st.markdown("**4. 下週行動方針 (請具體列出三項目標)**")
        
        st.markdown("**行動一**")
        action_1 = st.text_area("a1", placeholder="例：針對新人 A 進行高單價商品推銷話術驗收。", height=100, label_visibility="collapsed")
        
        st.markdown("**行動二**")
        action_2 = st.text_area("a2", placeholder="例：調整內場備料方式，縮短出餐時間。", height=100, label_visibility="collapsed")
        
        st.markdown("**行動三**")
        action_3 = st.text_area("a3", placeholder="例：在週三前會完成聖誕節布置。", height=100, label_visibility="collapsed")
        
        actions_str = f"1. {action_1.strip()}\n2. {action_2.strip()}\n3. {action_3.strip()}".strip()

        if st.button("提交值班主管週報", type="primary", use_container_width=True):
            if not review.strip() or not hr_status.strip() or not market.strip() or not action_1.strip() or not action_2.strip() or not action_3.strip():
                st.error("請確實填寫檢討、人事、商圈觀察，以及【三項行動方針】，不可留白，這才是主管的核心價值。")
            else:
                new_weekly_row = [
                    str(selected_date), department, str(start_of_week), str(end_of_week),
                    int(week_rev), int(week_spend), int(week_prod), 
                    review.strip(), hr_status.strip(), market.strip(), actions_str, 
                    st.session_state['user_name']
                ]
                
                success, action = db.upsert_report("WeeklyReports", str(selected_date), department, new_weekly_row)
                
                if success:
                    st.success("週報已成功寫入核心資料庫！")
                    
                    weekly_img_bytes = generate_weekly_image(
                        str(selected_date), department, str(start_of_week), str(end_of_week),
                        week_rev, week_spend, week_prod, review, hr_status, market, 
                        action_1.strip(), action_2.strip(), action_3.strip(), st.session_state['user_name']
                    )
                    
                    st.divider()
                    st.markdown("### 週報已生成")
                    st.info("請長按圖片儲存，並發送至管理群組完成本週匯報。")
                    st.image(weekly_img_bytes, use_container_width=True)
                else:
                    st.error(f"寫入失敗：{action}")

    elif mode == "月度損益彙總":
        st.title("月度財務彙總分析")
        
        if st.session_state['dept_access'] == "ALL":
            view_mode = st.radio("檢視模式", ["分店比較", "綜合彙總"], horizontal=True)
        else:
            view_mode = "綜合彙總"
            
        raw_df = pd.DataFrame(report_data)
        if not raw_df.empty:
            raw_df['日期'] = pd.to_datetime(raw_df['日期'])
            if st.session_state['dept_access'] != "ALL":
                raw_df = raw_df[raw_df['部門'] == st.session_state['dept_access']]
            
            month_list = sorted(raw_df['日期'].dt.strftime('%Y-%m').unique(), reverse=True)
            target_month = st.selectbox("選擇月份", month_list)
            
            filtered_df = raw_df[raw_df['日期'].dt.strftime('%Y-%m') == target_month].copy()
            filtered_df = filtered_df.sort_values(by='日期')
            
            for col in ['總營業額', '總工時', '平均時薪', '現金', '刷卡', '匯款', '工時產值', '客單價', '總來客數']:
                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0)
            
            if '人事成本占比' in filtered_df.columns:
                filtered_df['人事成本數值'] = filtered_df['人事成本占比'].astype(str).str.replace('%', '', regex=False)
                filtered_df['人事成本數值'] = pd.to_numeric(filtered_df['人事成本數值'], errors='coerce').fillna(0)
            
            m_rev = filtered_df['總營業額'].sum()
            m_hrs = filtered_df['總工時'].sum()
            m_cost = (filtered_df['總工時'] * filtered_df['平均時薪']).sum()
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("當月總營收", f"${m_rev:,.0f}")
            c2.metric("預估人事支出", f"${m_cost:,.0f}")
            c3.metric("平均工時產值", f"${m_rev/m_hrs:,.0f}/hr" if m_hrs > 0 else "0")
            
            st.subheader("趨勢與結構分析")
            
            if st.session_state['dept_access'] == "ALL":
                st.markdown("##### 各分店當月累計營收")
                dept_totals = filtered_df.groupby('部門')['總營業額'].sum()
                if not dept_totals.empty:
                    dept_cols = st.columns(len(dept_totals))
                    for idx, (dept_name, dept_total) in enumerate(dept_totals.items()):
                        dept_target = TARGETS.get(dept_name, 1)
                        achieve_rate = (dept_total / dept_target) * 100 if dept_target > 0 else 0
                        dept_cols[idx].metric(
                            label=f"📍 {dept_name}", 
                            value=f"${dept_total:,.0f}",
                            delta=f"達成率：{achieve_rate:.1f}%",
                            delta_color="normal"
                        )
                    st.write("") 

            chart_df = filtered_df.copy()
            chart_df['日期標籤'] = chart_df['日期'].dt.strftime('%m-%d')
            
            tab1, tab2, tab3, tab4 = st.tabs(["每日營收趨勢", "客單價趨勢", "工時產值監控", "人事成本佔比趨勢"])
            
            if view_mode == "分店比較":
                with tab1:
                    st.caption("透過分店每日營收起伏，檢視各店平假日業績落差與行銷活動成效。")
                    bar_chart = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('總營業額:Q', title='營業額 ($)'),
                        color=alt.Color('部門:N', title='分店'),
                        xOffset='部門:N',
                        tooltip=['日期標籤', '部門', '總營業額', '總來客數']
                    ).properties(height=350)
                    st.altair_chart(bar_chart, use_container_width=True)
                    
                with tab2:
                    st.caption("各店客單價波動比較，反映現場同仁推銷力道與高單價品項點購率差異。")
                    line_chart_spend = alt.Chart(chart_df).mark_line(point=True).encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('客單價:Q', title='客單價 ($)', scale=alt.Scale(zero=False)),
                        color=alt.Color('部門:N', title='分店'),
                        tooltip=['日期標籤', '部門', '客單價', '總營業額']
                    ).properties(height=350)
                    st.altair_chart(line_chart_spend, use_container_width=True)
                    
                with tab3:
                    st.caption("各店工時產值比較。數字過低代表人力閒置，過高代表現場過勞且可能犧牲服務品質。")
                    line_chart_prod = alt.Chart(chart_df).mark_line(point=True).encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('工時產值:Q', title='產值 ($/hr)', scale=alt.Scale(zero=False)),
                        color=alt.Color('部門:N', title='分店'),
                        tooltip=['日期標籤', '部門', '工時產值', '總工時']
                    ).properties(height=350)
                    st.altair_chart(line_chart_prod, use_container_width=True)
                    
                with tab4:
                    st.caption("各店每日人事成本佔比比較。當佔比異常飆升時，應立即檢視該店排班。")
                    line_chart_labor = alt.Chart(chart_df).mark_line(point=True).encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('人事成本數值:Q', title='人事成本佔比 (%)', scale=alt.Scale(zero=False)),
                        color=alt.Color('部門:N', title='分店'),
                        tooltip=['日期標籤', '部門', '人事成本數值', '總工時']
                    ).properties(height=350)
                    st.altair_chart(line_chart_labor, use_container_width=True)
            else:
                def aggregate_daily(df):
                    res = pd.Series(dtype='float64')
                    res['總營業額'] = df['總營業額'].sum()
                    res['總來客數'] = df['總來客數'].sum()
                    res['總工時'] = df['總工時'].sum()
                    daily_cost = (df['總工時'] * df['平均時薪']).sum()
                    res['客單價'] = res['總營業額'] / res['總來客數'] if res['總來客數'] > 0 else 0
                    res['工時產值'] = res['總營業額'] / res['總工時'] if res['總工時'] > 0 else 0
                    res['人事成本數值'] = (daily_cost / res['總營業額'] * 100) if res['總營業額'] > 0 else 0
                    return res

                agg_df = chart_df.groupby('日期標籤').apply(aggregate_daily).reset_index()
                
                with tab1:
                    st.caption("全品牌每日營收總和趨勢。")
                    bar_chart = alt.Chart(agg_df).mark_bar(color='#2E86AB').encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('總營業額:Q', title='總營業額 ($)'),
                        tooltip=['日期標籤', '總營業額', '總來客數']
                    ).properties(height=350)
                    st.altair_chart(bar_chart, use_container_width=True)
                    
                with tab2:
                    st.caption("全品牌綜合客單價趨勢。")
                    line_chart_spend = alt.Chart(agg_df).mark_line(point=True, color='#F2A65A').encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('客單價:Q', title='客單價 ($)', scale=alt.Scale(zero=False)),
                        tooltip=['日期標籤', '客單價', '總營業額']
                    ).properties(height=350)
                    st.altair_chart(line_chart_spend, use_container_width=True)
                    
                with tab3:
                    st.caption("全品牌綜合工時產值。")
                    line_chart_prod = alt.Chart(agg_df).mark_line(point=True, color='#D64933').encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('工時產值:Q', title='產值 ($/hr)', scale=alt.Scale(zero=False)),
                        tooltip=['日期標籤', '工時產值', '總工時']
                    ).properties(height=350)
                    st.altair_chart(line_chart_prod, use_container_width=True)
                    
                with tab4:
                    st.caption("全品牌綜合人事成本佔比。")
                    line_chart_labor = alt.Chart(agg_df).mark_line(point=True, color='#779CAB').encode(
                        x=alt.X('日期標籤:N', title='日期'),
                        y=alt.Y('人事成本數值:Q', title='人事成本佔比 (%)', scale=alt.Scale(zero=False)),
                        tooltip=['日期標籤', '人事成本數值', '總工時']
                    ).properties(height=350)
                    st.altair_chart(line_chart_labor, use_container_width=True)

            st.divider()
            st.subheader("當月明細數據")
            display_cols = ['日期', '部門', '現金', '刷卡', '匯款', '總營業額', '金額備註', '營運回報', '客訴分類標籤']
            st.dataframe(filtered_df[display_cols].sort_values(by='日期', ascending=False), use_container_width=True)
        else:
            st.info("尚未有數據。")
