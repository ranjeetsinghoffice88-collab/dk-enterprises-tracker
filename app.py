import streamlit as st
import sqlite3
from datetime import datetime, date
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

# View Mode selection menu in English
mode = st.sidebar.radio(
    "View Mode", 
    ["Staff Entry", "Admin Dashboard", "📖 Policy & User Guidelines"]
)

now_ist = get_india_now()
today_str = now_ist.strftime("%Y-%m-%d")
current_year = now_ist.year
current_month = now_ist.month

# Helper function to evaluate corporate leave rules
def evaluate_leave_rules(emp_name, l_type, l_days, target_date_str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    t_year = target_dt.year
    t_month = target_dt.month
    
    calc_type = l_type
    popup_msg = ""
    
    if l_type == "Planned Leave":
        cursor.execute("""
            SELECT COALESCE(SUM(total_days), 0) FROM leaves 
            WHERE emp_name = ? AND leave_type = 'Planned Leave' AND status != 'Rejected'
            AND strftime('%Y', from_date) = ? AND strftime('%m', from_date) = ?
        """, (emp_name, str(t_year), f"{t_month:02d}"))
        month_planned_count = cursor.fetchone()[0]
        
        if month_planned_count >= 2:
            calc_type = "Unplanned / LWP (Exceeded Monthly Planned Limit)"
            popup_msg = "⚠️ Notice: You have already exhausted your quota of 2 planned leaves for this month. This leave will be categorized as Unplanned / LWP."
        elif (month_planned_count + l_days) > 2:
            calc_type = "Mixed / Unplanned for Extra Days"
            popup_msg = "⚠️ Notice: Monthly planned leave quota is capped at 2 days. Any excess days will be processed as Unplanned / LWP."
            
    elif l_type == "Sick Leave":
        cursor.execute("""
            SELECT COALESCE(SUM(total_days), 0) FROM leaves 
            WHERE emp_name = ? AND leave_type = 'Sick Leave' AND status != 'Rejected'
            AND strftime('%Y', from_date) = ?
        """, (emp_name, str(t_year)))
        year_sick_count = cursor.fetchone()[0]
        
        if year_sick_count >= 7:
            calc_type = "Planned / Unplanned (Sick Quota Exhausted)"
            popup_msg = "⚠️ Notice: Your annual quota of 7 Sick Leaves has been exhausted. Additional sick leaves will follow standard leave evaluation."
            
    conn.close()
    return calc_type, popup_msg

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
                st.success(f"Checked out successfully at {now_time}")
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
            reason_input = st.text_input("If 'No', please state the reason:", placeholder="e.g., Uniform being washed / Emergency")
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

    # Section 3: Leave Application Module
    st.markdown("### 🌴 Leave Application & Team Planner")
    st.info("💡 **Note:** You can apply for future planned leaves or record missed past leaves using the flexible date selection calendar below. Submitted requests will stay as **'Pending'** until approved by management.")
    
    with st.form("leave_apply_form", clear_on_submit=True):
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            leave_type = st.selectbox("Leave Type", ["Planned Leave", "Sick Leave", "Half-Day Leave", "Unplanned Leave"])
        with col_l2:
            date_range = st.date_input("Select Leave Date(s) [Flexible Calendar]", [now_ist.date(), now_ist.date()])
            
        leave_reason = st.text_area("Reason / Task Handover Notes", placeholder="State reason for leave and nominate team member handling tasks...")
        submit_leave = st.form_submit_button("📤 Submit Leave Application")
        
        if submit_leave:
            if isinstance(date_range, list) and len(date_range) == 2:
                f_date, t_date = date_range
            elif isinstance(date_range, tuple) and len(date_range) == 2:
                f_date, t_date = date_range
            else:
                f_date = t_date = date_range if not isinstance(date_range, list) else date_range[0]
                
            f_str = f_date.strftime("%Y-%m-%d")
            t_str = t_date.strftime("%Y-%m-%d")
            total_days = (t_date - f_date).days + 1
            
            calc_res, warning_msg = evaluate_leave_rules(selected_emp, leave_type, total_days, f_str)
            if warning_msg:
                st.warning(warning_msg)
                
            applied_ts = get_india_now().strftime("%Y-%m-%d %I:%M %p")
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO leaves (emp_name, leave_type, from_date, to_date, total_days, reason, status, calculated_type, applied_at)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
            """, (selected_emp, leave_type, f_str, t_str, total_days, leave_reason, calc_res, applied_ts))
            conn.commit()
            conn.close()
            st.success("Leave application submitted successfully! Status is currently **Pending**.")
            st.rerun()

    st.markdown("#### 📅 Team Leave Schedule & Transparency Board")
    conn = sqlite3.connect(DB_NAME)
    df_team_leaves = pd.read_sql_query("""
        SELECT emp_name as Employee, leave_type as 'Type', from_date as 'From', to_date as 'To', 
               total_days as Days, status as Status, calculated_type as 'Policy Category', reason as Reason
        FROM leaves ORDER BY leave_id DESC
    """, conn)
    conn.close()
    
    if not df_team_leaves.empty:
        st.dataframe(df_team_leaves, use_container_width=True, hide_index=True)
    else:
        st.info("No leave records found.")

    st.divider()

    # Section 4: Live Activity Tracker
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
        st.write("🟢 **No activity running right now. Select an activity to start:**")
        
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
    st.subheader("🔒 Admin Dashboard (Time, Dress Code, Leave Approvals & History)")
    
    selected_date = st.date_input("Select Single Date View", now_ist.date())
    date_str = selected_date.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)

    # Leave Approval Management Panel for Admin
    st.markdown("### 📥 Pending Leave Requests (Approval Panel)")
    df_pending_leaves = pd.read_sql_query("""
        SELECT leave_id, emp_name as Employee, leave_type as 'Type', from_date as 'From', to_date as 'To', 
               total_days as Days, calculated_type as 'Policy Applied', reason as Reason, applied_at as 'Applied At'
        FROM leaves WHERE status = 'Pending' ORDER BY leave_id DESC
    """, conn)
    
    if not df_pending_leaves.empty:
        st.dataframe(df_pending_leaves, use_container_width=True, hide_index=True)
        
        with st.form("admin_leave_action_form"):
            col_a1, col_a2, col_a3 = st.columns([2, 1, 1])
            with col_a1:
                selected_leave_id = st.selectbox("Select Leave ID to Process", df_pending_leaves['leave_id'].tolist())
            with col_a2:
                action_decision = st.selectbox("Action", ["Approve", "Reject / Not Approved"])
            with col_a3:
                submit_action = st.form_submit_button("Update Leave Status")
                
            if submit_action:
                new_status = "Approved" if action_decision == "Approve" else "Rejected"
                cursor = conn.cursor()
                cursor.execute("UPDATE leaves SET status = ? WHERE leave_id = ?", (new_status, selected_leave_id))
                conn.commit()
                st.success(f"Leave ID {selected_leave_id} status updated to **{new_status}**!")
                st.rerun()
    else:
        st.info("No pending leave requests right now.")

    st.divider()

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

        # Historical Leave Log
        st.markdown(f"##### 🌴 Leave History ({from_date_str} to {to_date_str})")
        params_leave = selected_staff_filter + [from_date_str, to_date_str]
        query_hist_leave = f"""
            SELECT from_date as 'From', to_date as 'To', emp_name as Employee, leave_type as Type, 
                   total_days as Days, status as Status, calculated_type as 'Policy Applied', reason as Reason
            FROM leaves 
            WHERE emp_name IN ({placeholders}) AND from_date BETWEEN ? AND ? 
            ORDER BY leave_id DESC
        """
        df_hist_leave = pd.read_sql_query(query_hist_leave, conn, params=params_leave)
        st.dataframe(df_hist_leave, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### 📥 Download Database Backup CSVs")
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    
    with col_d1:
        df_all_attn = pd.read_sql_query("SELECT * FROM attendance", conn)
        if not df_all_attn.empty:
            csv_attn = df_all_attn.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Attendance CSV", data=csv_attn, file_name=f"dk_attendance_{today_str}.csv", mime="text/csv", use_container_width=True)

    with col_d2:
        df_all_tasks_db = pd.read_sql_query("SELECT * FROM live_tasks", conn)
        if not df_all_tasks_db.empty:
            csv_tasks = df_all_tasks_db.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Tasks CSV", data=csv_tasks, file_name=f"dk_tasks_{today_str}.csv", mime="text/csv", use_container_width=True)

    with col_d3:
        df_all_dress = pd.read_sql_query("SELECT * FROM dress_code", conn)
        if not df_all_dress.empty:
            csv_dress = df_all_dress.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Dress Code CSV", data=csv_dress, file_name=f"dk_dress_{today_str}.csv", mime="text/csv", use_container_width=True)

    with col_d4:
        df_all_leaves = pd.read_sql_query("SELECT * FROM leaves", conn)
        if not df_all_leaves.empty:
            csv_leaves = df_all_leaves.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Leave Records CSV", data=csv_leaves, file_name=f"dk_leaves_{today_str}.csv", mime="text/csv", use_container_width=True)

    conn.close()

# ---------------------------------------------------------
# VIEW 3: POLICY & USER GUIDELINES (ENGLISH VERSION)
# ---------------------------------------------------------
elif mode == "📖 Policy & User Guidelines":
    st.subheader("📖 D.K. Enterprises - Tracker User Manual & Corporate Policies")
    st.markdown("This user guide provides step-by-step instructions for employees and management to effectively utilize the staff tracker and understand company policies.")

    st.markdown("---")

    # Step-by-Step Staff Workflow in English
    st.markdown("### 🧑‍💼 Part 1: Employee Daily Workflow")
    
    st.markdown("""
    1. **Step 1: Select Your Profile**  
       - Open the sidebar on the left and select your name (**Komal**, **Vijay**, or **Navinder**) from the **'Select Employee'** dropdown.
    
    2. **Step 2: Morning Check-In**  
       - Upon arrival at the office, navigate to **Staff Entry** mode and click the **🟢 Morning Check-In** button to log your arrival timestamp.

    3. **Step 3: Dress Code Verification**  
       - Submit your daily uniform verification (**Yes, Full Uniform** or **No / Casual**). If not wearing the prescribed uniform, provide a valid reason before submitting.

    4. **Step 4: Live Activity Tracking**  
       - Select your current activity type (e.g., **Production**, **Break**, or **Others**) and click **▶️ Start Activity Now**. 
       - *Note:* Initiating a new activity automatically concludes and calculates the duration of the previous task. Click **⏹️ Stop Current Activity** when completing your work session.

    5. **Step 5: Evening Check-Out**  
       - At the end of your shift, click the **🔴 Evening Check-Out** button to complete your daily log.
    """)

    st.markdown("---")

    # Leave Application & Policies Guide in English
    st.markdown("### 🌴 Part 2: Leave Application & Corporate Leave Rules")
    
    st.markdown("""
    - **Flexible Calendar Leave Requests:**  
      Employees can apply for future planned leaves or log past unrecorded leaves using the flexible date picker calendar.
    - **Pending Status Workflow:**  
      All submitted leave applications remain in **'Pending'** status until reviewed and approved by management.
    - **Team Transparency Board:**  
      The public Team Leave Board allows all team members to view upcoming leave schedules, ensuring smooth operational planning and workload management.
    
    **Corporate Leave Rules & Limits:**
    1. **Planned Leave Quota:** Each employee is entitled to **2 Planned Leaves** per month. Any additional planned leave requests will trigger a system notice and be categorized as **Unplanned / LWP**.
    2. **Annual Sick Leave Quota:** Employees receive an annual entitlement of **7 Sick Leaves**. Once exhausted, subsequent sick leaves follow standard leave evaluation policies.
    3. **Unplanned Leaves & LWP:** Unplanned absences exceeding allowed limits will be processed as Leave Without Pay (LWP).
    """)

    st.markdown("---")

    # Admin Dashboard Guide in English
    st.markdown("### 🔒 Part 3: Management & Admin Review Guide")
    
    st.markdown("""
    In **Admin Dashboard** mode, management has access to the following oversight controls:
    1. **Leave Approval Panel:**  
       Review all pending leave submissions, view policy calculations, and update request statuses to **'Approved'** or **'Rejected'**.
    2. **Daily Attendance & Uniform Compliance:**  
       Access daily attendance timestamps and uniform compliance logs for any selected date.
    3. **Historical Data & CSV Backups:**  
       Filter activity logs by date ranges and download secure CSV backups for attendance, task timelines, uniform records, and leave histories.
    """)
