from bs4 import BeautifulSoup
import re
from typing import List, Set

def extract_emails(html_content: str) -> Set[str]:
    """Scans raw HTML for email addresses using a regular expression."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, html_content))
    
    cleaned_emails = {email for email in emails if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))}
    return cleaned_emails

def scan_for_keywords(html_content: str, keywords: List[str]) -> List[str]:
    """Parses HTML text and checks for specific keywords."""
    if not keywords:
        return []
        
    soup = BeautifulSoup(html_content, 'html.parser')
    page_text = soup.get_text(separator=' ', strip=True).lower()
    
    found_keywords = []
    for keyword in keywords:
        if keyword.lower() in page_text:
            found_keywords.append(keyword)
            
    return found_keywords

if __name__ == "__main__":
    print("Testing the HTML parser module...")
    
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
    
    roles = scan_for_keywords(dummy_html, ["graduate", "analyst", "mechanical", "entry-level"])
    print(f"Keywords matched: {roles}")