from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def fetch_page_html(url: str) -> str:
    """Visits a URL using a headless browser and returns the raw HTML."""
    print(f"Navigating to {url}...")
    
    with sync_playwright() as p:
        # Launch Chromium in headless mode (invisible background browser)
        browser = p.chromium.launch(headless=True)
        
        # We spoof a standard Windows user agent so sites don't immediately block us
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Go to the website and wait until the core structure has loaded
            # We set a 30-second timeout so the programme doesn't hang on dead links
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Extract the raw HTML of the page
            html_content = page.content()
            return html_content
            
        except PlaywrightTimeoutError:
            print(f"Timeout: {url} took too long to load.")
            return ""
        except Exception as e:
            print(f"Failed to load {url}: {e}")
            return ""
        finally:
            browser.close()

# --- Quick Local Test ---
if __name__ == "__main__":
    print("Testing the headless browser module...")
    
    # We will test it on a standard, reliable website
    test_url = "https://example.com"
    html = fetch_page_html(test_url)
    
    if html:
        print(f"\nSuccess! Fetched {len(html)} characters of HTML from {test_url}.")
        print("Here is a quick peek at the first 250 characters of the source code:")
        print("-" * 50)
        print(html[:250])
        print("-" * 50)
    else:
        print("Failed to fetch HTML.")