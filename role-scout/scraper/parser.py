from bs4 import BeautifulSoup
import re
from typing import List, Set

def extract_emails(html_content: str) -> set:
    """Scans raw HTML for email addresses using a regular expression."""
    # A standard regex pattern for finding emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, html_content))
    
    # Filter out common false positives (like image files or generic web dev strings)
    cleaned_emails = {email for email in emails if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))}
    return cleaned_emails

def scan_for_roles(html_content: str, keywords: List[str] = None) -> List[str]:
    """Parses HTML text and checks for specific role or hiring keywords."""
    if keywords is None:
        # Default keywords focused on early-career pathways and technical advisory roles
        keywords = ["graduate", "internship", "analyst", "consultant", "mechanical", "entry-level"]
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract all visible text from the webpage and make it lowercase
    page_text = soup.get_text(separator=' ', strip=True).lower()
    
    found_keywords = []
    for keyword in keywords:
        if keyword.lower() in page_text:
            found_keywords.append(keyword)
            
    return found_keywords

# --- Quick Local Test ---
if __name__ == "__main__":
    print("Testing the HTML parser module...")
    
    # A dummy HTML snippet to simulate a company's careers page
    dummy_html = """
    <html>
        <body>
            <h1>Join Our Team</h1>
            <p>We are currently looking for a driven graduate to join our mechanical design team.</p>
            <p>As an entry-level analyst, you will work on high-impact projects.</p>
            <p>Send your CV to careers@topfirm.co.uk or reach out to our hiring manager at john.doe@topfirm.co.uk.</p>
            <img src="banner@2x.png" alt="Company Banner">
        </body>
    </html>
    """
    
    print("\nScanning dummy HTML...")
    
    emails = extract_emails(dummy_html)
    print(f"Emails found: {emails}")
    
    roles = scan_for_roles(dummy_html)
    print(f"Keywords matched: {roles}")