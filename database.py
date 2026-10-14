import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

def get_india_now():
    return datetime.now(ZoneInfo('Asia/Kolkata'))

@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    client = get_gspread_client()
    return client.open("Staff_Tracker_Database")

def init_db():
    try:
        sheet = get_spreadsheet()
        expected_tables = {
            "dk_employees": ["emp_id", "name", "department"],
            "dk_attendance": ["id", "emp_name", "date", "check_in", "check_out"],
            "dk_live_tasks": ["task_id", "emp_name", "date", "activity_type", "start_time", "end_time", "duration", "task_desc", "priority", "status"],
            "dk_dress_code": ["id", "emp_name", "date", "in_uniform", "reason", "timestamp"],
            "dk_leaves": ["leave_id", "emp_name", "leave_type", "from_date", "to_date", "total_days", "reason", "status", "calculated_type", "applied_at"]
        }
        
        for table_name, headers in expected_tables.items():
            try:
                worksheet = sheet.worksheet(table_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=table_name, rows=1000, cols=20)
            
            if not worksheet.get_all_values():
                worksheet.append_row(headers)
                
        emp_ws = sheet.worksheet("dk_employees")
        existing_emps = emp_ws.get_all_records()
        if not existing_emps:
            dk_staff = [("Komal", "Operations"), ("Vijay", "Operations"), ("Navinder", "Operations")]
            for idx, (name, dept) in enumerate(dk_staff, start=1):
                emp_ws.append_row([idx, name, dept])
                
    except Exception as e:
        st.error(f"Google Sheets Connection Error: {e}")
