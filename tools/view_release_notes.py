import requests
from datetime import datetime


from pathlib import Path
import argparse
from notion_client import Client
from datetime import datetime
import sys

# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import NOTION_TOKEN, RELEASES_DATABASE_ID
except ImportError:
    print("❌ ERROR: Missing configuration!")
    print("Please run setup_releases.py first to create the database.")
    exit(1)

# =========================
# CONFIG
# =========================

notion = Client(auth=NOTION_TOKEN)

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# =========================
# QUERY DATABASE
# =========================
def query_database():
    url = f"{BASE_URL}/databases/{RELEASES_DATABASE_ID}/query"
    response = requests.post(url, headers=headers)

    response.raise_for_status()
    return response.json()["results"]

# =========================
# PARSE HELPERS
# =========================
def get_title(prop):
    return prop["title"][0]["plain_text"] if prop["title"] else ""

def get_rich_text(prop):
    return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""

def get_select(prop):
    return prop["select"]["name"] if prop["select"] else ""

def get_date(prop):
    if not prop["date"]:
        return ""
    start = prop["date"]["start"]
    return datetime.fromisoformat(start).date().isoformat()

# =========================
# MAIN
# =========================
def main():
    pages = query_database()

    print("\n📦 Watchtower Releases\n" + "=" * 60)

    for page in pages:
        props = page["properties"]

        version = get_title(props["Version"])
        date = get_date(props["Date"])
        release_type = get_select(props["Type"])
        status = get_select(props["Status"])
        description = get_rich_text(props["Description"])

        print(f"\n🔖 Version     : {version}")
        print(f"📅 Date        : {date}")
        print(f"🏷️ Type        : {release_type}")
        print(f"🚦 Status      : {status}")
        print(f"📝 Description : {description}")
        print("-" * 60)

if __name__ == "__main__":
    main()


