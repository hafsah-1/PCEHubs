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

# === Constants for Hub IDs ===
HUB_INTERESTS = {
    "Artificial Intelligence (AI) & Society": "28a8c2775a",
    "Health & Wellbeing": "1b8933d69f",
    "Nature, Biodiversity & Sustainability": "53f1e5e98a",
    "Future Cities": "908333b451"
}

# === Date 90 days ago (timezone-aware)
since_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).isoformat()

# === Get subscribed list members and their interests ===
def get_list_members():
    members = {}
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
            members[email] = {
                "interests": [k for k, v in interests.items() if v]
            }
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
def build_open_activity_set(campaigns):
    active_emails = set()
    for campaign in campaigns:
        email_activities = get_email_activity(campaign['id'])
        for email in email_activities:
            actions = email.get('activity', [])
            if any(action["action"] == "open" for action in actions):
                active_emails.add(email['email_address'].lower())
    return active_emails

# === Build and export final report ===
def generate_activity_per_hub_report(export_path="hub_activity_report.xlsx"):
    # Fetch members and campaigns inside the function
    print("Getting subscribed members and interests...")
    members = get_list_members()
    print(f"Retrieved {len(members)} subscribed members.")
    
    print("Fetching recent campaigns (last 90 days)...")
    campaigns = get_recent_campaigns()
    print(f"Found {len(campaigns)} campaigns.")
    
    print("Gathering email open activity...")
    active_emails = build_open_activity_set(campaigns)

    # Generate the summary for each hub
    summary = []
    for hub_name, hub_id in HUB_INTERESTS.items():
        hub_members = [email for email, data in members.items() if hub_id in data["interests"]]
        active_hub_members = [email for email in hub_members if email in active_emails]
        total = len(hub_members)
        active = len(active_hub_members)
        rate = (active / total * 100) if total > 0 else 0
        summary.append({
            "Hub": hub_name,
            "Members": total,
            "Active": active,
            "Active %": f"{rate:.2f}%"
        })

    # Print to terminal
    print(f"\n{'Hub':40s} | Members | Active | Active %")
    print("-" * 65)
    for row in summary:
        print(f"{row['Hub']:40s} | {row['Members']:>7} | {row['Active']:>6} | {row['Active %']}")

    # Write to Excel
    df = pd.DataFrame(summary)
    df.to_excel(export_path, index=False)
    print(f"\n✅ Report exported to: {export_path}")
    
    # Return df for Streamlit download
    return df

# === RUN ===
if __name__ == "__main__":
    generate_activity_per_hub_report()  # Run the report generation when script is executed
