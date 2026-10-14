import streamlit as st
from datetime import datetime, date
import pandas as pd
from zoneinfo import ZoneInfo
from database import get_india_now, get_gspread_client, init_db
import gspread

init_db()

st.set_page_config(page_title="D.K. Enterprises - Daily Staff Tracker & Workboard", layout="wide")
st.title("📋 D.K. Enterprises - Daily Staff Tracker & Workboard")

st.sidebar.header("Navigation")

def fetch_df(table_name):
    client = get_gspread_client()
    sheet = client.open("Staff_Tracker_Database")
    ws = sheet.worksheet(table_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)

def insert_row(table_name, row_data):
    client = get_gspread_client()
    sheet = client.open("Staff_Tracker_Database")
    ws = sheet.worksheet(table_name)
    ws.append_row(row_data)

df_emp = fetch_df("dk_employees")
staff_list = df_emp['name'].tolist() if not df_emp.empty and 'name' in df_emp.columns else ["Komal", "Vijay", "Navinder"]

selected_emp = st.sidebar.selectbox("Select Employee", staff_list)

mode = st.sidebar.radio(
    "View Mode", 
    ["Staff Entry", "Admin Dashboard", "📖 Policy & User Guidelines"]
)

now_ist = get_india_now()
today_str = now_ist.strftime("%Y-%m-%d")

def update_attendance_checkout(emp_name, date_val, out_time):
    client = get_gspread_client()
    sheet = client.open("Staff_Tracker_Database")
    ws = sheet.worksheet("dk_attendance")
    records = ws.get_all_records()
    for idx, row in enumerate(records, start=2):
        if str(row.get("emp_name")) == str(emp_name) and str(row.get("date")) == str(date_val):
            ws.update_cell(idx, 5, out_time)
            return True
    return False

def evaluate_leave_rules(emp_name, l_type, l_days, target_date_str):
    df_leaves = fetch_df("dk_leaves")
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    t_year = target_dt.year
    t_month = target_dt.month
    
    calc_type = l_type
    popup_msg = ""
    
    if not df_leaves.empty and 'emp_name' in df_leaves.columns:
        if l_type == "Planned Leave":
            month_planned_count = 0
            for _, r in df_leaves.iterrows():
                if str(r['emp_name']) == emp_name and str(r['leave_type']) == 'Planned Leave' and str(r['status']) != 'Rejected':
                    f_d = str(r['from_date'])
                    try:
                        dt_f = datetime.strptime(f_d, "%Y-%m-%d")
                        if dt_f.year == t_year and dt_f.month == t_month:
                            month_planned_count += int(r['total_days'])
                    except:
                        pass
            
            if month_planned_count >= 2:
                calc_type = "Unplanned / LWP (Exceeded Monthly Planned Limit)"
                popup_msg = "⚠️ Notice: You have already exhausted your quota of 2 planned leaves for this month."
            elif (month_planned_count + l_days) > 2:
                calc_type = "Mixed / Unplanned for Extra Days"
                popup_msg = "⚠️ Notice: Monthly planned leave quota is capped at 2 days."
                
    return calc_type, popup_msg

# ---------------------------------------------------------
# VIEW 1: STAFF ENTRY
# ---------------------------------------------------------
if mode == "Staff Entry":
    st.subheader(f"Welcome, {selected_emp} 👋")
    
    st.markdown("### ⏰ Daily Attendance")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🟢 Morning Check-In", use_container_width=True):
            now_time = get_india_now().strftime("%I:%M %p")
            df_att = fetch_df("dk_attendance")
            already_in = False
            if not df_att.empty and 'emp_name' in df_att.columns:
                matched = df_att[(df_att['emp_name'] == selected_emp) & (df_att['date'] == today_str)]
                if not matched.empty:
                    already_in = True
                    
            if already_in:
                st.warning("Already checked in today!")
            else:
                new_id = len(df_att) + 1
                insert_row("dk_attendance", [new_id, selected_emp, today_str, now_time, ""])
                st.success(f"Checked in successfully at {now_time}")

    with col2:
        if st.button("🔴 Evening Check-Out", use_container_width=True):
            now_time = get_india_now().strftime("%I:%M %p")
            success = update_attendance_checkout(selected_emp, today_str, now_time)
            if success:
                st.success(f"Checked out successfully at {now_time}")
            else:
                st.warning("No check-in record found for today!")

    st.divider()

    st.markdown("### 👔 Daily Dress Code Verification")
    df_dress = fetch_df("dk_dress_code")
    today_dress = None
    if not df_dress.empty and 'emp_name' in df_dress.columns:
        matched = df_dress[(df_dress['emp_name'] == selected_emp) & (df_dress['date'] == today_str)]
        if not matched.empty:
            today_dress = matched.iloc[0]

    if today_dress is not None:
        st.success(f"✅ Today's Uniform Status Submitted: **{today_dress['in_uniform']}**" + (f" (Reason: {today_dress['reason']})" if today_dress['reason'] else ""))
    else:
        with st.form("dress_code_form", clear_on_submit=False):
            dress_opt = st.radio("Are you wearing the official office uniform / dress code today?", ["Yes, Full Uniform 🟢", "No / Casual / Partial 🔴"], horizontal=True)
            reason_input = st.text_input("If 'No', please state the reason:", placeholder="e.g., Uniform being washed / Emergency")
            submit_dress = st.form_submit_button("Submit Dress Code Status")

            if submit_dress:
                is_uniform = "Yes" if "Yes" in dress_opt else "No"
                now_ts = get_india_now().strftime("%Y-%m-%d %I:%M %p")
                new_id = len(df_dress) + 1
                insert_row("dk_dress_code", [new_id, selected_emp, today_str, is_uniform, reason_input if is_uniform == "No" else "-", now_ts])
                st.success("Dress code status recorded successfully!")
                st.rerun()

    st.divider()

    st.markdown("### ⏱️ Live Activity Tracker")
    df_tasks = fetch_df("dk_live_tasks")
    emp_today_tasks = pd.DataFrame()
    if not df_tasks.empty and 'emp_name' in df_tasks.columns:
        emp_today_tasks = df_tasks[(df_tasks['emp_name'] == selected_emp) & (df_tasks['date'] == today_str)]

    active_task = None
    if not emp_today_tasks.empty and 'status' in emp_today_tasks.columns:
        act_match = emp_today_tasks[emp_today_tasks['status'] == 'Ongoing']
        if not act_match.empty:
            active_task = act_match.iloc[0]

    if active_task is not None:
        st.info(f"⏳ Currently Active: **{active_task['activity_type']}** (Started at {active_task['start_time']})")
        if st.button("⏹️ Stop Current Activity", type="primary"):
            client = get_gspread_client()
            sheet = client.open("Staff_Tracker_Database")
            ws = sheet.worksheet("dk_live_tasks")
            records = ws.get_all_records()
            end_time_str = get_india_now().strftime("%I:%M %p")
            for idx, row in enumerate(records, start=2):
                if str(row.get("emp_name")) == str(selected_emp) and str(row.get("date")) == str(today_str) and str(row.get("status")) == "Ongoing":
                    ws.update_cell(idx, 6, end_time_str)
                    ws.update_cell(idx, 10, "Completed")
                    break
            st.success("Activity stopped and completed successfully!")
            st.rerun()
    else:
        with st.form("start_activity_form"):
            act_type = st.selectbox("Select Activity / Task Type", ["Production", "Quality Check", "Client Meeting", "Admin Work", "Break / Lunch", "Others"])
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
            desc = st.text_input("Task Description / Notes", placeholder="e.g., Working on client order processing...")
            start_act_btn = st.form_submit_button("▶️ Start New Activity")

            if start_act_btn:
                start_time_str = get_india_now().strftime("%I:%M %p")
                new_task_id = len(df_tasks) + 1 if not df_tasks.empty else 1
                insert_row("dk_live_tasks", [new_task_id, selected_emp, today_str, act_type, start_time_str, "In Progress...", "Running", desc, priority, "Ongoing"])
                st.success(f"Started '{act_type}' successfully!")
                st.rerun()

    st.markdown(f"#### 📊 Today's Activity Timeline for {selected_emp} ({today_str})")
    if not emp_today_tasks.empty:
        st.dataframe(emp_today_tasks[['activity_type', 'start_time', 'end_time', 'duration', 'task_desc', 'priority', 'status']].rename(
            columns={'activity_type': 'Activity', 'start_time': 'Start Time', 'end_time': 'End Time', 'duration': 'Duration', 'task_desc': 'Description', 'priority': 'Priority', 'status': 'Status'}
        ), use_container_width=True, hide_index=True)
    else:
        st.info("No activities recorded for today yet.")

    st.divider()

    st.markdown("### 🌴 Leave Application & Team Planner")
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
            df_l = fetch_df("dk_leaves")
            new_id = len(df_l) + 1
            insert_row("dk_leaves", [new_id, selected_emp, leave_type, f_str, t_str, total_days, leave_reason, "Pending", calc_res, applied_ts])
            st.success("Leave application submitted successfully! Status is currently **Pending**.")
            st.rerun()

    st.markdown("#### 📅 Team Leave Schedule & Transparency Board")
    df_team_leaves = fetch_df("dk_leaves")
    if not df_team_leaves.empty and 'emp_name' in df_team_leaves.columns:
        df_show = df_team_leaves[['emp_name', 'leave_type', 'from_date', 'to_date', 'total_days', 'status', 'calculated_type', 'reason']].rename(
            columns={'emp_name': 'Employee', 'leave_type': 'Type', 'from_date': 'From', 'to_date': 'To', 'total_days': 'Days', 'status': 'Status', 'calculated_type': 'Policy Category', 'reason': 'Reason'}
        )
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.info("No leave records found.")

# ---------------------------------------------------------
# VIEW 2: ADMIN DASHBOARD
# ---------------------------------------------------------
elif mode == "Admin Dashboard":
    st.subheader("🔒 Admin Dashboard (Time, Dress Code, Leave Approvals & History)")
    selected_date = st.date_input("Select Single Date View", now_ist.date())
    date_str = selected_date.strftime("%Y-%m-%d")

    st.markdown("### 📥 Pending Leave Requests (Approval Panel)")
    df_leaves_all = fetch_df("dk_leaves")
    if not df_leaves_all.empty and 'status' in df_leaves_all.columns:
        df_pend = df_leaves_all[df_leaves_all['status'] == 'Pending']
        if not df_pend.empty:
            for idx, row in df_pend.iterrows():
                col_info, col_app, col_rej = st.columns([4, 1, 1])
                with col_info:
                    st.write(f"**{row['emp_name']}** | {row['leave_type']} ({row['from_date']} to {row['to_date']}, {row['total_days']} days) | Reason: {row['reason']}")
                with col_app:
                    if st.button("Approve", key=f"app_{row['leave_id']}"):
                        client = get_gspread_client()
                        sheet = client.open("Staff_Tracker_Database")
                        ws = sheet.worksheet("dk_leaves")
                        records = ws.get_all_records()
                        for r_idx, r_val in enumerate(records, start=2):
                            if str(r_val.get("leave_id")) == str(row['leave_id']):
                                ws.update_cell(r_idx, 8, "Approved")
                                break
                        st.success("Approved!")
                        st.rerun()
                with col_rej:
                    if st.button("Reject", key=f"rej_{row['leave_id']}"):
                        client = get_gspread_client()
                        sheet = client.open("Staff_Tracker_Database")
                        ws = sheet.worksheet("dk_leaves")
                        records = ws.get_all_records()
                        for r_idx, r_val in enumerate(records, start=2):
                            if str(r_val.get("leave_id")) == str(row['leave_id']):
                                ws.update_cell(r_idx, 8, "Rejected")
                                break
                        st.warning("Rejected!")
                        st.rerun()
        else:
            st.info("No pending leave requests right now.")
    else:
        st.info("No leave requests found.")

    st.divider()

    st.markdown(f"### 📅 Attendance Summary for {date_str}")
    df_att_all = fetch_df("dk_attendance")
    if not df_att_all.empty and 'date' in df_att_all.columns:
        att_day = df_att_all[df_att_all['date'] == date_str]
        if not att_day.empty:
            st.dataframe(att_day[['emp_name', 'check_in', 'check_out']].rename(columns={'emp_name': 'Employee', 'check_in': 'Check In', 'check_out': 'Check Out'}), use_container_width=True, hide_index=True)
        else:
            st.info("No attendance records for this date.")
    else:
        st.info("No attendance data found.")

    st.markdown(f"### 👔 Uniform Compliance Summary for {date_str}")
    df_dress_all = fetch_df("dk_dress_code")
    if not df_dress_all.empty and 'date' in df_dress_all.columns:
        dress_day = df_dress_all[df_dress_all['date'] == date_str]
        if not dress_day.empty:
            st.dataframe(dress_day[['emp_name', 'in_uniform', 'reason', 'timestamp']].rename(columns={'emp_name': 'Employee', 'in_uniform': 'In Uniform', 'reason': 'Reason / Note', 'timestamp': 'Submitted At'}), use_container_width=True, hide_index=True)
        else:
            st.info("No dress code entries for this date.")
    else:
        st.info("No dress code data found.")

    st.markdown(f"### ⏱️ Live Staff Activity & Break Timeline for {date_str}")
    df_tasks_all = fetch_df("dk_live_tasks")
    if not df_tasks_all.empty and 'date' in df_tasks_all.columns:
        tasks_day = df_tasks_all[df_tasks_all['date'] == date_str]
        if not tasks_day.empty:
            st.dataframe(tasks_day[['emp_name', 'activity_type', 'start_time', 'end_time', 'duration', 'task_desc', 'priority', 'status']].rename(
                columns={'emp_name': 'Employee', 'activity_type': 'Activity', 'start_time': 'Start Time', 'end_time': 'End Time', 'duration': 'Duration', 'task_desc': 'Description', 'priority': 'Priority', 'status': 'Status'}
            ), use_container_width=True, hide_index=True)
        else:
            st.info("No activities recorded for this date.")
    else:
        st.info("No task activity data found.")

    st.divider()
    st.markdown("### 🔍 Past Data History Search & Filter")
    f_emp_filter = st.multiselect("Filter Employee(s)", staff_list, default=staff_list)
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        d_from = st.date_input("From Date", now_ist.date())
    with col_f2:
        d_to = st.date_input("To Date", now_ist.date())
        
    d_from_str = d_from.strftime("%Y-%m-%d")
    d_to_str = d_to.strftime("%Y-%m-%d")
    
    st.markdown(f"#### 📜 Activity History ({d_from_str} to {d_to_str})")
    if not df_tasks_all.empty:
        filtered_tasks = df_tasks_all[df_tasks_all['emp_name'].isin(f_emp_filter) & df_tasks_all['date'].between(d_from_str, d_to_str)]
        if not filtered_tasks.empty:
            st.dataframe(filtered_tasks[['date', 'emp_name', 'activity_type', 'start_time', 'end_time', 'duration', 'task_desc', 'status']].rename(
                columns={'date': 'Date', 'emp_name': 'Employee', 'activity_type': 'Activity', 'start_time': 'Start Time', 'end_time': 'End Time', 'duration': 'Duration', 'task_desc': 'Description', 'status': 'Status'}
            ), use_container_width=True, hide_index=True)
        else:
            st.info("No records found in this date range.")

    st.markdown(f"#### 🌴 Leave History ({d_from_str} to {d_to_str})")
    if not df_leaves_all.empty:
        filtered_leaves = df_leaves_all[df_leaves_all['emp_name'].isin(f_emp_filter)]
        if not filtered_leaves.empty:
            st.dataframe(filtered_leaves[['from_date', 'to_date', 'emp_name', 'leave_type', 'total_days', 'status', 'calculated_type', 'reason']].rename(
                columns={'from_date': 'From', 'to_date': 'To', 'emp_name': 'Employee', 'leave_type': 'Type', 'total_days': 'Days', 'status': 'Status', 'calculated_type': 'Policy Applied', 'reason': 'Reason'}
            ), use_container_width=True, hide_index=True)
        else:
            st.info("No leave records found in this range.")

    st.divider()
    st.markdown("### 📥 Download Database Backup CSVs")
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        if not df_att_all.empty:
            st.download_button("📥 Attendance CSV", df_att_all.to_csv(index=False), "dk_attendance_backup.csv", "text/csv")
    with col_c2:
        if not df_tasks_all.empty:
            st.download_button("📥 Tasks CSV", df_tasks_all.to_csv(index=False), "dk_tasks_backup.csv", "text/csv")
    with col_c3:
        if not df_dress_all.empty:
            st.download_button("📥 Dress Code CSV", df_dress_all.to_csv(index=False), "dk_dress_code_backup.csv", "text/csv")
    with col_c4:
        if not df_leaves_all.empty:
            st.download_button("📥 Leave Records CSV", df_leaves_all.to_csv(index=False), "dk_leaves_backup.csv", "text/csv")

# ---------------------------------------------------------
# VIEW 3: POLICY & GUIDELINES
# ---------------------------------------------------------
elif mode == "📖 Policy & User Guidelines":
    st.subheader("📖 D.K. Enterprises - Tracker User Manual & Corporate Policies")
    st.markdown("""
    This user guide provides step-by-step instructions for employees and management to effectively utilize the staff tracker and understand company policies.

    ---

    ### 👤 Part 1: Employee Daily Workflow

    1. **Step 1: Select Your Profile**
       - Open the sidebar on the left and select your name from the **'Select Employee'** dropdown.
    2. **Step 2: Morning Check-In**
       - Upon arrival at the office, navigate to **Staff Entry** mode and click the 🟢 **Morning Check-In** button to log your arrival timestamp.
    3. **Step 3: Dress Code Verification**
       - Submit your daily uniform verification (**Yes, Full Uniform** or **No / Casual**). If not wearing the prescribed uniform, provide a valid reason before submitting.
    4. **Step 4: Live Activity Tracking**
       - Select your current activity type (e.g., **Production, Break, or Others**) and click ▶️ **Start Activity Now**.
       - *Note:* Initiating a new activity automatically concludes and calculates the duration of the previous task. Click ⏹️ **Stop Current Activity** when completing your work session.
    5. **Step 5: Evening Check-Out**
       - At the end of your shift, click the 🔴 **Evening Check-Out** button to complete your daily log.

    ---

    ### 🌴 Part 2: Leave Application & Corporate Leave Rules

    * **Flexible Calendar Leave Requests:** Employees can apply for future planned leaves or log past unrecorded leaves using the flexible date picker calendar.
    * **Pending Status Workflow:** All submitted leave applications remain in **'Pending'** status until reviewed and approved by management.
    * **Team Transparency Board:** The public Team Leave Board allows all team members to view upcoming leave schedules, ensuring smooth operational planning and workload management.

    **Corporate Leave Rules & Limits:**
    1. **Planned Leave Quota:** Each employee is entitled to **2 Planned Leaves** per month. Any additional planned leave requests will trigger a system notice and be categorized as **Unplanned / LWP**.
    2. **Annual Sick Leave Quota:** Employees receive an annual entitlement of **7 Sick Leaves**. Once exhausted, subsequent sick leaves follow standard leave evaluation policies.
    3. **Unplanned Leaves & LWP:** Unplanned absences exceeding allowed limits will be processed as Leave Without Pay (LWP).

    ---

    ### 🔒 Part 3: Management & Admin Review Guide

    In **Admin Dashboard** mode, management has access to the following oversight controls:

    1. **Leave Approval Panel:**
       - Review all pending leave submissions, view policy calculations, and update request statuses to **'Approved'** or **'Rejected'**.
    2. **Daily Attendance & Uniform Compliance:**
       - Access daily attendance timestamps and uniform compliance logs for any selected date.
    3. **Historical Data & CSV Backups:**
       - Filter activity logs by date ranges and download secure CSV backups for attendance, task timelines, uniform records, and leave histories.
    """)
