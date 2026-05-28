import streamlit as st
import pandas as pd
import os
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from location.overpass_client import get_coordinates, find_businesses_in_polygon
from utils.filters import clean_business_data
from scraper.browser import fetch_page_html
from scraper.parser import extract_emails, scan_for_roles

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

st.title("Role Scout: Firm Intelligence")
st.markdown("Draw a perimeter on the map to strictly target consultancies in a specific area.")

# State management
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = []
if 'clean_df' not in st.session_state:
    st.session_state.clean_df = pd.DataFrame()

# Sidebar Setup
with st.sidebar:
    st.header("1. Set Map Focus")
    street_name = st.text_input("Street Name (to centre map)", value="Union Street")
    city = st.text_input("City", value="Aberdeen")
    
    st.divider()
    
    st.header("2. Search Parameters")
    industry_focus = st.selectbox(
        "Industry Focus",
        options=["Engineering Consultancy", "Finance Consultancy", "Energy Services", "General Office"]
    )
    
    tag_map = {
        "Engineering Consultancy": "office",
        "Finance Consultancy": "office", 
        "Energy Services": "commercial",
        "General Office": "office"
    }
    business_type = tag_map[industry_focus]

# --- Step 1: Map & Drawing ---
coords = get_coordinates(street_name, city)

if coords:
    # Initialise the map centered on your chosen street
    m = folium.Map(location=[coords[0], coords[1]], zoom_start=15)
    
    # Add drawing tools (we only need polygons and rectangles for this)
    draw_options = {
        'polyline': False, 'circlemarker': False, 'marker': False, 'circle': False,
        'polygon': True, 'rectangle': True
    }
    Draw(export=False, draw_options=draw_options).add_to(m)
    
    st.markdown("### Select Search Area")
    st.info("Use the ⬛ (Rectangle) or ⬟ (Polygon) tools on the left of the map to draw your search zone.")
    
    # Render the map and capture any shapes drawn by the user
    map_data = st_folium(m, width=1000, height=500)
    
    # Only show the search button if the user has actually drawn a shape
    if map_data and map_data.get("last_active_drawing"):
        st.success("Perimeter locked. Ready to scan.")
        fetch_button = st.button("Discover Firms in Perimeter", type="primary", use_container_width=True)
        
        if fetch_button:
            geom = map_data["last_active_drawing"]["geometry"]
            if geom["type"] == "Polygon":
                with st.spinner("Querying drawn perimeter..."):
                    # GeoJSON provides coordinates as [Longitude, Latitude]
                    raw_coords = geom["coordinates"][0]
                    # We must flip them to (Latitude, Longitude) for Overpass
                    polygon_coords = [(lat, lon) for lon, lat in raw_coords]
                    
                    st.session_state.raw_data = find_businesses_in_polygon(polygon_coords, business_type)
                    
                    if st.session_state.raw_data:
                        st.session_state.clean_df = clean_business_data(st.session_state.raw_data)
                        st.success(f"Successfully identified {len(st.session_state.clean_df)} viable targets.")
                    else:
                        st.warning("No businesses found in that specific shape. Try drawing a wider area.")

# --- Step 2: Deep Scraping ---
if not st.session_state.clean_df.empty:
    st.divider()
    st.subheader("Target Roster")
    st.dataframe(st.session_state.clean_df, use_container_width=True, hide_index=True)
    
    st.subheader("Deep Analysis")
    st.markdown("Scan targeted websites for contact emails and early-career hiring signals (e.g., graduate, analyst, entry-level).")
    
    scrape_button = st.button("Initiate Deep Scrape", type="primary")
    
    if scrape_button:
        df = st.session_state.clean_df.copy()
        df["Contact Emails"] = ""
        df["Hiring Signals"] = ""
        
        progress_bar = st.progress(0, text="Scanning targets. Please wait...")
        total_firms = len(df)
        
        for index, row in df.iterrows():
            url = row["Website"]
            progress_bar.progress((index) / total_firms, text=f"Analysing {row['Company Name']}...")
            
            html = fetch_page_html(url)
            if html:
                emails = extract_emails(html)
                roles = scan_for_roles(html)
                
                df.at[index, "Contact Emails"] = ", ".join(emails) if emails else "None found"
                df.at[index, "Hiring Signals"] = ", ".join(roles).title() if roles else "No signals"
            else:
                df.at[index, "Contact Emails"] = "Scan failed"
                df.at[index, "Hiring Signals"] = "Scan failed"
                
        progress_bar.progress(1.0, text="Analysis complete.")
        st.session_state.clean_df = df
        
        st.subheader("Final Intelligence Report")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Report as CSV",
            data=csv,
            file_name=f"firm_intelligence_{city.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )