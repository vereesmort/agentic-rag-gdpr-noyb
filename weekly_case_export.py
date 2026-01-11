import requests
import json
import re
import time
import schedule
from datetime import datetime, timedelta

API_URL = "https://gdprhub.eu/api.php"
OUTPUT_FILE = "extracted_weekly.json"

def clean_html(raw_html):
    # Removes HTML tags and cleans up whitespace for the vector index
    if not raw_html: return ""
    clean = re.sub(r'<(script|style).*?>.*?</\1>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', '', clean)
    import html
    return html.unescape(clean).strip()


def get_page_data(title):
    # Fetches metadata and summary using the MediaWiki Parse API
    data = {"Page Title": title}

    # Find English Summary section index, these have a different id from the case
    sections_params = {
        "action": "parse",
        "page": title,
        "prop": "sections",
        "format": "json"
    }

    try:
        sec_res = requests.get(API_URL, params=sections_params).json()
        sections = sec_res.get("parse", {}).get("sections", [])

        summary_index = None
        for s in sections:
            if "English Summary" in s.get("line", ""):
                summary_index = s.get("index")
                break

        if summary_index:
            summary_params = {
                "action": "parse",
                "page": title,
                "section": summary_index,
                "prop": "text",
                "format": "json"
            }
            sum_res = requests.get(API_URL, params=summary_params).json()
            raw_summary = sum_res.get("parse", {}).get("text", {}).get("*", "")
            data["Summary"] = clean_html(raw_summary)
        else:
            data["Summary"] = "No Summary found"

        meta_params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json"
        }
        meta_res = requests.get(API_URL, params=meta_params).json()
        wikitext = meta_res.get("parse", {}).get("wikitext", {}).get("*", "")

        # Extract fields
        params = re.findall(r'\|\s*([^=|\n]+?)\s*=\s*([^|{}\n]*)', wikitext)
        for key, val in params:
            k = key.strip().replace("_", " ")
            v = re.sub(r'\[\[|\]\]', '', val.strip())
            if k and v:
                data[k] = v

    except Exception as e:
        print(f"Error parsing {title}: {e}")

    return data


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
        list_res = requests.get(API_URL, params=list_params).json()
        changes = list_res.get("query", {}).get("recentchanges", [])

        for change in changes:
            title = change['title']
            print(f"Processing: {title}")
            results.append(get_page_data(title))
            time.sleep(0.5)  # Rate limit avoidance

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