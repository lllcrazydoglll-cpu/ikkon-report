import streamlit as st
import datetime
import pandas as pd
import altair as alt
from database import DatabaseManager

st.set_page_config(page_title="IKKON 經營決策系統", layout="wide")

SHEET_COLUMNS = [
    "日期", "部門", "現金", "刷卡", "匯款", "現金折價卷", "金額備註",
    "總營業額", "月營業額", "目標占比", "總來客數", "客單價", 
    "內場工時", "外場工時", "總工時", "平均時薪", "工時產值", "人事成本占比",
    "昨日剩", "今日支出", "今日補", "今日剰", 
    "IKKON折抵券", "1000折價券", "總共折抵金",
    "營運回報", "客訴分類標籤", "客訴原因說明", "客訴處理結果", "事項宣達"
]

SID = "16FcpJZLhZjiRreongRDbsKsAROfd5xxqQqQMfAI7H08"

db = DatabaseManager(SID, st.secrets)

@st.cache_data(ttl=300)
def load_cached_data():
    return db.get_all_data()

user_df, settings_df, report_data = load_cached_data()

# 若資料庫讀取失敗的防呆提醒
if user_df is None and settings_df is None:
    st.error("系統初始化失敗：無法連接至核心資料庫，請檢查網路連線或授權設定。")
    st.stop()

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

if login_ui(user_df):
    TARGETS = dict(zip(settings_df['部門'], settings_df['月目標']))
    HOURLY_RATES = dict(zip(settings_df['部門'], settings_df['平均時薪']))
    is_admin = st.session_state.get("user_role") == "admin"
    is_ceo = st.session_state.get("user_role") == "ceo"

    with st.sidebar:
        st.title(f"{st.session_state['user_name']}")
        st.caption(f"權限等級：{st.session_state['user_role'].upper()}")
        
        menu_options = ["數據登記", "月度損益彙總"]
        if is_admin:
            menu_options.append("系統後台管理")
            
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
            st.caption("權限等級規範：admin (管理員) / ceo (執行長) / staff (店長)。負責部門若為全部請填寫 ALL。")
            edited_users = st.data_editor(user_df, num_rows="dynamic", use_container_width=True, key="user_editor")
            if st.button("儲存帳號設定", type="primary"):
                success, msg = db.update_backend_sheet("Users", edited_users)
                if success:
                    st.success("帳號資料已成功同步至資料庫！")
                    st.cache_data.clear()
                else:
                    st.error(f"寫入失敗：{msg}")

        with tab_settings:
            st.subheader("各分店目標與時薪基準")
            edited_settings = st.data_editor(settings_df, num_rows="dynamic", use_container_width=True, key="setting_editor")
            if st.button("儲存營運設定", type="primary"):
                success, msg = db.update_backend_sheet("Settings", edited_settings)
                if success:
                    st.success("營運設定已成功同步至資料庫！")
                    st.cache_data.clear()
                else:
                    st.error(f"寫入失敗：{msg}")

    elif mode == "數據登記":
        st.title("營運數據登記")
        dept_options = list(TARGETS.keys()) if st.session_state['dept_access'] == "ALL" else [st.session_state['dept_access']]
        department = st.selectbox("部門", dept_options)
        date = st.date_input("報表日期", datetime.date.today())
        avg_rate = HOURLY_RATES.get(department, 205)
        month_target = TARGETS.get(department, 1000000)
        
        last_petty_cash = 0
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

        st.subheader("營收數據")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            cash = st.number_input("現金收入", min_value=0, step=100)
        with c2:
            card = st.number_input("刷卡收入", min_value=0, step=100)
        with c3:
            remit = st.number_input("匯款收入", min_value=0, step=100)
        with c4:
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

        st.subheader("營運與客訴回報")
        ops_note = st.text_area("營運狀況回報", height=120)
        announcement = st.text_area("事項宣達", height=80)
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            tags = st.multiselect("客訴分類", ["餐點品質", "服務態度", "環境衛生", "上菜效率", "訂位系統", "其他"])
            tags_str = ", ".join(tags) if tags else "無"
        with col_c2:
            reason_action = st.text_area("原因與處理結果", height=80)

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
                mask = (raw_df['部門'] == department) & (raw_df['日期'].dt.strftime('%Y-%m') == current_month_str) & (raw_df['日期'] < pd.to_datetime(date))
                historical_month_rev = float(pd.to_numeric(raw_df.loc[mask, '總營業額'], errors='coerce').fillna(0).sum())
                current_month_rev += historical_month_rev
        
        target_ratio = float(current_month_rev / month_target) if month_target > 0 else 0.0

        if st.button("提交報表", type="primary", use_container_width=True):
            new_row = [
                str(date), department, 
                int(cash), int(card), int(remit), int(cash_coupon), rev_memo,
                int(total_rev), int(current_month_rev), f"{target_ratio*100:.1f}%", 
                int(customers), int(avg_customer_spend),
                float(k_hours), float(f_hours), float(total_hrs), 
                int(avg_rate), int(productivity), f"{labor_ratio*100:.1f}%",
                int(petty_yesterday), int(petty_expense), int(petty_replenish), int(petty_today),
                int(ikkon_coupon), int(thousand_coupon), int(total_coupon),
                ops_note.strip(), tags_str, reason_action.strip(), "已提交", announcement.strip()
            ]
            
            success, action = db.upsert_daily_report(str(date), department, new_row)
            
            if success:
                action_text = "更新" if action == "updated" else "新增"
                st.success(f"{date} {department} 的營運報表已成功{action_text}。")
                st.cache_data.clear()
            else:
                st.error(f"報表寫入失敗，請聯絡系統管理員。錯誤訊息：{action}")
            
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
| **距離目標** | **${int(month_target - current_month_rev):,.0f}** | **目標占比** | **{target_ratio*100:.1f}%** |

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

            st.subheader("回報文字彙整")
            
            st.markdown("##### 預覽區 (同仁確認用)")
            st.info(f"**【營運回報】**\n\n{ops_note.strip()}\n\n---\n\n**【事項宣達】**\n\n{announcement.strip()}\n\n---\n\n**【客訴處理】** ({tags_str})\n\n{reason_action.strip()}")
            
            st.markdown("##### 一鍵複製區 (點擊右上角按鈕)")
            text_summary = f"【營運回報】\n{ops_note.strip()}\n\n【事項宣達】\n{announcement.strip()}\n\n【客訴處理】({tags_str})\n{reason_action.strip()}"
            st.code(text_summary, language="text")

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
