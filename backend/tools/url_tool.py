"""
Live URL Content Reader Tool for Gemini Agent
==============================================
Fetches, cleans, and extracts readable text and article content from web URLs.
Handles HTML boilerplate removal, timeout safeguards, and token-friendly truncation.
"""

import re
import urllib.parse
from typing import Dict, Any

try:
    import httpx
except ImportError:
    httpx = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import trafilatura
except ImportError:
    trafilatura = None


def clean_html_content(html: str) -> str:
    """
    Extracts high-quality readable text from HTML:
    1. Tries trafilatura (state-of-the-art main article extractor)
    2. Falls back to BeautifulSoup with noise tag stripping
    """
    if trafilatura:
        extracted = trafilatura.extract(
            html,
            include_links=True,
            include_tables=True,
            include_images=False,
            output_format="txt",
        )
        if extracted and len(extracted.strip()) > 100:
            return extracted.strip()

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, navbars, footers, svg, and ads
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside", "form"]):
            tag.decompose()

        # Extract text from main or article if available, else body
        main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup
        text = main_content.get_text(separator="\n", strip=True)

        # Remove excessive empty lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # Minimal fallback
    cleaned = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", cleaned).strip()


def fetch_url_content(url: str, max_chars: int = 15000) -> Dict[str, Any]:
    """
    Fetches the web page content of a given URL and returns extracted text.
    
    Args:
        url: The HTTP or HTTPS URL to fetch.
        max_chars: Maximum character limit to keep Gemini context fast and focused.
        
    Returns:
        dict with status, url, title, content, or error.
    """
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Validate URL structure
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        return {
            "status": "error",
            "url": url,
            "error": "Invalid URL format. Must include a valid domain name."
        }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        # Fetch with httpx (sync client)
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            html_text = response.text

        # Extract clean text
        content_text = clean_html_content(html_text)

        if not content_text:
            return {
                "status": "warning",
                "url": url,
                "content": "Web page loaded but no readable text could be extracted.",
            }

        # Truncate if too long to prevent context overflow
        if len(content_text) > max_chars:
            content_text = content_text[:max_chars] + "\n\n[... Content truncated for length ...]"

        return {
            "status": "success",
            "url": url,
            "char_count": len(content_text),
            "content": content_text
        }

    except Exception as exc:
        return {
            "status": "error",
            "url": url,
            "error": f"Failed to fetch content from URL: {str(exc)}"
        }
