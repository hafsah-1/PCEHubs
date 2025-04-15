import requests
import datetime
import pandas as pd
from requests.auth import HTTPBasicAuth
import streamlit as st

# === CONFIG ===
API_KEY = st.secrets["mailchimp"]["api_key"]
DC = st.secrets["mailchimp"]["server_prefix"]
LIST_ID = st.secrets["mailchimp"]["list_id"]

# Map the interest keys to their respective PCE Hub themes
interest_keys = {
    '53f1e5e98a': 'Nature, Biodiversity & Sustainability',
    '1b8933d69f': 'Health & Wellbeing',
    '908333b451': 'Future Cities',
    '28a8c2775a': 'Artificial Intelligence (AI) & Society'
}

# Map the faculty IDs to their respective faculties
faculty_interests = {
    'fbc13fadbd': 'FAH (Faculty of Arts & Humanities)',
    '2ce4176b3e': 'FELS (Faculty of Environmental & Life Sciences)',
    '9ffaf45dc1': 'FEPS (Faculty of Engineering & Physical Sciences)',
    'dfb73b828c': 'FM (Faculty of Medicine)',
    '2662784a17': 'FSS (Faculty of Social Sciences)',
    '829422230f': 'Professional Services'
}

# Function to generate the membership breakdown report
def generate_membership_breakdown_report():
    # API Endpoint for fetching members
    url = f'https://{DC}.api.mailchimp.com/3.0/lists/{LIST_ID}/members?count=1000'

    # Basic Auth
    auth = HTTPBasicAuth('anystring', API_KEY)

    # Make request to fetch members
    response = requests.get(url, auth=auth)
    print("Status Code:", response.status_code)

    if response.status_code == 200:
        data = response.json()

        if 'members' in data:
            hubs_counts = {
                theme: {
                    'total': 0,
                    'non_current': 0,
                    'current': 0,
                    'alumni': 0,
                    'faculties': {
                        faculty: {'total': 0} for faculty in faculty_interests.values()
                    }
                }
                for theme in interest_keys.values()
            }

            # Process each member
            for member in data['members']:
                if member['status'] != 'subscribed':
                    continue

                hubs_interested = []
                for key, theme in interest_keys.items():
                    if member.get('interests', {}).get(key, False):
                        hubs_interested.append(theme)
                        hubs_counts[theme]['total'] += 1

                faculty_interested = []
                for faculty_id, faculty_name in faculty_interests.items():
                    if member.get('interests', {}).get(faculty_id, False):
                        faculty_interested.append(faculty_name)
                        for theme in hubs_interested:
                            hubs_counts[theme]['faculties'][faculty_name]['total'] += 1

                is_current_uos = member.get('merge_fields', {}).get('MMERGE7') == 'Yes'
                if is_current_uos:
                    for theme in hubs_interested:
                        hubs_counts[theme]['current'] += 1
                else:
                    for theme in hubs_interested:
                        hubs_counts[theme]['non_current'] += 1

                alumni_status = member.get('merge_fields', {}).get('MMERGE8') == 'Yes'
                if alumni_status:
                    for theme in hubs_interested:
                        hubs_counts[theme]['alumni'] += 1

            # Prepare the report data
            report_data = []
            report_date = datetime.datetime.now().strftime("%Y-%m-%d")

            for hub, counts in hubs_counts.items():
                hub_data = {
                    'PCE Hub': hub,
                    'Total UoS': counts['total'],
                    'Non-Current UoS': counts['non_current'],
                    'Current UoS': counts['current'],
                    'Alumni': counts['alumni'],
                    'FAH': counts['faculties'].get('FAH (Faculty of Arts & Humanities)', {}).get('total', 0),
                    'FELS': counts['faculties'].get('FELS (Faculty of Environmental & Life Sciences)', {}).get('total', 0),
                    'FEPS': counts['faculties'].get('FEPS (Faculty of Engineering & Physical Sciences)', {}).get('total', 0),
                    'FM': counts['faculties'].get('FM (Faculty of Medicine)', {}).get('total', 0),
                    'FSS': counts['faculties'].get('FSS (Faculty of Social Sciences)', {}).get('total', 0),
                    'PS': counts['faculties'].get('Professional Services', {}).get('total', 0),
                }
                report_data.append(hub_data)

            # All hubs row
            all_hubs_row = {
                'PCE Hub': 'All Hubs',
                'Total UoS': sum(1 for member in data['members'] if member['status'] == 'subscribed'),
                'Non-Current UoS': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('merge_fields', {}).get('MMERGE7') == 'No'),
                'Current UoS': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('merge_fields', {}).get('MMERGE7') == 'Yes'),
                'Alumni': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('merge_fields', {}).get('MMERGE8') == 'Yes'),
                'FAH': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('interests', {}).get('fbc13fadbd', False)),
                'FELS': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('interests', {}).get('2ce4176b3e', False)),
                'FEPS': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('interests', {}).get('9ffaf45dc1', False)),
                'FM': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('interests', {}).get('dfb73b828c', False)),
                'FSS': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('interests', {}).get('2662784a17', False)),
                'PS': sum(1 for member in data['members'] if member['status'] == 'subscribed' and member.get('interests', {}).get('829422230f', False)),
                'Report Date': report_date
            }
            report_data.insert(0, all_hubs_row)

            # Create the Excel file using pandas
            df = pd.DataFrame(report_data)

            # Generate the export path with the current date
            filename_with_date = f"pce_hub_report_{datetime.datetime.now().strftime('%d%m%Y')}.xlsx"

            # Save to local file (optional, for your own records)
            df.to_excel(filename_with_date, index=False)

            print(f"\n✅ Report exported to: {filename_with_date}")

            # Return the DataFrame for Streamlit download
            return df

        else:
            print("❌ No members found in the response.")
            return "❌ No members found in the response."
    else:
        print("❌ Failed to fetch data")
        return "❌ Failed to fetch data"
