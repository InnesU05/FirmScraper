import streamlit as st
import pandas as pd
import os
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from location.overpass_client import get_coordinates, find_businesses_in_polygon, find_businesses_nearby
from utils.filters import clean_business_data
from scraper.browser import fetch_page_html
from scraper.parser import extract_emails, scan_for_keywords, extract_linkedin
from utils.constants import FIRM_CATEGORIES, JOB_ROLES

# --- CLOUD SETUP SNIPPET ---
os.system("playwright install chromium")
# ---------------------------

st.set_page_config(page_title="Role Scout", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { font-weight: 300; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

st.title("Role Scout: Advanced Firm Intelligence")
st.markdown("Isolate boutique consultancies and finance firms using geospatial targeting and deep text analysis.")

# State management
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = []
if 'clean_df' not in st.session_state:
    st.session_state.clean_df = pd.DataFrame()

@st.cache_data(show_spinner=False)
def cached_get_coordinates(street, city):
    return get_coordinates(street, city)

# Sidebar Setup
with st.sidebar:
    st.header("1. Geospatial Focus")
    street_name = st.text_input("Street Name (to centre map)", value="Union Street")
    city = st.text_input("City", value="Aberdeen")
    search_mode = st.radio("Select Target Method", ["Draw Perimeter", "Radius Search"])
    
    if search_mode == "Radius Search":
        radius = st.slider("Search Radius (metres)", min_value=100, max_value=5000, value=1000, step=100)
    else:
        radius = None
        
    st.divider()
    
    st.header("2. Firm Identity (Deep Scrape)")
    st.markdown("We pull all offices from the map. The scraper will scan their websites for these exact terms to verify what they do.")
    
    all_categories = st.checkbox("Select All Industry Categories", value=False)
    if all_categories:
        selected_cats = list(FIRM_CATEGORIES.keys())
    else:
        selected_cats = st.multiselect("Select Industry Categories", list(FIRM_CATEGORIES.keys()), default=["Core Finance and Banking"])
        
    available_firm_types = []
    for cat in selected_cats:
        available_firm_types.extend(FIRM_CATEGORIES[cat])
        
    all_firm_types = st.checkbox("Select All Firm Types in Chosen Categories", value=True)
    if all_firm_types:
        final_firm_types = available_firm_types
    else:
        final_firm_types = st.multiselect("Select Specific Firm Types", available_firm_types, default=available_firm_types[:5] if available_firm_types else [])

    st.divider()
    
    st.header("3. Hiring Signals")
    all_roles = st.checkbox("Select All Job Roles", value=False)
    if all_roles:
        final_job_roles = JOB_ROLES
    else:
        final_job_roles = st.multiselect(
            "Select Job Roles", 
            JOB_ROLES, 
            default=["Finance analyst", "Graduate finance", "Commercial analyst"]
        )

# --- Step 1: Map & Location ---
coords = cached_get_coordinates(street_name, city)

if coords:
    if search_mode == "Draw Perimeter":
        m = folium.Map(location=[coords[0], coords[1]], zoom_start=15)
        draw_options = {
            'polyline': False, 'circlemarker': False, 'marker': False, 'circle': False,
            'polygon': True, 'rectangle': True
        }
        Draw(export=False, draw_options=draw_options).add_to(m)
        
        st.markdown("### Select Search Area")
        st.info("Use the ⬛ (Rectangle) or ⬟ (Polygon) tools on the map to draw your specific search zone.")
        
        map_data = st_folium(m, width=1000, height=500, key="perimeter_map")
        
        if map_data and map_data.get("last_active_drawing"):
            st.success("Perimeter locked. Ready to scan.")
            fetch_button = st.button("Discover Offices in Perimeter", type="primary", use_container_width=True)
            
            if fetch_button:
                geom = map_data["last_active_drawing"]["geometry"]
                if geom["type"] == "Polygon":
                    with st.spinner("Pulling all commercial nodes from map..."):
                        raw_coords = geom["coordinates"][0]
                        polygon_coords = [(lat, lon) for lon, lat in raw_coords]
                        
                        st.session_state.raw_data = find_businesses_in_polygon(polygon_coords)
                        
                        if st.session_state.raw_data:
                            st.session_state.clean_df = clean_business_data(st.session_state.raw_data)
                            st.success(f"Identified {len(st.session_state.clean_df)} valid commercial offices.")
                        else:
                            st.warning("No commercial offices found in that specific shape. Try drawing a wider area.")

    elif search_mode == "Radius Search":
        m = folium.Map(location=[coords[0], coords[1]], zoom_start=14)
        
        folium.Circle(
            location=[coords[0], coords[1]],
            radius=radius,
            color="#FF4B4B",
            fill=True,
            fill_color="#FF4B4B"
        ).add_to(m)
        
        st.markdown("### Search Radius")
        st.info(f"Targeting all commercial locations within a {radius} metre radius.")
        
        st_folium(m, width=1000, height=500, key="radius_map")
        
        fetch_button = st.button("Discover Offices in Radius", type="primary", use_container_width=True)
        if fetch_button:
            with st.spinner(f"Pulling all commercial nodes within {radius}m..."):
                st.session_state.raw_data = find_businesses_nearby(coords[0], coords[1], radius)
                
                if st.session_state.raw_data:
                    st.session_state.clean_df = clean_business_data(st.session_state.raw_data)
                    st.success(f"Identified {len(st.session_state.clean_df)} valid commercial offices.")
                else:
                    st.warning("No commercial offices found in this area. Try increasing the radius.")
else:
    st.error("⚠️ Could not load the map. The coordinate server might be busy, or the location is misspelled. Please wait 5 seconds and refresh.")

# --- Step 2: Deep Scraping ---
if not st.session_state.clean_df.empty:
    st.divider()
    st.subheader("Target Roster")
    st.dataframe(st.session_state.clean_df, use_container_width=True, hide_index=True)
    
    st.subheader("Deep Analysis")
    st.markdown("The scraper will now visit these websites and cross-reference the text against your selected parameters.")
    
    scrape_button = st.button("Initiate Deep Scrape", type="primary")
    
    if scrape_button:
        df = st.session_state.clean_df.copy()
        df["Verified Identity (Website Match)"] = ""
        df["Hiring Signals"] = ""
        df["Contact Emails"] = ""
        df["LinkedIn Profile"] = ""  # New Column
        
        progress_bar = st.progress(0, text="Scanning targets. Please wait...")
        total_firms = len(df)
        
        for index, row in df.iterrows():
            url = row["Website"]
            progress_bar.progress((index) / total_firms, text=f"Analysing {row['Company Name']}...")
            
            html = fetch_page_html(url)
            if html:
                emails = extract_emails(html)
                linkedin_links = extract_linkedin(html)
                matched_identity = scan_for_keywords(html, final_firm_types)
                matched_roles = scan_for_keywords(html, final_job_roles)
                
                df.at[index, "Contact Emails"] = ", ".join(emails) if emails else "None found"
                df.at[index, "LinkedIn Profile"] = ", ".join(linkedin_links) if linkedin_links else "None found"
                df.at[index, "Verified Identity (Website Match)"] = ", ".join(matched_identity).title() if matched_identity else "Unverified/Other"
                df.at[index, "Hiring Signals"] = ", ".join(matched_roles).title() if matched_roles else "No signals"
            else:
                df.at[index, "Contact Emails"] = "Scan failed"
                df.at[index, "LinkedIn Profile"] = "Scan failed"
                df.at[index, "Verified Identity (Website Match)"] = "Scan failed"
                df.at[index, "Hiring Signals"] = "Scan failed"
                
        progress_bar.progress(1.0, text="Analysis complete.")
        st.session_state.clean_df = df
        
        # Display all rows natively without filtering anything out
        st.subheader("Final Intelligence Report")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Report as CSV",
            data=csv,
            file_name=f"firm_intelligence_{city.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )