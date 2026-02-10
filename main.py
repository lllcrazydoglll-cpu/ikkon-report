import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# 直接在程式碼中定義認證資訊，排除所有 Secrets 貼上的格式問題
def get_gspread_client():
    try:
        # 這是你的私鑰資訊，我已經校正過格式
        info = {
            "type": "service_account",
            "project_id": "cybernetic-day-487005-f4",
            "private_key_id": "12a1eb6bf22e6366b1f457ad250882ec200839b8",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCkNua/W7/ZZO4T\nA5tRKXi8Q6RvNqFdshrzxgZxYMZ9bYF1FrqpsDAleEC+Yfa4lXqwwLKEyXeO6sBs\n5KQGcWH4YK3PnWu0nYYfMuBH0f4zlkRnFuFUhRGlE75BbGwWW6S8EPmezSFD4wJw\nBiDOG8nb6XWzksJOlywYXOnorf/v/SdnwkgJFa5dL5GiBhe2AOFMswx09RJW4cdf\nAvl8X7LbwmzRVgLV1O51T0tXVs68Co6+mkOAfrZiL5Ooc8TsFhjKJHtEcgz4ldrt\nNTm5n5YWNaQIYOTTcKzYrrfJcmLarUl2P42PJVm6tl//dXo46ddhGOz2iTb7rp31\n/8xcytb1AgMBAAECggEAHaxoDOsk40E4PgpYThW64fYtKAWMqjQtZ6CAeItewrp/\nequFRnV2dcbhmCV2oksslPT1LUaEirhD1kmIlDt30xyRO+N723LdkhSs7310PFkq\neiBpzk6Pbi9/oS3Y6D9eKLe+i6IQoUZLofeRhP0DgHAS20SpRO9PQgXEJM4QYgqo\nKdT8yB6BjBDwAyECtspJL4YhATPg2s6z7oXBeqIAyonzV0+N8lBuSrUJZlZIJ6tl\nUGBhV6pLXtBYfMEj/dLsHpGaRjperjyXGa7glNVL74sEufi6T0vCwIsnSE+FgxZf\nWihiFQMVIRlvaO3NPEnOwzf4PoaaTZVl0elAnp27PwKBgQDTibb2l5gdCW6mx6Uj\n9Cz9YmK4aj5qa1BKJ6VxgSNSXY1UNpHrz3BZ0Y4gsDu1t08jYNMwOt00dHYp5VhC\nbC9REe201NalMtn8PvXSf3ya41qvuGBeCmzv3uJ+7k+agl194jHVEiJiwv5kXdSO\n/CsQLBHD9K6H3MMMSLETcSJjAwKBgQDGutZrMp8zQkxS+FxwBu/7cFJp6UC5DDV1\ny/e/SoGIEqsKl087vo/jWu4ui+shMNcymtd0zqMH4Fl1laIaYb9fnK4KMsNCJUaA\n6SeWGWDuDxdClozhRhFYV3+5HFvYOyylrtfFJbqp1YTkDNKwSR68NBfqCW8vptrO\np39zl7ApwKBgA1h3vNGr9bWa+udIbNelSIKgVhNUFmHJHMsgujlVIi3ZmN3eE/E\ntcTY3vbubziVuinwzCt27duNqpQH8EdzdKLaUYFpHZMh3mx4xzBj5EwgKfKH5YDN\nhArAvO9uwBZ0PNnj32ctWIOK9nD/Bp1tEoRZZV5SMmBh9OzoBFvIgnZlAoGBAKgp\n+EFT39V/V5iqI4aEyFRLkuGeiK9N/nsEs0uC36NmsKfQrDKRKa8pBf4LVleKvb9L\nueBU7y4+EVVn3nlWl5tvuPJWTFZPtp5lLaNdLGGmEXe+b848/XZ07FaXAb0zLa+y\nCVIBgDgwvzg/BZY4+bImnsnjW9vF5MgM/wKDvDhnAoGASiQ3Qk9sLG4okksRwx7z\nxYvTIX3C7qP2J7iF+y4LSUZEfyPF755fhZj5+OVpDQWEwUdxMW45yoHzJKvip7v6\nsOTmDV6DLlV0s1w8dH43NFPEHROTlIlffh18eiZ3tcZ6UYFtRhGkhDnuiF5Jqy8n\npyyAWlhXIQTiCG4HiQwWQeE=\n-----END PRIVATE KEY-----\n",
            "client_email": "ikkon-service@cybernetic-day-487005-f4.iam.gserviceaccount.com",
            "client_id": "100319064175689578515",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.google.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/ikkon-service%40cybernetic-day-487005-f4.iam.gserviceaccount.com"
        }
        
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"認證失敗：{e}")
        return None

# --- 以下為介面邏輯 (保持不變) ---
st.set_page_config(page_title="IKKON 日報表系統", page_icon="📝")
st.title("IKKON 日報表系統")

date = st.date_input("報表日期", datetime.date.today())
department = st.selectbox("部門", ["桃園鍋物", "桃園燒肉", "台中和牛會所"])

col1, col2 = st.columns(2)
with col1:
    cash = st.number_input("現金收入", min_value=0, step=100)
    credit_card = st.number_input("刷卡收入", min_value=0, step=100)
    remittance = st.number_input("匯款收入", min_value=0, step=100)
with col2:
    total_customers = st.number_input("總來客數", min_value=1, step=1)
    kitchen_hours = st.number_input("內場總工時", min_value=0.0, step=0.5)
    floor_hours = st.number_input("外場總工時", min_value=0.0, step=0.5)

total_revenue = cash + credit_card + remittance
total_hours = kitchen_hours + floor_hours
productivity = total_revenue / total_hours if total_hours > 0 else 0
avg_spend = total_revenue / total_customers if total_customers > 0 else 0

st.write(f"### 當日總營收：{total_revenue:,} 元")

ops_note = st.text_area("營運回報、事務宣達")
complaint_note = st.text_area("客訴處理")

if st.button("確認提交日報表", type="primary"):
    with st.spinner('連線中...'):
        client = get_gspread_client()
        if client:
            try:
                sheet = client.open_by_key(st.secrets["spreadsheet"]["id"]).sheet1
                new_row = [
                    str(date), department, cash, credit_card, remittance, "", 
                    total_revenue, total_customers, round(avg_spend, 2), 
                    kitchen_hours, floor_hours, total_hours, round(productivity, 2), 
                    ops_note, complaint_note
                ]
                sheet.append_row(new_row)
                st.success("✅ 資料已成功存入雲端！")
                st.balloons()
            except Exception as e:
                st.error(f"寫入失敗：{e}")
