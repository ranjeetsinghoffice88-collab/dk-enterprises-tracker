import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from zoneinfo import ZoneInfo
from database import DB_NAME, get_india_now, init_db

# Initialize Database & Tables
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
            end_t_dt = get_india_now()
            end_t_str = end_t_dt.strftime("%I:%M %p")
            
            start_t_dt = datetime.strptime(f"{today_str} {start_t_str}", "%Y-%m-%d %I:%M %p").replace(tzinfo=ZoneInfo('Asia/Kolkata'))
            diff_mins = int((end_t_dt - start_t_dt).total_seconds() / 60)
            
            hrs = diff_mins // 60
            mins = diff_mins % 60
            dur_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins} mins"
            
            cursor.execute("""
                UPDATE live_tasks 
                SET end_time = ?, duration = ?, status = 'Completed' 
                WHERE task_id = ?
            """, (end_t_str, dur_str, task_id))
            conn.commit()
            st.success(f"Activity stopped at {end_t_str}! Total duration: {dur_str}")
            st.rerun()
    else:
        st.write("🟢 **No activity running right now. Choose an activity to start:**")
        
        st.markdown("#### Start New Activity")
        with st.form("start_task_form", clear_on_submit=True):
            col_act, col_prio = st.columns([2, 1])
            with col_act:
                activity = st.selectbox("Activity Type", ["Production", "Break", "Out of Office", "No Work", "Planned Leave", "Others"])
            with col_prio:
                priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)
                
            desc = st.text_input("Description / Notes (Optional)", placeholder="E.g., Lunch break, Client call, Project task details...")
            
            start_submitted = st.form_submit_button("▶️ Start Activity Now")
            
            if start_submitted:
                now_dt = get_india_now()
                start_t_str = now_dt.strftime("%I:%M %p")
                
                cursor.execute("""
                    SELECT task_id, start_time FROM live_tasks 
                    WHERE emp_name = ? AND date = ? AND status = 'Ongoing'
                """, (selected_emp, today_str))
                prev_task = cursor.fetchone()
                
                if prev_task:
                    p_id, p_start = prev_task
                    p_start_dt = datetime.strptime(f"{today_str} {p_start}", "%Y-%m-%d %I:%M %p").replace(tzinfo=ZoneInfo('Asia/Kolkata'))
                    diff_m = int((now_dt - p_start_dt).total_seconds() / 60)
                    dur_s = f"{diff_m//60}h {diff_m%60}m" if diff_m >= 60 else f"{diff_m} mins"
                    cursor.execute("UPDATE live_tasks SET end_time = ?, duration = ?, status = 'Completed' WHERE task_id = ?", 
                                   (start_t_str, dur_s, p_id))

                final_desc = desc.strip() if desc.strip() else f"Activity: {activity}"
                cursor.execute("""
                    INSERT INTO live_tasks (emp_name, date, activity_type, start_time, task_desc, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'Ongoing')
                """, (selected_emp, today_str, activity, start_t_str, final_desc, priority))
                
                conn.commit()
                st.success(f"Started '{activity}' at {start_t_str}!")
                st.rerun()

    conn.close()

    st.divider()
    st.markdown(f"### 📊 Today's Activity Timeline for **{selected_emp}** ({today_str})")
    
    conn = sqlite3.connect(DB_NAME)
    df_tasks = pd.read_sql_query("""
        SELECT activity_type as Activity, start_time as 'Start Time', COALESCE(end_time, 'In Progress...') as 'End Time', 
               COALESCE(duration, 'Running') as Duration, task_desc as Description, priority as Priority, status as Status 
        FROM live_tasks WHERE emp_name = ? AND date = ? ORDER BY task_id DESC
    """, conn, params=(selected_emp, today_str))
    conn.close()

    if not df_tasks.empty:
        st.dataframe(df_tasks, use_container_width=True, hide_index=True)
    else:
        st.info("No activities logged yet today.")

# ---------------------------------------------------------
# VIEW 2: ADMIN DASHBOARD & HISTORICAL RECORDS
# ---------------------------------------------------------
elif mode == "Admin Dashboard":
    st.subheader("🔒 Admin Dashboard (Time, Dress Code & History Overview)")
    
    selected_date = st.date_input("Select Single Date View", now_ist.date())
    date_str = selected_date.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)

    # Attendance Summary
    st.markdown(f"#### 📅 Attendance Summary for {date_str}")
    df_attn = pd.read_sql_query("SELECT emp_name as Employee, check_in as 'Check In', check_out as 'Check Out' FROM attendance WHERE date = ?", conn, params=(date_str,))
    st.dataframe(df_attn, use_container_width=True, hide_index=True)

    # Dress Code Summary
    st.markdown(f"#### 👔 Uniform Compliance Summary for {date_str}")
    df_dress_today = pd.read_sql_query("SELECT emp_name as Employee, in_uniform as 'In Uniform', reason as 'Reason / Note', timestamp as 'Submitted At' FROM dress_code WHERE date = ?", conn, params=(date_str,))
    if not df_dress_today.empty:
        st.dataframe(df_dress_today, use_container_width=True, hide_index=True)
    else:
        st.info(f"No dress code entries recorded for {date_str}.")

    # Activity Timeline
    st.markdown(f"#### ⏱️ Live Staff Activity & Break Timeline for {date_str}")
    df_all_tasks = pd.read_sql_query("""
        SELECT emp_name as Employee, activity_type as Activity, start_time as 'Start Time', 
               COALESCE(end_time, 'In Progress...') as 'End Time', COALESCE(duration, 'Running') as Duration, 
               task_desc as Description, priority as Priority, status as Status 
        FROM live_tasks WHERE date = ? ORDER BY task_id DESC
    """, conn, params=(date_str,))
    st.dataframe(df_all_tasks, use_container_width=True, hide_index=True)

    st.divider()

    # PAST DATA HISTORY SEARCH & CSV DOWNLOAD
    st.markdown("### 🔍 Past Data History Search & Filter")
    
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        selected_staff_filter = st.multiselect("Filter Employee(s)", staff_list, default=staff_list)
    with col_h2:
        from_date = st.date_input("From Date", now_ist.date())
    with col_h3:
        to_date = st.date_input("To Date", now_ist.date())

    from_date_str = from_date.strftime("%Y-%m-%d")
    to_date_str = to_date.strftime("%Y-%m-%d")

    if selected_staff_filter:
        placeholders = ', '.join('?' for _ in selected_staff_filter)
        
        # Historical Activity Log
        st.markdown(f"##### 📜 Activity History ({from_date_str} to {to_date_str})")
        params_tasks = selected_staff_filter + [from_date_str, to_date_str]
        query_hist_tasks = f"""
            SELECT date as Date, emp_name as Employee, activity_type as Activity, start_time as 'Start Time', 
                   end_time as 'End Time', duration as Duration, task_desc as Description, status as Status
            FROM live_tasks 
            WHERE emp_name IN ({placeholders}) AND date BETWEEN ? AND ? 
            ORDER BY date DESC, task_id DESC
        """
        df_hist_tasks = pd.read_sql_query(query_hist_tasks, conn, params=params_tasks)
        st.dataframe(df_hist_tasks, use_container_width=True, hide_index=True)

        # Historical Dress Code Log
        st.markdown(f"##### 👔 Dress Code History ({from_date_str} to {to_date_str})")
        params_dress = selected_staff_filter + [from_date_str, to_date_str]
        query_hist_dress = f"""
            SELECT date as Date, emp_name as Employee, in_uniform as 'In Uniform', reason as Reason, timestamp as Timestamp
            FROM dress_code 
            WHERE emp_name IN ({placeholders}) AND date BETWEEN ? AND ? 
            ORDER BY date DESC
        """
        df_hist_dress = pd.read_sql_query(query_hist_dress, conn, params=params_dress)
        st.dataframe(df_hist_dress, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### 📥 Download Database Backup CSVs")
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        df_all_attn = pd.read_sql_query("SELECT * FROM attendance", conn)
        if not df_all_attn.empty:
            csv_attn = df_all_attn.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Attendance CSV",
                data=csv_attn,
                file_name=f"dk_attendance_backup_{today_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col_d2:
        df_all_tasks_db = pd.read_sql_query("SELECT * FROM live_tasks", conn)
        if not df_all_tasks_db.empty:
            csv_tasks = df_all_tasks_db.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Tasks Backup CSV",
                data=csv_tasks,
                file_name=f"dk_tasks_backup_{today_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col_d3:
        df_all_dress = pd.read_sql_query("SELECT * FROM dress_code", conn)
        if not df_all_dress.empty:
            csv_dress = df_all_dress.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Dress Code CSV",
                data=csv_dress,
                file_name=f"dk_dress_code_backup_{today_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

    conn.close()
