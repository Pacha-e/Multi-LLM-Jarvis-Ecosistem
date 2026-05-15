"""Patch tools.py — add scrape_url + fix imports"""
import re

path = r'C:\Users\Acer Nitro\jarvis_files\jarvis\agent\tools.py'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Add re import
if 'import re' not in src:
    src = src.replace(
        'import math\nimport json\nimport httpx',
        'import math\nimport json\nimport re\nimport httpx'
    )

# 2. Add scrape_url tool before remember_fact
SCRAPE_TOOL = '''
@tool
def scrape_url(url: str, extract: str = "text") -> str:
    """Scrape a web page and extract its content.
    Args:
        url: Full URL to scrape (e.g. 'https://example.com/article')
        extract: What to extract: 'text' (clean text), 'links' (all links), 'summary' (first 1000 chars)
    """
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        }
        r = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        if extract == "links":
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if href.startswith("http") and text:
                    links.append(f"- {text}: {href}")
            return ("Links from " + url + ":\\n" + "\\n".join(links[:30])) if links else "No links found."
        text = soup.get_text(separator="\\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        clean = "\\n".join(lines)
        if extract == "summary":
            return "Summary of " + url + ":\\n" + clean[:1000] + "..."
        return "Content from " + url + ":\\n" + clean[:4000]
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code} error scraping {url}"
    except Exception as e:
        return f"Could not scrape {url}: {e}"

'''

if 'def scrape_url' not in src:
    src = src.replace('@tool\ndef remember_fact', SCRAPE_TOOL + '@tool\ndef remember_fact')

# 3. Add to JARVIS_TOOLS list
if 'scrape_url,' not in src:
    src = src.replace(
        '    web_search,\n    remember_fact,',
        '    web_search,\n    scrape_url,\n    remember_fact,'
    )

# 4. Fix re usage in web_search (already uses re if imported)
with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("Patch applied successfully")
