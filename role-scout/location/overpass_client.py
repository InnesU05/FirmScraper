# Logic for querying OpenStreetMap (no API key needed)
import requests
from typing import List, Dict, Optional

def get_coordinates(street_name: str, city: str) -> Optional[tuple]:
    """Fetches the latitude and longitude for a given street and city using Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "street": street_name,
        "city": city,
        "format": "json",
        "limit": 1
    }
    # OpenStreetMap requires a custom User-Agent to prevent blocking
    headers = {"User-Agent": "RoleScoutApp/1.0"}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None
    except requests.RequestException as e:
        print(f"Error fetching coordinates: {e}")
        return None

def find_businesses_nearby(lat: float, lon: float, radius: int, business_type: str = "office") -> List[Dict]:
    """Queries the Overpass API for businesses within a specific radius (in metres)."""
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Overpass QL query: searches for nodes within 'radius' of the lat/lon
    overpass_query = f"""
    [out:json];
    (
      node["{business_type}"](around:{radius},{lat},{lon});
      way["{business_type}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    
    try:
        response = requests.post(overpass_url, data={"data": overpass_query})
        response.raise_for_status()
        data = response.json()
        
        businesses = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            website = tags.get("website") or tags.get("contact:website")
            
            # We only care about businesses that actually have a name
            if name:
                businesses.append({
                    "name": name,
                    "website": website,
                    "type": tags.get(business_type, "Unknown")
                })
        return businesses
    except requests.RequestException as e:
        print(f"Error fetching businesses from Overpass: {e}")
        return []

# --- Quick Local Test ---
if __name__ == "__main__":
    print("Fetching coordinates...")
    coords = get_coordinates("Union Street", "Aberdeen")
    if coords:
        print(f"Found coordinates: {coords}")
        print("Searching for offices within a 500 metre radius...")
        # Searching for 'office' as a broad category first
        results = find_businesses_nearby(coords[0], coords[1], 500, "office")
        
        for idx, biz in enumerate(results[:5]): # Just print the first 5 so we don't flood the terminal
            print(f"{idx + 1}. {biz['name']} - Website: {biz['website']}")
    else:
        print("Could not find that location.")