import requests
from bs4 import BeautifulSoup

API_URL = "https://gdprhub.eu/api.php"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "gdpr-rag-bot/0.1 (contact: you@example.com)"})


def get_candidate_titles(prefix="A", limit_pages=5000):
    """
    Retrieve page titles from gdprhub.eu API, starting from a given prefix.
    
    Uses the MediaWiki API to paginate through all pages. Can be called
    multiple times with different prefixes to get all titles.
    """
    titles = []
    apcontinue = None

    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apfrom": prefix,
            "apnamespace": 0,
            "aplimit": "max",
            "format": "json",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue

        r = SESSION.get(API_URL, params=params)
        r.raise_for_status()
        data = r.json()

        for page in data.get("query", {}).get("allpages", []):
            titles.append(page["title"])

        apcontinue = data.get("continue", {}).get("apcontinue")
        if not apcontinue or len(titles) >= limit_pages:
            break

    return titles


def looks_like_gdpr_article(title: str) -> bool:
    """
    Check if a page title looks like a GDPR article.
    
    Currently checks if both "article" and "gdpr" appear in the title.
    """
    t = title.lower()
    return "article" in t and "gdpr" in t


def fetch_page_html(title):
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    }
    r = SESSION.get(API_URL, params=params)
    r.raise_for_status()
    data = r.json()
    return data.get("parse", {}).get("text", "")


def extract_sections_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    sections = []
    current_title = "Intro"
    current_text_parts = []

    def flush_section():
        nonlocal current_title, current_text_parts
        text = " ".join(t.strip() for t in current_text_parts if t.strip())
        if text:
            sections.append(
                {"section_title": current_title, "text": text}
            )
        current_title = None
        current_text_parts = []

    for el in soup.find_all(["h2", "h3", "p", "li"]):
        if el.name in ("h2", "h3"):
            flush_section()
            current_title = el.get_text(" ", strip=True)
        else:
            current_text_parts.append(el.get_text(" ", strip=True))

    flush_section()
    return sections


def build_article_docs(title, html):
    sections = extract_sections_from_html(html)

    # very rough article number extraction: find "article <num>" in title
    article_number = None
    import re

    m = re.search(r"article\s+(\d+)", title, flags=re.I)
    if m:
        article_number = m.group(1)

    url = "https://gdprhub.eu/index.php?title=" + title.replace(" ", "_")

    # join all section texts into one big string
    full_text = " ".join(sec["text"] for sec in sections if sec.get("text"))

    doc = {
        "id": "article"+article_number,              # 1 article = 1 id
        "type": "article",
        "title": title,
        "article_number": article_number,
        "url": url,
        "text": full_text,
    }

    # keep API the same: return a list
    return [doc]



def main():
    # 1) Broad discovery
    titles = get_candidate_titles(prefix="A")  # run again with other prefixes if needed
    print(f"Fetched {len(titles)} titles starting from 'A'")

    # 2) Filter to likely GDPR article commentaries
    article_titles = [t for t in titles if looks_like_gdpr_article(t)][:]
    print("Candidate GDPR article pages:")
    for t in article_titles:
        print(" -", t)

    all_docs = []

    for title in article_titles:
        print(f"Processing {title}...")
        html = fetch_page_html(title)
        docs = build_article_docs(title, html)
        all_docs.extend(docs)

    print(f"Built {len(all_docs)} document chunks")

    # Example: show a few chunks
    with open('gdpr_articles.json', 'w') as w:
      import json
      w.write(json.dumps(all_docs, 
              indent=2, 
              sort_keys=True)
      )


if __name__ == "__main__":
    main()
