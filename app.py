import streamlit as st
from datetime import datetime, date
import pandas as pd
from zoneinfo import ZoneInfo
from database import get_india_now, get_gspread_client, init_db
import gspread

init_db()

st.set_page_config(page_title="D.K. Enterprises Staff Tracker", layout="wide")
st.title("📋 D.K. Enterprises - Daily Staff Tracker & Workboard")

st.sidebar.header("Navigation")
staff_list = ["Komal", "Vijay", "Navinder"]
selected_emp = st.sidebar.selectbox("Select Employee", staff_list)

mode = st.sidebar.radio(
    "View Mode", 
    ["Staff Entry", "Admin Dashboard", "📖 Policy & User Guidelines"]
)

now_ist = get_india_now()
today_str = now_ist.strftime("%Y-%m-%d")

# Helper to read table as DataFrame
def fetch_df(table_name):
    client = get_gspread_client()
    sheet = client.open("Staff_Tracker_Database")
    ws = sheet.worksheet(table_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)

# Helper to insert row
def insert_row(table_name, row_data):
    client = get_gspread_client()
    sheet = client.open("Staff_Tracker_Database")
    ws = sheet.worksheet(table_name)
    ws.append_row(row_data)

# Helper to update cell/row dynamically
def update_attendance_checkout(emp_name, date_val, out_time):
    client = get_gspread_client()
    sheet = client.open("Staff_Tracker_Database")
    ws = sheet.worksheet("dk_attendance")
    records = ws.get_all_records()
    for idx, row in enumerate(records, start=2): # row 1 is header
        if str(row.get("emp_name")) == str(emp_name) and str(row.get("date")) == str(date_val):
            ws.update_cell(idx, 5, out_time) # column 5 is check_out
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
            # Filter for same month/year & approved/pending
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
                # find next id
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
    st.subheader("🔒 Admin Dashboard")
    selected_date = st.date_input("Select Single Date View", now_ist.date())
    date_str = selected_date.strftime("%Y-%m-%d")

    st.markdown("### 📥 Pending Leave Requests")
    df_leaves_all = fetch_df("dk_leaves")
    if not df_leaves_all.empty and 'status' in df_leaves_all.columns:
        df_pend = df_leaves_all[df_leaves_all['status'] == 'Pending']
        if not df_pend.empty:
            st.dataframe(df_pend, use_container_width=True, hide_index=True)
        else:
            st.info("No pending leave requests right now.")
    else:
        st.info("No leave requests found.")

# ---------------------------------------------------------
# VIEW 3: POLICY & GUIDELINES
# ---------------------------------------------------------
elif mode == "📖 Policy & User Guidelines":
    st.subheader("📖 D.K. Enterprises - Tracker User Manual & Corporate Policies")
    st.markdown("This guide provides step-by-step instructions for utilizing the staff tracker and understanding company leave rules.")
