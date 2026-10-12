import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

DB_NAME = "dk_staff_tracker.db"

def get_india_now():
    return datetime.now(ZoneInfo('Asia/Kolkata'))

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table 1: Employees
