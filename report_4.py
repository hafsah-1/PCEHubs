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

# === Date 90 days ago (timezone-aware)
since_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).isoformat()

# === Get subscribed list members with UOS classification ===
def get_list_members():
    members = {"UOS": set(), "Non-UOS": set()}
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
            merge7_value = m.get("merge_fields", {}).get("MMERGE7", "").strip().lower()
            if merge7_value == 'yes':
                members["UOS"].add(email)
            else:
                members["Non-UOS"].add(email)
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

# === Track opens across campaigns ===
def build_open_activity_set(campaigns, uos_emails, non_uos_emails):
    active_uos_emails = set()
    active_non_uos_emails = set()

    for campaign in campaigns:
        email_activities = get_email_activity(campaign['id'])
        for email in email_activities:
            actions = email.get('activity', [])
            if any(action["action"] == "open" for action in actions):
                email_address = email['email_address'].lower()
                if email_address in uos_emails:
                    active_uos_emails.add(email_address)
                elif email_address in non_uos_emails:
                    active_non_uos_emails.add(email_address)

    return active_uos_emails, active_non_uos_emails

# === Generate UOS and Non-UOS activity report ===
def generate_uos_non_uos_activity_report(export_path="uos_activity.xlsx"):
    # Fetch members and campaigns inside the function
    print("Getting subscribed members from the list...")
    members = get_list_members()
    print(f"List has {len(members['UOS']) + len(members['Non-UOS'])} active subscribed members.")

    print("Fetching recent campaigns (last 90 days)...")
    campaigns = get_recent_campaigns()
    print(f"Found {len(campaigns)} campaigns.")

    print("Gathering email open activity...")
    active_uos_emails, active_non_uos_emails = build_open_activity_set(campaigns, members["UOS"], members["Non-UOS"])

    # Calculate totals and percentages
    uos_total = len(members["UOS"])
    uos_active = len(active_uos_emails)
    non_uos_total = len(members["Non-UOS"])
    non_uos_active = len(active_non_uos_emails)

    uos_pct = (uos_active / uos_total * 100) if uos_total > 0 else 0
    non_uos_pct = (non_uos_active / non_uos_total * 100) if non_uos_total > 0 else 0

    # Debug printouts to verify calculations
    print(f"UOS: ({uos_active} / {uos_total}) * 100 = {uos_pct:.2f}%")
    print(f"Non-UOS: ({non_uos_active} / {non_uos_total}) * 100 = {non_uos_pct:.2f}%")

    summary = [
        {
            "Category": "UOS",
            "Members": uos_total,
            "Active": uos_active,
            "Active %": f"{uos_pct:.2f}%"
        },
        {
            "Category": "Non-UOS",
            "Members": non_uos_total,
            "Active": non_uos_active,
            "Active %": f"{non_uos_pct:.2f}%"
        }
    ]

    # Print to terminal
    print(f"\n{'Category':10s} | Members | Active | Active %")
    print("-" * 42)
    for row in summary:
        print(f"{row['Category']:10s} | {row['Members']:>7} | {row['Active']:>6} | {row['Active %']}")

    # Generate the export path with the current date
    filename_with_date = export_path.split(".")[0] + "_" + datetime.datetime.now().strftime("%d%m%Y") + ".xlsx"

    # Write to Excel
    df = pd.DataFrame(summary)
    df.to_excel(filename_with_date, index=False)
    print(f"\n✅ Report exported to: {filename_with_date}")
    
    # Return df for Streamlit download
    return df

# === RUN ===
if __name__ == "__main__":
    generate_uos_non_uos_activity_report()  # Run the report generation when script is executed
