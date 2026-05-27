import pandas as pd
from typing import List, Dict

def clean_business_data(raw_businesses: List[Dict], exclude_keywords: List[str] = None) -> pd.DataFrame:
    """
    Takes raw business data from Overpass, removes invalid entries, 
    and converts it into a clean Pandas DataFrame for the UI.
    """
    if exclude_keywords is None:
        # Default keywords to filter out high-street shops and non-corporate offices
        exclude_keywords = ["taxi", "hair", "salon", "plumbing", "dental", "clinic", "cafe", "restaurant", "retail"]

    cleaned_list = []
    
    for biz in raw_businesses:
        name = biz.get("name", "")
        website = biz.get("website")
        
        # 1. We must have a website to scrape
        if not website or str(website).lower() == "none":
            continue
            
        # 2. Convert name to lowercase to check against our exclusion list
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in exclude_keywords):
            continue
            
        # 3. Ensure the website has http/https so Playwright can navigate to it later
        if not website.startswith("http"):
            website = f"https://{website}"
            
        cleaned_list.append({
            "Company Name": name,
            "Industry Type": str(biz.get("type", "Office")).capitalize(),
            "Website": website
        })
        
    # Convert the clean list into a Pandas DataFrame
    df = pd.DataFrame(cleaned_list)
    return df

# --- Quick Local Test ---
if __name__ == "__main__":
    print("Testing the filter module...")
    
    # Simulating the messy data you just got from Overpass
    dummy_data = [
        {"name": "Centrum Aberdeen", "website": "https://centrum-offices.com/", "type": "office"},
        {"name": "City Gate Aberdeen", "website": None, "type": "office"},
        {"name": "Aberdeen Taxis", "website": "https://aberdeen-taxis.com", "type": "office"},
        {"name": "Global Engineering Consulting", "website": "www.global-eng.co.uk", "type": "office"}
    ]
    
    df = clean_business_data(dummy_data)
    
    print("\nOriginal list size:", len(dummy_data))
    print("Cleaned DataFrame size:", len(df))
    print("\nFinal Cleaned Data Table:")
    print(df)