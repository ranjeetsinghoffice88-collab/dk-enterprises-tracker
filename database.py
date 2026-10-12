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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    
    # Table 2: Attendance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_name TEXT NOT NULL,
            date TEXT NOT NULL,
            check_in TEXT,
            check_out TEXT,
            UNIQUE(emp_name, date)
        )
    ''')
    
    # Table 3: Live Tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS live_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_name TEXT NOT NULL,
            date TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration TEXT,
            task_desc TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT NOT NULL
        )
    ''')

    # Table 4: Dress Code Tracker
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dress_code (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_name TEXT NOT NULL,
            date TEXT NOT NULL,
            in_uniform TEXT NOT NULL,
            reason TEXT,
            timestamp TEXT NOT NULL,
            UNIQUE(emp_name, date)
        )
    ''')

    # Table 5: Leave Management (New Corporate Leave Table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_name TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            total_days INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            calculated_type TEXT,
            applied_at TEXT NOT NULL
        )
    ''')

    # D.K. Enterprises Staff Members
    dk_staff = [("Komal", "Operations"), ("Vijay", "Operations"), ("Navinder", "Operations")]
    for name, dept in dk_staff:
        cursor.execute("INSERT OR IGNORE INTO employees (name, department) VALUES (?, ?)", (name, dept))
        
    conn.commit()
    conn.close()
