import base64
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup

def decode_email():
    with open('/Users/E2005/projects/bobfrmmktg/Weekly Performance Demand Report_ 2026-W08.eml', 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    html_content = ""
    for part in msg.walk():
        if part.get_content_type() == 'text/html':
            html_content = part.get_content()
            break
            
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        with open('/Users/E2005/projects/bobfrmmktg/decoded_email.txt', 'w') as f:
            f.write(text)
        print("Wrote decoded email to decoded_email.txt")
    else:
        print("No HTML content found.")

if __name__ == "__main__":
    decode_email()
