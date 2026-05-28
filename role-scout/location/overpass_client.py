import requests
import time
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

def find_businesses_nearby(lat: float, lon: float, radius: int, business_type: str = "office", retries: int = 3) -> List[Dict]:
    """Queries the Overpass API with built-in retries for timeout errors."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # We add [timeout:25] to explicitly give the server more time to process the geography
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["{business_type}"](around:{radius},{lat},{lon});
      way["{business_type}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    
    headers = {
        "User-Agent": "RoleScoutApp/1.0",
        "Accept": "*/*"
    }
    
    # A standard loop to retry the request if the server is busy
    for attempt in range(retries):
        try:
            # We set a Python timeout of 30 seconds so our code doesn't hang forever
            response = requests.post(overpass_url, data={"data": overpass_query}, headers=headers, timeout=30)
            
            # If the status code is 504, manually trigger a retry
            if response.status_code == 504:
                print(f"Attempt {attempt + 1}: Server is busy (504). Retrying in 2 seconds...")
                time.sleep(2)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            businesses = []
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                name = tags.get("name")
                website = tags.get("website") or tags.get("contact:website")
                
                if name:
                    businesses.append({
                        "name": name,
                        "website": website,
                        "type": tags.get(business_type, "Unknown")
                    })
            return businesses
            
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1}: The connection timed out. Retrying in 2 seconds...")
            time.sleep(2)
        except requests.RequestException as e:
            print(f"Error fetching businesses from Overpass: {e}")
            break # Break the loop on other fatal errors (like no internet)
            
    print("Failed to fetch data after all retries. The server might be down.")
    return []

def find_businesses_in_polygon(polygon_coords: list, business_type: str = "office", retries: int = 3) -> List[Dict]:
    """Queries the Overpass API for businesses strictly within a drawn custom polygon."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Flatten the list of (lat, lon) tuples into the exact string format Overpass requires: "lat1 lon1 lat2 lon2"
    poly_string = " ".join([f"{lat} {lon}" for lat, lon in polygon_coords])
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["{business_type}"](poly:"{poly_string}");
      way["{business_type}"](poly:"{poly_string}");
    );
    out center;
    """
    
    headers = {
        "User-Agent": "RoleScoutApp/1.1",
        "Accept": "*/*"
    }
    
    for attempt in range(retries):
        try:
            response = requests.post(overpass_url, data={"data": overpass_query}, headers=headers, timeout=30)
            
            if response.status_code == 504:
                print(f"Attempt {attempt + 1}: Server is busy (504). Retrying in 2 seconds...")
                time.sleep(2)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            businesses = []
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                name = tags.get("name")
                website = tags.get("website") or tags.get("contact:website")
                
                if name:
                    businesses.append({
                        "name": name,
                        "website": website,
                        "type": tags.get(business_type, "Unknown")
                    })
            return businesses
            
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1}: The connection timed out. Retrying in 2 seconds...")
            time.sleep(2)
        except requests.RequestException as e:
            print(f"Error fetching businesses from Overpass: {e}")
            break 
            
    print("Failed to fetch data after all retries.")
    return []

# --- Quick Local Test ---
if __name__ == "__main__":
    print("Fetching coordinates...")
    coords = get_coordinates("Union Street", "Aberdeen")
    if coords:
        print(f"Found coordinates: {coords}")
        print("Searching for offices within a 500 metre radius. This may take a few seconds...")
        results = find_businesses_nearby(coords[0], coords[1], 500, "office")
        
        if not results:
            print("No businesses found or request was blocked.")
        else:
            print(f"\nSuccess! Found {len(results)} total offices. Here are the first 5:")
            for idx, biz in enumerate(results[:5]): 
                print(f"{idx + 1}. {biz['name']} - Website: {biz['website']}")
    else:
        print("Could not find that location.")