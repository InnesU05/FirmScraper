import streamlit as st
import pandas as pd
import os
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from location.overpass_client import get_coordinates, find_businesses_in_polygon, find_businesses_nearby
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
st.markdown("Isolate professional consultancies and advisory firms using geospatial targeting.")

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
    st.header("1. Set Map Focus")
    street_name = st.text_input("Street Name (to centre map)", value="Union Street")
    city = st.text_input("City", value="Aberdeen")
    
    st.divider()
    
    # --- NEW: Search Mode Toggle ---
    st.header("2. Search Mode")
    search_mode = st.radio("Select Target Method", ["Draw Perimeter", "Radius Search"])
    
    if search_mode == "Radius Search":
        radius = st.slider("Search Radius (metres)", min_value=100, max_value=5000, value=1000, step=100)
    else:
        radius = None
        
    st.divider()
    
    st.header("3. Industry Parameters")
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

# --- Step 1: Map & Location ---
coords = cached_get_coordinates(street_name, city)

if coords:
    # ---------------------------------------------------------
    # MODE A: DRAW PERIMETER
    # ---------------------------------------------------------
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
            fetch_button = st.button("Discover Firms in Perimeter", type="primary", use_container_width=True)
            
            if fetch_button:
                geom = map_data["last_active_drawing"]["geometry"]
                if geom["type"] == "Polygon":
                    with st.spinner("Querying drawn perimeter..."):
                        raw_coords = geom["coordinates"][0]
                        polygon_coords = [(lat, lon) for lon, lat in raw_coords]
                        
                        st.session_state.raw_data = find_businesses_in_polygon(polygon_coords, business_type)
                        
                        if st.session_state.raw_data:
                            st.session_state.clean_df = clean_business_data(st.session_state.raw_data)
                            st.success(f"Successfully identified {len(st.session_state.clean_df)} viable targets.")
                        else:
                            st.warning("No businesses found in that specific shape. Try drawing a wider area.")

    # ---------------------------------------------------------
    # MODE B: RADIUS SEARCH
    # ---------------------------------------------------------
    elif search_mode == "Radius Search":
        m = folium.Map(location=[coords[0], coords[1]], zoom_start=14)
        
        # Visually render the radius on the map
        folium.Circle(
            location=[coords[0], coords[1]],
            radius=radius,
            color="#FF4B4B",
            fill=True,
            fill_color="#FF4B4B"
        ).add_to(m)
        
        st.markdown("### Search Radius")
        st.info(f"Targeting all {industry_focus.lower()} locations within a {radius} metre radius.")
        
        st_folium(m, width=1000, height=500, key="radius_map")
        
        fetch_button = st.button("Discover Firms in Radius", type="primary", use_container_width=True)
        if fetch_button:
            with st.spinner(f"Querying a {radius}m radius..."):
                st.session_state.raw_data = find_businesses_nearby(coords[0], coords[1], radius, business_type)
                
                if st.session_state.raw_data:
                    st.session_state.clean_df = clean_business_data(st.session_state.raw_data)
                    st.success(f"Successfully identified {len(st.session_state.clean_df)} viable targets.")
                else:
                    st.warning("No businesses found in this area. Try increasing the radius.")
else:
    st.error("⚠️ Could not load the map. The coordinate server might be busy, or the location is misspelled. Please wait 5 seconds and refresh.")

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