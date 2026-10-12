import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
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

    # D.K. Enterprises Staff Members
    dk_staff = [("Komal", "Operations"), ("Vijay", "Operations"), ("Navinder", "Operations")]
    for name, dept in dk_staff:
        cursor.execute("INSERT OR IGNORE INTO employees (name, department) VALUES (?, ?)", (name, dept))
        
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="D.K. Enterprises Staff Tracker", layout="wide")

st.title("📋 D.K. Enterprises - Daily Staff Tracker & Workboard")

st.sidebar.header("Navigation")
staff_list = ["Komal", "Vijay", "Navinder"]
selected_emp = st.sidebar.selectbox("Select Employee", staff_list)

mode = st.sidebar.radio("View Mode", ["Staff Entry", "Admin Dashboard"])

now_ist = get_india_now()
today_str = now_ist.strftime("%Y-%m-%d")

# ---------------------------------------------------------
# VIEW 1: STAFF ENTRY
# ---------------------------------------------------------
if mode == "Staff Entry":
    st.subheader(f"Welcome, {selected_emp} 👋")
    
    # Section 1: Attendance
    st.markdown("### ⏰ Daily Attendance")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🟢 Morning Check-In", use_container_width=True):
            now_time = get_india_now().strftime("%I:%M %p")
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO attendance (emp_name, date, check_in) VALUES (?, ?, ?)", (selected_emp, today_str, now_time))
                conn.commit()
                st.success(f"Checked in successfully at {now_time}")
            except sqlite3.IntegrityError:
                st.warning("Already checked in today!")
            finally:
                conn.close()

    with col2:
        if st.button("🔴 Evening Check-Out", use_container_width=True):
            now_time = get_india_now().strftime("%I:%M %p")
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE attendance SET check_out = ? WHERE emp_name = ? AND date = ?", (now_time, selected_emp, today_str))
            conn.commit()
            if cursor.rowcount > 0:
                st.success(f"Checked out at {now_time}")
            else:
                st.warning("No check-in record found for today!")
            conn.close()

    st.divider()

    # Section 2: Daily Dress Code Checker
    st.markdown("### 👔 Daily Dress Code Verification")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT in_uniform, reason FROM dress_code WHERE emp_name = ? AND date = ?", (selected_emp, today_str))
    dress_record = cursor.fetchone()
    conn.close()

    if dress_record:
        st.success(f"✅ Today's Uniform Status Submitted: **{dress_record[0]}**" + (f" (Reason: {dress_record[1]})" if dress_record[1] else ""))
    else:
        with st.form("dress_code_form", clear_on_submit=False):
            dress_opt = st.radio(
                "Are you wearing the official office uniform / dress code today?",
                ["Yes, Full Uniform 🟢", "No / Casual / Partial 🔴"],
                horizontal=True
            )
            reason_input = st.text_input("If 'No', please state the reason:", placeholder="e.g. Uniform on washing / Emergency")
            submit_dress = st.form_submit_button("Submit Dress Code Status")

            if submit_dress:
                is_uniform = "Yes" if "Yes" in dress_opt else "No"
                now_ts = get_india_now().strftime("%Y-%m-%d %I:%M %p")
                
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO dress_code (emp_name, date, in_uniform, reason, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (selected_emp, today_str, is_uniform, reason_input if is_uniform == "No" else "-", now_ts))
                    conn.commit()
                    st.success("Dress code status recorded successfully!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.warning("Dress code status already submitted for today!")
                finally:
                    conn.close()

    st.divider()

    # Section 3: Live Activity Tracker
    st.markdown("### ⏱️ Live Activity Tracker")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT task_id, activity_type, start_time, task_desc 
        FROM live_tasks 
        WHERE emp_name = ? AND date = ? AND status = 'Ongoing' 
        ORDER BY task_id DESC LIMIT 1
    """, (selected_emp, today_str))
    active_task = cursor.fetchone()
    
    if active_task:
        task_id, act_type, start_t_str, desc = active_task
        st.info(f"⏳ **Currently Active:** {act_type} (Started at {start_t_str})")
        if desc:
            st.caption(f"Note: {desc}")
            
        if st.button("⏹️ Stop Current Activity", type="primary", use_container_width=True):
            end_
