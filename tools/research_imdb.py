#!/usr/bin/env python3
"""
Hybrid IMDb / TMDb Research + Notion Updater
- Search TMDb by title
- Pick the correct candidate
- Automatically update your Notion database using the IMDb ID
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from textwrap import shorten
from notion_client import Client
from datetime import datetime, timezone

# Import configuration from .env
try:
    from config import NOTION_TOKEN, DATABASE_ID, TMDB_API_KEY, REGION
except ImportError:
    print("❌ ERROR: config.py not found!")
    print("Please copy config.example.py to config.py and fill in your credentials.")
    exit(1)

notion = Client(auth=NOTION_TOKEN)


# ---------------------------
# TMDb search by title
# ---------------------------
def search_by_title(title, media_type=None, max_results=5):
    results_list = []
    search_types = [media_type] if media_type in ("movie", "tv") else ["movie", "tv"]

    for stype in search_types:
        url = f"https://api.themoviedb.org/3/search/{stype}"
        params = {"api_key": TMDB_API_KEY, "query": title}
        try:
            data = requests.get(url, params=params).json()
        except Exception as e:
            print(f"⚠️ Error searching TMDb for {title}: {e}")
            continue

        for item in data.get("results", [])[:max_results]:
            tmdb_id = item.get("id")
            name = item.get("title") or item.get("name")
            overview = item.get("overview") or ""
            year = (item.get("release_date") or item.get("first_air_date") or "")[:4]

            # Get IMDb ID
            imdb_id = None
            try:
                ext = requests.get(
                    f"https://api.themoviedb.org/3/{stype}/{tmdb_id}/external_ids",
                    params={"api_key": TMDB_API_KEY}
                ).json()
                imdb_id = ext.get("imdb_id")
            except Exception:
                pass

            results_list.append({
                "title": name,
                "overview": overview,
                "year": year,
                "imdb_id": imdb_id,
                "media_type": stype,
                "tmdb_id": tmdb_id
            })

    # Sort by year descending
    results_list.sort(key=lambda x: x.get("year") or "", reverse=True)
    return results_list


# ---------------------------
# Print results in terminal
# ---------------------------
def print_results(results):
    if not results:
        print("⚠️ No results found.")
        return
    print("\nSearch results:\n")
    for i, r in enumerate(results, 1):
        desc = shorten(r["overview"], width=80, placeholder="…")
        print(f"{i}. {r['title']} ({r['year']}) [{r['media_type']}] - IMDb: {r['imdb_id']}")
        print(f"    {desc}\n")


# ---------------------------
# Get TMDb ID from IMDb ID
# ---------------------------
def get_tmdb_id_from_imdb(imdb_id):
    url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    params = {"api_key": TMDB_API_KEY, "external_source": "imdb_id"}
    try:
        data = requests.get(url, params=params).json()
    except Exception as e:
        print(f"⚠️ Error fetching TMDb ID for IMDb {imdb_id}: {e}")
        return None, None

    if data.get("tv_results"):
        return data["tv_results"][0]["id"], "tv"
    elif data.get("movie_results"):
        return data["movie_results"][0]["id"], "movie"
    else:
        print(f"⚠️ No TMDb result found for IMDb ID {imdb_id}")
        return None, None


# ---------------------------
# Update Notion page by IMDb ID
# ---------------------------
def update_page_by_imdb(page_id, imdb_id, force_refresh=True):
    tmdb_id, media_type = get_tmdb_id_from_imdb(imdb_id)
    if not tmdb_id:
        print(f"⚠️ Could not fetch TMDb ID for IMDb {imdb_id}")
        return

    updates = {"TMDb ID": {"number": tmdb_id}}

    # Optional: fetch trailer
    trailer_url = get_trailer(tmdb_id, media_type)
    if trailer_url:
        updates["Trailer URL"] = {"url": trailer_url}

    # Update last synced
    updates["Last Synced"] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}

    try:
        notion.pages.update(page_id=page_id, properties=updates)
        print(f"✅ Updated Notion page with TMDb ID {tmdb_id} (IMDb: {imdb_id})")
    except Exception as e:
        print(f"⚠️ Failed to update Notion page: {e}")


# ---------------------------
# Fetch YouTube trailer
# ---------------------------
def get_trailer(tmdb_id, media_type):
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/videos"
    params = {"api_key": TMDB_API_KEY}
    try:
        data = requests.get(url, params=params).json()
    except Exception:
        return None

    trailer_url = None
    for v in data.get("results", []):
        if v.get("site", "").lower() == "youtube" and v.get("type", "").lower() == "trailer":
            trailer_url = f"https://www.youtube.com/watch?v={v.get('key')}"
            break
    return trailer_url


# ---------------------------
# Main interactive loop
# ---------------------------
def main():
    print("=== TMDb / IMDb Quick Lookup + Notion Updater ===\n")

    while True:
        title = input("Enter title to search (or 'q' to quit): ").strip()
        if title.lower() == "q":
            break

        media_type = input("Enter media type (movie/tv, optional): ").strip().lower()
        if media_type not in ("movie", "tv"):
            media_type = None

        results = search_by_title(title, media_type=media_type, max_results=10)
        print_results(results)

        if not results:
            continue

        selection = input("Select the correct result (number, or 0 to skip): ").strip()
        if selection == "0":
            continue
        try:
            idx = int(selection) - 1
            chosen = results[idx]
        except (ValueError, IndexError):
            print("⚠️ Invalid selection. Skipping.")
            continue

        # Ask for the Notion page ID
        page_id = input("Enter the Notion page ID to update with this IMDb ID (or leave blank to skip): ").strip()
        if page_id:
            update_page_by_imdb(page_id, chosen["imdb_id"])

        print("\n---\n")


if __name__ == "__main__":
    main()