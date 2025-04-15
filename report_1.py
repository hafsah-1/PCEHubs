import requests
import datetime
import pandas as pd
import streamlit as st

# === CONFIG ===
API_KEY = st.secrets["mailchimp"]["api_key"]
SERVER_PREFIX = st.secrets["mailchimp"]["server_prefix"]
LIST_ID = st.secrets["mailchimp"]["list_id"]
BASE_URL = f'https://{SERVER_PREFIX}.api.mailchimp.com/3.0'
HEADERS = {
    'Authorization': f'Bearer {API_KEY}'
}

# === Map Faculty IDs to Faculty Names ===
faculty_interests = {
    'fbc13fadbd': 'FAH (Faculty of Arts & Humanities)',
    '2ce4176b3e': 'FELS (Faculty of Environmental & Life Sciences)',
    '9ffaf45dc1': 'FEPS (Faculty of Engineering & Physical Sciences)',
    'dfb73b828c': 'FM (Faculty of Medicine)',
    '2662784a17': 'FSS (Faculty of Social Sciences)',
    '829422230f': 'Professional Services'
}

# === Date 90 days ago (timezone-aware) ===
since_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).isoformat()

# === Get subscribed list members with Faculty interests ===
def get_list_members():
    members = {faculty: set() for faculty in faculty_interests.values()}
    offset = 0
    while True:
        url = f"{BASE_URL}/lists/{LIST_ID}/members"
        params = {"offset": offset, "count": 1000, "status": "subscribed"}
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json().get("members", [])
        if not data:
            break
        for m in data:
            email = m["email_address"].lower()
            interests = m.get("interests", {})
            for faculty_id, faculty_name in faculty_interests.items():
                if interests.get(faculty_id, False):
                    members[faculty_name].add(email)
        offset += len(data)
    return members

# === Get campaigns from last 90 days ===
def get_recent_campaigns():
    url = f"{BASE_URL}/campaigns"
    params = {
        "since_send_time": since_date,
        "status": "sent",
        "count": 1000
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json().get('campaigns', [])

# === Get email activity per campaign ===
def get_email_activity(campaign_id):
    email_activities = []
    offset = 0
    while True:
        url = f"{BASE_URL}/reports/{campaign_id}/email-activity"
        params = {"offset": offset, "count": 1000}
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json().get("emails", [])
        if not data:
            break
        email_activities.extend(data)
        offset += len(data)
    return email_activities

# === Track opens across campaigns for each faculty ===
def build_open_activity_set(campaigns, faculty_members):
    active_faculty_members = {faculty: set() for faculty in faculty_members}

    for campaign in campaigns:
        email_activities = get_email_activity(campaign['id'])
        for email in email_activities:
            actions = email.get('activity', [])
            if any(action["action"] == "open" for action in actions):
                email_address = email['email_address'].lower()
                for faculty, members in faculty_members.items():
                    if email_address in members:
                        active_faculty_members[faculty].add(email_address)

    return active_faculty_members

# === Generate Faculty activity report without arguments ===
def generate_faculty_activity_report(export_path="faculty_activity.xlsx"):
    # Fetch the list members and campaigns inside the function
    print("Getting subscribed members from the list...")
    faculty_members = get_list_members()
    print(f"List has {sum(len(members) for members in faculty_members.values())} active subscribed members.")

    print("Fetching recent campaigns (last 90 days)...")
    campaigns = get_recent_campaigns()
    print(f"Found {len(campaigns)} campaigns.")

    print("Gathering email open activity...")
    active_faculty_members = build_open_activity_set(campaigns, faculty_members)

    # Now create the report
    report_data = []
    for faculty, members in faculty_members.items():
        total = len(members)
        active = len(active_faculty_members.get(faculty, set()))
        pct_active = (active / total * 100) if total > 0 else 0
        report_data.append({
            "Faculty": faculty,
            "Total Members": total,
            "Active Members": active,
            "Active %": f"{pct_active:.2f}%"
        })

    # Print to terminal
    print(f"\n{'Faculty':30s} | Total Members | Active Members | Active %")
    print("-" * 58)
    for row in report_data:
        print(f"{row['Faculty']:30s} | {row['Total Members']:>13} | {row['Active Members']:>15} | {row['Active %']}")

    # Generate the export path with the current date
    filename_with_date = export_path.split(".")[0] + "_" + datetime.datetime.now().strftime("%d%m%Y") + ".xlsx"

    # Write to Excel
    df = pd.DataFrame(report_data)
    df.to_excel(filename_with_date, index=False)
    print(f"\n✅ Report exported to: {filename_with_date}")
    
    # Return df for Streamlit download
    return df

# === RUN ===
if __name__ == "__main__":
    generate_faculty_activity_report()  # Run the report generation when script is executed
