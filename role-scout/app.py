import streamlit as st
import pandas as pd
import os
from location.overpass_client import get_coordinates, find_businesses_nearby
from utils.filters import clean_business_data
from scraper.browser import fetch_page_html
from scraper.parser import extract_emails, scan_for_roles

# --- CLOUD SETUP SNIPPET ---
# This ensures the cloud server downloads the browser binaries before running the app
os.system("playwright install chromium")
# ---------------------------

# Configure a clean, professional layout
st.set_page_config(page_title="Role Scout", page_icon="🎯", layout="wide")

# Custom styling to ensure a minimalist aesthetic
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { font-weight: 300; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

st.title("Role Scout: Firm Intelligence")
st.markdown("A highly targeted, locally hosted scraper for identifying professional consultancies and advisory firms.")

# Sidebar for search parameters
with st.sidebar:
    st.header("Search Parameters")
    street_name = st.text_input("Street Name", value="Union Street")
    city = st.text_input("City", value="Aberdeen")
    radius = st.slider("Search Radius (metres)", min_value=100, max_value=5000, value=1000, step=100)
    
    industry_focus = st.selectbox(
        "Industry Focus",
        options=["Engineering Consultancy", "Finance Consultancy", "Energy Services", "General Office"]
    )
    
    # Map the UI dropdown choices to the underlying OpenStreetMap tags
    tag_map = {
        "Engineering Consultancy": "office",
        "Finance Consultancy": "office", 
        "Energy Services": "commercial",
        "General Office": "office"
    }
    business_type = tag_map[industry_focus]

    fetch_button = st.button("1. Discover Firms", type="primary", use_container_width=True)

# State management ensures the table doesn't disappear when you click another button
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = []
if 'clean_df' not in st.session_state:
    st.session_state.clean_df = pd.DataFrame()

# --- Step 1: Location Discovery ---
if fetch_button:
    with st.spinner("Pinpointing location and querying OpenStreetMap..."):
        coords = get_coordinates(street_name, city)
        if coords:
            st.session_state.raw_data = find_businesses_nearby(coords[0], coords[1], radius, business_type)
            
            if st.session_state.raw_data:
                # Clean the data immediately using your filter module
                st.session_state.clean_df = clean_business_data(st.session_state.raw_data)
                st.success(f"Successfully identified {len(st.session_state.clean_df)} viable targets after filtering.")
            else:
                st.warning("No businesses found in this area. Try increasing the radius.")
        else:
            st.error("Could not find coordinates for that location.")

# --- Step 2: Deep Scraping ---
# Only show this section if we have successfully loaded a clean table of firms
if not st.session_state.clean_df.empty:
    st.subheader("Target Roster")
    st.dataframe(st.session_state.clean_df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Deep Analysis")
    st.markdown("Scan targeted websites for contact emails and early-career hiring signals (e.g., graduate, analyst, entry-level).")
    
    scrape_button = st.button("2. Initiate Deep Scrape", type="primary")
    
    if scrape_button:
        df = st.session_state.clean_df.copy()
        
        # Add blank columns to store our findings
        df["Contact Emails"] = ""
        df["Hiring Signals"] = ""
        
        progress_text = "Scanning targets. Please wait..."
        progress_bar = st.progress(0, text=progress_text)
        
        total_firms = len(df)
        
        # Iterate through the table, fetching HTML and parsing it for each firm
        for index, row in df.iterrows():
            url = row["Website"]
            
            # Update the progress bar so you aren't staring at a frozen screen
            progress_bar.progress((index) / total_firms, text=f"Analysing {row['Company Name']}...")
            
            html = fetch_page_html(url)
            if html:
                emails = extract_emails(html)
                roles = scan_for_roles(html)
                
                # Format the sets/lists into clean, readable strings
                df.at[index, "Contact Emails"] = ", ".join(emails) if emails else "None found"
                df.at[index, "Hiring Signals"] = ", ".join(roles).title() if roles else "No signals"
            else:
                df.at[index, "Contact Emails"] = "Scan failed"
                df.at[index, "Hiring Signals"] = "Scan failed"
                
        progress_bar.progress(1.0, text="Analysis complete.")
        st.session_state.clean_df = df
        
        st.subheader("Final Intelligence Report")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Create a button to export the final pandas DataFrame to a CSV file
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Report as CSV",
            data=csv,
            file_name=f"firm_intelligence_{city.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )