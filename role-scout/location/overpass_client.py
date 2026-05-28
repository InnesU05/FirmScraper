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
    headers = {"User-Agent": "RoleScoutApp/1.1"}
    
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

def find_businesses_nearby(lat: float, lon: float, radius: int, retries: int = 3) -> List[Dict]:
    """Queries the Overpass API with built-in retries for timeout errors."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["office"](around:{radius},{lat},{lon});
      way["office"](around:{radius},{lat},{lon});
      node["commercial"](around:{radius},{lat},{lon});
      way["commercial"](around:{radius},{lat},{lon});
      node["amenity"="bank"](around:{radius},{lat},{lon});
      way["amenity"="bank"](around:{radius},{lat},{lon});
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
                    biz_type = tags.get("office") or tags.get("commercial") or tags.get("amenity") or "Commercial"
                    businesses.append({
                        "name": name,
                        "website": website,
                        "type": biz_type
                    })
            return businesses
            
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1}: The connection timed out. Retrying in 2 seconds...")
            time.sleep(2)
        except requests.RequestException as e:
            print(f"Error fetching businesses from Overpass: {e}")
            break 
            
    print("Failed to fetch data after all retries. The server might be down.")
    return []

def find_businesses_in_polygon(polygon_coords: list, retries: int = 3) -> List[Dict]:
    """Queries the Overpass API for businesses strictly within a drawn custom polygon."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    poly_string = " ".join([f"{lat} {lon}" for lat, lon in polygon_coords])
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["office"](poly:"{poly_string}");
      way["office"](poly:"{poly_string}");
      node["commercial"](poly:"{poly_string}");
      way["commercial"](poly:"{poly_string}");
      node["amenity"="bank"](poly:"{poly_string}");
      way["amenity"="bank"](poly:"{poly_string}");
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
                    biz_type = tags.get("office") or tags.get("commercial") or tags.get("amenity") or "Commercial"
                    businesses.append({
                        "name": name,
                        "website": website,
                        "type": biz_type
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

if __name__ == "__main__":
    print("Fetching coordinates...")
    coords = get_coordinates("Union Street", "Aberdeen")
    if coords:
        print(f"Found coordinates: {coords}")
        print("Searching for commercial nodes within a 500 metre radius. This may take a few seconds...")
        results = find_businesses_nearby(coords[0], coords[1], 500)
        
        if not results:
            print("No businesses found or request was blocked.")
        else:
            print(f"\nSuccess! Found {len(results)} total offices. Here are the first 5:")
            for idx, biz in enumerate(results[:5]): 
                print(f"{idx + 1}. {biz['name']} - Website: {biz['website']}")
    else:
        print("Could not find that location.")