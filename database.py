import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

class DatabaseManager:
    def __init__(self, sid, secrets):
        self.sid = sid
        self.secrets = secrets
        self.client = self._connect()

    def _connect(self):
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds_info = dict(self.secrets["gcp_service_account"])
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"資料庫連線錯誤：{e}")
            return None

    def get_all_data(self):
        if not self.client: 
            return None, None, None
        try:
            sh = self.client.open_by_key(self.sid)
            user_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
            settings_df = pd.DataFrame(sh.worksheet("Settings").get_all_records())
            report_data = sh.worksheet("Sheet1").get_all_records()
            return user_df, settings_df, report_data
        except Exception as e:
            print(f"資料讀取錯誤：{e}")
            return None, None, None

    def upsert_daily_report(self, date_str, department, new_row):
        if not self.client: 
            return False, "連線失敗"
        try:
            sh = self.client.open_by_key(self.sid)
            sheet = sh.worksheet("Sheet1")
            all_values = sheet.get_all_values()
            target_row_idx = None
            
            for i, row in enumerate(all_values):
                if i == 0: continue
                if len(row) >= 2 and row[0] == date_str and row[1] == department:
                    target_row_idx = i + 1
                    break
            
            if target_row_idx:
                cell_list = sheet.range(f"A{target_row_idx}:AD{target_row_idx}")
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

    def update_backend_sheet(self, sheet_name, df):
        if not self.client: 
            return False, "連線失敗"
        try:
            sh = self.client.open_by_key(self.sid)
            sheet = sh.worksheet(sheet_name)
            sheet.clear()
            df_cleaned = df.fillna("")
            data = [df_cleaned.columns.tolist()] + df_cleaned.values.tolist()
            sheet.update(values=data, range_name="A1")
            return True, "success"
        except Exception as e:
            return False, str(e)
