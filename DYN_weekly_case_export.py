import requests
import json
import re
import time
import html
import schedule
from datetime import datetime, timedelta

API_URL = "https://gdprhub.eu/api.php"
BASE_URL = "https://gdprhub.eu/index.php?title="
OUTPUT_FILE = "./data/extracted_weekly.json"


def clean_html(raw_html):
    """ Removes HTML tags and cleans up whitespace for the vector index"""
    if not raw_html: return ""
    clean = re.sub(r'<(script|style).*?>.*?</\1>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', '', clean)
    return html.unescape(clean).strip()


def get_transformed_page_data(title):
    """Fetches metadata and summary using the MediaWiki API"""

    # Case schema
    transformed = {
        "id": "",
        "article_number": "",
        "title": title,
        "url": f"{BASE_URL}{title.replace(' ', '_')}",
        "type": "",
        "jurisdiction": "",
        "date": "",
        "fine": "",
        "currency": "",
        "gdpr_articles": [],
        "text": ""
    }

    try:
        # Find English Summary sections as they have different IDs to the article
        sec_res = requests.get(API_URL, params={
            "action": "parse",
            "page": title,
            "prop": "sections",
            "format": "json"
        }).json()
        sections = sec_res.get("parse", {}).get("sections", [])

        summary_idx = next((s.get("index") for s in sections if "English Summary" in s.get("line", "")), None)

        if summary_idx:
            sum_res = requests.get(API_URL, params={
                "action": "parse",
                "page": title,
                "section": summary_idx,
                "prop": "text",
                "format": "json"
            }).json()
            raw_text = sum_res.get("parse", {}).get("text", {}).get("*", "")
            transformed["text"] = clean_html(raw_text)

        meta_res = requests.get(API_URL, params={
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json"
        }).json()
        wikitext = meta_res.get("parse", {}).get("wikitext", {}).get("*", "")

        # Extract the fields
        params = re.findall(r'\|\s*([^=|\n]+?)\s*=\s*([^|{}\n]*)', wikitext)

        temp_articles = []
        for key, val in params:
            k = key.strip()
            # Clean wiki brackets
            v = re.sub(r'\[\[|\]\]', '', val.strip())

            if not v: continue

            if k == "ECLI":
                transformed["article_number"] = v
                transformed["id"] = v
            elif k == "Type":
                transformed["type"] = v
            elif k == "Jurisdiction":
                transformed["jurisdiction"] = v
            elif k == "Fine":
                transformed["fine"] = v
            elif k == "Currency":
                transformed["currency"] = v
            elif k == "Date Decided":
                transformed["date"] = v
            elif k.startswith("GDPR Article"):
                if "Link" not in k:
                    temp_articles.append(v)

        transformed["gdpr_articles"] = list(set(temp_articles))

    except Exception as e:
        print(f"Error processing {title}: {e}")

    return transformed


def run_weekly_job():
    print(f"[{datetime.now()}] Starting Extraction...")

    start_time = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Get titles of pages created in the last week
    list_params = {
        "action": "query",
        "list": "recentchanges",
        "rcstart": start_time,
        "rcdir": "newer",
        "rctype": "new",
        "rcnamespace": "0",
        "rclimit": "500",
        "format": "json"
    }

    results = []
    try:
        response = requests.get(API_URL, params=list_params).json()
        changes = response.get("query", {}).get("recentchanges", [])

        for change in changes:
            title = change['title']
            print(f"Processing: {title}")
            results.append(get_transformed_page_data(title))
            time.sleep(0.5) # Rate limit avoidance

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        print(f"Finished. {len(results)} cases extracted")

    except Exception as e:
        print(f"Job Failed: {e}")


schedule.every().monday.at("00:01").do(run_weekly_job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)