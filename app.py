import streamlit as st
import datetime
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import pandas as pd
import io

from report_1 import generate_faculty_activity_report
from report_2 import generate_membership_breakdown_report
from report_3 import generate_activity_per_hub_report
from report_4 import generate_uos_non_uos_activity_report

# --- Set up Streamlit page ---
st.set_page_config(page_title="Mailchimp Report Generator for PCE Hubs", layout="centered")

# --- Load credentials from secrets.toml ---
config = {
    'credentials': yaml.safe_load(st.secrets["authentication"]["credentials"]),
    'cookie': {
        'name': st.secrets["authentication"]["cookie"],
        'key': st.secrets["authentication"]["key"],
        'expiry_days': st.secrets["authentication"]["expiry_days"]
    }
}

# --- Authenticator ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- Check if user is already logged in via session state ---
if 'authentication_status' not in st.session_state:
    st.session_state.authentication_status = None
if 'name' not in st.session_state:
    st.session_state.name = None
if 'username' not in st.session_state:
    st.session_state.username = None

# --- Login Widget ---
if st.session_state.authentication_status is None:
    login_result = authenticator.login(location="main")
    if login_result:
        name, authentication_status, username = login_result

        # Save the authentication status and username to session state
        st.session_state.authentication_status = authentication_status
        st.session_state.name = name
        st.session_state.username = username

# Handle authentication states
if st.session_state.authentication_status is False:
    st.error("Invalid username or password.")
elif st.session_state.authentication_status is None:
    st.warning("Please enter your username and password.")
elif st.session_state.authentication_status:
    # --- Main App Starts Here ---
    st.sidebar.success(f"Welcome, {st.session_state.name}!")
    authenticator.logout("Logout", "sidebar")

    st.title("📬 Mailchimp Reports for PCE Hubs")

    st.markdown("""
    Generate **membership** and **engagement** reports based on Mailchimp campaign and member data.

    - **Membership Report**: Shows total members per PCE Hub and their faculty affiliations.
    - **Engagement Report**: Tracks active members based on email open rates.

    > **Active**: A member is considered active if they've opened *at least one* email in the last 90 days.
    """)

    today = datetime.datetime.now().strftime("%d-%m-%Y")

    with st.form(key="report_form"):
        col1, col2 = st.columns(2)

        with col1:
            faculty_btn = st.form_submit_button("📘 Generate Faculty Activity Report")
            breakdown_btn = st.form_submit_button("📊 Generate Membership Breakdown Report")

        with col2:
            hub_btn = st.form_submit_button("🌐 Generate Activity per Hub Report")
            uos_btn = st.form_submit_button("🏫 Generate UoS vs Non-UoS Activity Report")

    def download_xlsx(result, filename):
        # Check if the result is a string (error message)
        if isinstance(result, str):
            st.error(result)
            return

        # Ensure result is a valid DataFrame
        if result is None or not isinstance(result, pd.DataFrame):
            st.error("No data to download!")
            return
    
        # Check if the DataFrame is empty
        if result.empty:
            st.error("The generated report is empty!")
            return

        # Prepare to save to an in-memory buffer
        towrite = io.BytesIO()

        # Create an Excel writer to write the DataFrame to the in-memory buffer
        with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
            # Write the DataFrame to the sheet
            result.to_excel(writer, index=False, sheet_name="Report")  # Make sure "Report" is the name of the sheet

        # Rewind the buffer for reading
        towrite.seek(0)

        # Provide download button
        st.download_button(
            label="📥 Download Excel",
            data=towrite,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    if faculty_btn:
        with st.spinner("Generating Faculty Activity Report..."):
            result = generate_faculty_activity_report()
        st.success(f"✅ Faculty Activity Report generated successfully! ({today})")
        download_xlsx(result, f"Faculty_Activity_Report_{today}.xlsx")

    if breakdown_btn:
        with st.spinner("Generating Membership Breakdown Report..."):
            result = generate_membership_breakdown_report()
        st.success(f"✅ Membership Breakdown Report generated successfully! ({today})")
        download_xlsx(result, f"Membership_Breakdown_{today}.xlsx")

    if hub_btn:
        with st.spinner("Generating Activity per Hub Report..."):
            result = generate_activity_per_hub_report()
        st.success(f"✅ Activity per Hub Report generated successfully! ({today})")
        download_xlsx(result, f"Activity_per_Hub_{today}.xlsx")

    if uos_btn:
        with st.spinner("Generating UoS vs Non-UoS Activity Report..."):
            result = generate_uos_non_uos_activity_report()
        st.success(f"✅ UoS vs Non-UoS Activity Report generated successfully! ({today})")
        download_xlsx(result, f"UoS_vs_Non_UoS_Activity_{today}.xlsx")
