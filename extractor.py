import httpx
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.headings = []
        self.text_content = []
        
        self.in_title = False
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            attrs_dict = dict(attrs)
            if attrs_dict.get("name", "").lower() == "description":
                self.meta_description = attrs_dict.get("content", "")
            elif attrs_dict.get("property", "").lower() == "og:description":
                # Fallback to OpenGraph description if standard description isn't set yet
                if not self.meta_description:
                    self.meta_description = attrs_dict.get("content", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        self.current_tag = None

    def handle_data(self, data):
        cleaned_data = data.strip()
        if not cleaned_data:
            return
            
        if self.in_title:
            self.title = cleaned_data
        elif self.current_tag in ["h1", "h2", "h3"]:
            if len(self.headings) < 10:  # Limit headings count
                self.headings.append(f"{self.current_tag.upper()}: {cleaned_data}")
        
        # Accumulate plain text (ignoring script/style tags)
        if self.current_tag not in ["script", "style", "head", "title", "meta", "link"]:
            self.text_content.append(cleaned_data)

def extract_domain_metadata(domain: str) -> dict:
    """
    Fetches the homepage of the domain and extracts title, meta description, headings,
    and looks for contact emails in the visible text.
    """
    # Clean domain name
    domain = domain.strip().lower()
    if domain.startswith("http://") or domain.startswith("https://"):
        url = domain
        parsed = urlparse(url)
        domain = parsed.netloc
    else:
        url = f"https://{domain}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Fetch homepage
        with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0, verify=False) as client:
            response = client.get(url)
            
            # If https fails, try http
            if response.status_code != 200 and url.startswith("https://"):
                url = f"http://{domain}"
                response = client.get(url)
                
            response.raise_for_status()
            html_content = response.text
    except Exception as e:
        # Fallback: if https fails completely, try http
        if url.startswith("https://"):
            try:
                url = f"http://{domain}"
                with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0, verify=False) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    html_content = response.text
            except Exception as inner_e:
                raise Exception(f"Failed to fetch website {domain}: {str(inner_e)}")
        else:
            raise Exception(f"Failed to fetch website {domain}: {str(e)}")

    # Parse HTML
    parser = MetadataParser()
    parser.feed(html_content)
    
    full_text = " ".join(parser.text_content)
    
    # Extract emails using regex
    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    found_emails = list(set(email_regex.findall(full_text)))
    
    # Filter out trash/assets emails (e.g. format extensions, logos)
    exclude_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', 'example.com')
    filtered_emails = [
        email for email in found_emails 
        if not email.lower().endswith(exclude_extensions) and not any(part in email.lower() for part in ['w3.org', 'schema.org', 'git'])
    ]

    # Try to find a primary contact email
    # Priority: info@, contact@, sales@, hello@, support@, admin@
    primary_email = ""
    if filtered_emails:
        priority_prefixes = ["info@", "contact@", "hello@", "sales@", "support@", "admin@"]
        for prefix in priority_prefixes:
            for email in filtered_emails:
                if email.lower().startswith(prefix):
                    primary_email = email
                    break
            if primary_email:
                break
        if not primary_email:
            primary_email = filtered_emails[0]
            
    # Fallback to info@domain.com if no emails found
    if not primary_email:
        primary_email = f"info@{domain}"

    # Extract clean text snippet
    text_snippet = full_text[:2000] if len(full_text) > 2000 else full_text

    return {
        "title": parser.title or f"{domain.capitalize()} Homepage",
        "description": parser.meta_description or "No description available.",
        "headings": parser.headings,
        "emails_found": filtered_emails,
        "primary_email": primary_email,
        "text_snippet": text_snippet,
        "scraped_url": url
    }

if __name__ == "__main__":
    # Small test
    try:
        res = extract_domain_metadata("google.com")
        print("Success:", res["title"], res["primary_email"])
    except Exception as ex:
        print("Error:", ex)
