import requests
import argparse
import time
from notion_client import Client
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
import re
from send_text import send_text
import concurrent.futures
from typing import Dict, List, Tuple, Optional

# Import configuration
try:
    from config import NOTION_TOKEN, DATABASE_ID, TMDB_API_KEY, REGION, DIGEST_PAGE_TITLE, NOTIFICATIONS
except ImportError:
    print("ERROR: config.py not found!")
    print("Please copy config.example.py to config.py and fill in your credentials.")
    exit(1)

PROTECTED_FIELDS = {
    "Status",
    "Your Rating",
    "Date Watched",
}

SERIES_STATUS_MAP = {
    "IN_PRODUCTION": "In Production 🟢",
    "ENDED": "Ended ⚪",
    "CANCELLED": "Cancelled 🔴",
}

SEASON_STATUS_MAP = {
    "CURRENTLY_AIRING": "Currently Airing 📺",
    "SEASON_FINISHED": "Season Finished ✅",
    "BETWEEN_SEASONS": "Between Seasons ⏸️",
    "UPCOMING": "Upcoming Season 🔜",
}

notion = Client(auth=NOTION_TOKEN)

# -----------------------------
# Notification Helper
# -----------------------------
def is_notification_enabled(notification_type):
    """Check if a notification type is enabled in config"""
    return NOTIFICATIONS.get(notification_type, True)  # Default to True if not specified

# -----------------------------
# TMDb Helpers
# -----------------------------
def get_next_season_status(details, current_season_number):
    """
    Determine Next Season Status:
    - Canceled
    - Coming Soon
    - Announced
    - No info
    """

    status = details.get("status")
    in_production = details.get("in_production")
    next_ep = details.get("next_episode_to_air")

    # Canceled
    if status in ("Canceled", "Cancelled"):
        return "Canceled"

    # Coming Soon: dated episode in a future season
    if next_ep:
        next_season = next_ep.get("season_number")
        air_date = next_ep.get("air_date")
        if (
            next_season
            and air_date
            and next_season > (current_season_number or 0)
        ):
            return "Coming Soon"

    # Announced: renewed but no dates
    if in_production:
        return "Announced"

    return "No info"

def debug_json_mode(titles_or_ids, retries=3):
    import json
    import pyperclip

    all_json = []

    for identifier in titles_or_ids:
        # First try IMDb ID lookup
        tmdb_id, media_type = get_tmdb_from_imdb(identifier, retries)
        # If not IMDb, try searching by title
        if not tmdb_id:
            tmdb_id, media_type = search_tmdb(identifier, retries)
        if not tmdb_id:
            print(f"⚠️ Could not find TMDb entry for '{identifier}'")
            continue

        details = get_details(tmdb_id, media_type, retries)
        if not details:
            print(f"⚠️ TMDb details empty for '{identifier}'")
            continue

        formatted_json = json.dumps(details, indent=2)
        all_json.append(formatted_json)

        print(f"\n--- TMDb JSON for '{identifier}' ({media_type}) ---")
        print(formatted_json)

    if all_json:
        combined_json = "\n\n".join(all_json)
        try:
            pyperclip.copy(combined_json)
            print("\n✅ All debug JSON has been copied to your clipboard.")
        except Exception as e:
            print(f"❌ Could not copy to clipboard: {e}")

def tmdb_get(url, params, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5)
    return None

def get_watch_providers(tmdb_id, media_type, region, retries=3):
    data = tmdb_get(f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/watch/providers",
                    {"api_key": TMDB_API_KEY}, retries)
    if not data:
        return []
    region_data = data.get("results", {}).get(region, {})
    flatrate = region_data.get("flatrate", [])
    return [p.get("provider_name") for p in flatrate if p.get("provider_name")]

def get_details(tmdb_id, media_type, retries=3):
    return tmdb_get(
        f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}",
        {"api_key": TMDB_API_KEY, "append_to_response": "credits,external_ids,videos"},
        retries
    )

def normalize_title(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()

def choose_best_tmdb_match(results, query_title):
    norm_query = normalize_title(query_title)
    exact_matches, fallback = [], []
    for r in results:
        title = r.get("title") or r.get("name")
        if not title:
            continue
        norm_title = normalize_title(title)
        (exact_matches if norm_title == norm_query else fallback).append(r)
    return exact_matches[0] if exact_matches else (fallback[0] if fallback else None)

def get_tmdb_from_imdb(imdb_id, retries=3):
    data = tmdb_get(f"https://api.themoviedb.org/3/find/{imdb_id}",
                    {"api_key": TMDB_API_KEY, "external_source": "imdb_id"},
                    retries)
    if data.get("tv_results"):
        return data["tv_results"][0]["id"], "tv"
    if data.get("movie_results"):
        return data["movie_results"][0]["id"], "movie"
    return None, None

def search_tmdb(title, retries=3):
    for media_type in ["tv", "movie"]:
        data = tmdb_get(f"https://api.themoviedb.org/3/search/{media_type}",
                        {"api_key": TMDB_API_KEY, "query": title},
                        retries)
        if data and data.get("results"):
            best = choose_best_tmdb_match(data["results"], title)
            if best:
                return best["id"], media_type
    return None, None

def infer_media_type_from_notion_or_tmdb(props, tmdb_id, retries=3):
    type_prop = props.get("Type", {}).get("select")
    if type_prop and type_prop.get("name"):
        return type_prop["name"].lower()
    for media_type in ("tv", "movie"):
        try:
            r = requests.get(f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}",
                             {"api_key": TMDB_API_KEY}, timeout=10)
            r.raise_for_status()
            return media_type
        except:
            continue
    return None

def get_tmdb_id_from_props(props):
    tmdb_id = props.get("TMDb ID", {}).get("number")
    return tmdb_id if isinstance(tmdb_id, int) else None

def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def is_today(date_str):
    if not date_str:
        return False
    try:
        return date.fromisoformat(date_str) == date.today()
    except ValueError:
        return False

def is_within_days(date_str, days=7):
    if not date_str:
        return False
    try:
        return 0 < (date.fromisoformat(date_str) - date.today()).days <= days
    except ValueError:
        return False

def select_prop_from_map(map_obj, key):
    if key not in map_obj:
        raise KeyError(f"Invalid status key: {key}")
    return {"select": {"name": map_obj[key]}}

def build_notion_props(updates_dict):
    return {k: v for k, v in updates_dict.items() if v is not None}

def should_update(prop_name, current_value, mode):
    if prop_name == "Title":
        return False
    if prop_name == "IMDb ID" and current_value:
        return False
    if mode == "normal":
        return not current_value
    if mode in ("only-missing", "force"):
        return True
    return False

# -----------------------------
# PARALLEL PROCESSING - NEW!
# -----------------------------
def update_notion_page_safe(page_id: str, properties: dict, cover_url: Optional[str] = None) -> Tuple[str, bool, Optional[str]]:
    """
    Safely update a Notion page with error handling.
    Returns: (page_id, success, error_message)
    """
    try:
        # Update cover first if provided
        if cover_url:
            notion.pages.update(page_id=page_id, cover={"type": "external", "external": {"url": cover_url}})
        
        # Update properties
        notion.pages.update(page_id=page_id, properties=properties)
        return (page_id, True, None)
    except Exception as e:
        return (page_id, False, str(e))

def update_notion_pages_parallel(updates_list: List[dict], max_workers: int = 5) -> dict:
    """
    Update multiple Notion pages in parallel.
    
    Args:
        updates_list: List of dicts with keys: page_id, properties, cover_url, title
        max_workers: Number of parallel workers (default: 5, Notion has lower rate limits)
    
    Returns:
        Dict with success/failure counts
    """
    print(f"📝 Updating {len(updates_list)} Notion pages in parallel (workers={max_workers})...")
    
    results = {"success": 0, "failed": 0, "errors": []}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_update = {
            executor.submit(
                update_notion_page_safe, 
                update["page_id"], 
                update["properties"],
                update.get("cover_url")
            ): update 
            for update in updates_list
        }
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_update):
            update = future_to_update[future]
            page_id, success, error = future.result()
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "title": update.get("title", "Unknown"),
                    "error": error
                })
            
            completed += 1
            if completed % 20 == 0:
                print(f"  Updated {completed}/{len(updates_list)} pages...")
    
    print(f"  ✅ Updated {results['success']} pages successfully")
    if results["failed"] > 0:
        print(f"  ⚠️ Failed to update {results['failed']} pages")
    
    return results

def resolve_tmdb_id_and_type(page: dict, args) -> Tuple[Optional[int], Optional[str], str]:
    """
    Resolve TMDb ID and media type for a single page.
    Returns: (tmdb_id, media_type, title)
    """
    props = page.get("properties", {})
    title_prop = props.get("Title", {}).get("title", [])
    title = title_prop[0]["plain_text"].strip() if title_prop else "Untitled"
    
    imdb_id_prop = props.get("IMDb ID", {}).get("rich_text", [])
    imdb_id = imdb_id_prop[0]["plain_text"] if imdb_id_prop else None
    tmdb_id = get_tmdb_id_from_props(props)
    
    # Resolve TMDb ID and media type
    if tmdb_id:
        media_type = infer_media_type_from_notion_or_tmdb(props, tmdb_id, args.retries)
    elif imdb_id:
        tmdb_id, media_type = get_tmdb_from_imdb(imdb_id, args.retries)
    else:
        tmdb_id, media_type = search_tmdb(title, args.retries)
    
    return tmdb_id, media_type, title

def fetch_tmdb_data_parallel(pages: List[dict], args, max_workers: int = 10) -> Dict[str, Tuple]:
    """
    Fetch TMDb data for multiple pages in parallel.
    
    Returns: Dict mapping page_id -> (tmdb_id, media_type, details, title)
    """
    print(f"🚀 Fetching TMDb data for {len(pages)} shows in parallel (workers={max_workers})...")
    
    results = {}
    
    # Phase 1: Resolve TMDb IDs in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page = {
            executor.submit(resolve_tmdb_id_and_type, page, args): page 
            for page in pages
        }
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_page):
            page = future_to_page[future]
            page_id = page["id"]
            
            try:
                tmdb_id, media_type, title = future.result()
                
                if not tmdb_id or not media_type:
                    results[page_id] = (None, None, None, title)
                else:
                    results[page_id] = (tmdb_id, media_type, None, title)  # details will be fetched next
                
                completed += 1
                if completed % 20 == 0:
                    print(f"  Resolved {completed}/{len(pages)} shows...")
                    
            except Exception as e:
                title_prop = page.get("properties", {}).get("Title", {}).get("title", [])
                title = title_prop[0]["plain_text"] if title_prop else "Unknown"
                print(f"  ⚠️ Error resolving {title}: {e}")
                results[page_id] = (None, None, None, title)
    
    print(f"  ✅ Resolved {len(results)} TMDb IDs")
    
    # Build a page_id -> page lookup for fallback resolution
    page_lookup = {page["id"]: page for page in pages}

    # Phase 2: Fetch detailed data in parallel
    print(f"🎬 Fetching detailed TMDb data...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page_id = {}
        
        for page_id, (tmdb_id, media_type, _, title) in results.items():
            if tmdb_id and media_type:
                future = executor.submit(get_details, tmdb_id, media_type, args.retries)
                future_to_page_id[future] = page_id
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_page_id):
            page_id = future_to_page_id[future]
            tmdb_id, media_type, _, title = results[page_id]
            
            try:
                details = future.result()
                results[page_id] = (tmdb_id, media_type, details, title)
                
                completed += 1
                if completed % 20 == 0:
                    print(f"  Fetched {completed}/{len(future_to_page_id)} details...")
                    
            except Exception as e:
                print(f"  ⚠️ Bad TMDb ID for {title} ({tmdb_id}), attempting fallback resolution...")
                
                # Fallback: try IMDb ID then title search
                page = page_lookup.get(page_id)
                fallback_tmdb_id, fallback_media_type = None, None
                
                if page:
                    props = page.get("properties", {})
                    imdb_id_prop = props.get("IMDb ID", {}).get("rich_text", [])
                    imdb_id = imdb_id_prop[0]["plain_text"] if imdb_id_prop else None
                    
                    if imdb_id:
                        fallback_tmdb_id, fallback_media_type = get_tmdb_from_imdb(imdb_id, args.retries)
                    
                    if not fallback_tmdb_id:
                        fallback_tmdb_id, fallback_media_type = search_tmdb(title, args.retries)
                
                if fallback_tmdb_id and fallback_media_type:
                    try:
                        details = get_details(fallback_tmdb_id, fallback_media_type, args.retries)
                        results[page_id] = (fallback_tmdb_id, fallback_media_type, details, title)
                        print(f"  ✅ Fallback succeeded for {title} (new TMDb ID: {fallback_tmdb_id})")
                    except Exception as e2:
                        print(f"  ❌ Fallback also failed for {title}: {e2}")
                        results[page_id] = (tmdb_id, media_type, None, title)
                else:
                    print(f"  ❌ Could not resolve {title} via fallback")
                    results[page_id] = (tmdb_id, media_type, None, title)
    
    print(f"  ✅ Fetched {len(future_to_page_id)} detailed records")
    
    return results

# -----------------------------
# Digest logging
# -----------------------------
def log_digest_to_notion(digest_events):
    if not digest_events:
        return

    blocks = []
    for e in digest_events:
        if e["type"] == "movie":
            content = f"🎬 Movie released today: {e['title']}"
        elif e["type"] == "episode":
            content = f"📺 New episode today: {e['title']} ({e['detail']})"
        elif e["type"] == "bulk":
            content = f"📦 Bulk season released: {e['title']} ({e['detail']})"
        elif e["type"] == "bulk_season_dropped":
            content = f"🍿 New Season Dropped: {e['title']} ({e['detail']})"
        elif e["type"] == "upcoming":
            content = f"🔜 Upcoming season soon: {e['title']} (airing {e['detail']})"
        elif e["type"] == "watching_airing_today":
            content = f"📺 Watching - Airs Today: {e['title']} ({e['detail']})"
        elif e["type"] == "season_finale_today":
            content = f"🎊 Season Finale Today: {e['title']} ({e['detail']})"
        elif e["type"] == "returning_soon":
            content = f"🔄 Returning Soon: {e['title']} ({e['detail']})"
        elif e["type"] == "long_gap_warning":
            content = f"⏸️ Long Gap: {e['title']} ({e['detail']})"
        elif e["type"] == "multiple_episodes_tonight":
            content = f"📅 Busy TV Night: {e['title']} - {e['detail']}"
        else:
            continue

        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        })

    # Create title with date and timestamp
    now = datetime.now(ZoneInfo("America/New_York"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    notion.pages.create(
        parent={"type": "database_id", "database_id": DATABASE_ID},
        properties={
            "Title": {
                "title": [{"text": {"content": f"{DIGEST_PAGE_TITLE} {timestamp}"}}]
            },
            "Is Digest": {"checkbox": True}
        },
        children=blocks
    )

    print("✅ Digest logged to Notion.")

# -----------------------------
# Fetch pages
# -----------------------------
def fetch_all_pages():
    pages, cursor = [], None
    while True:
        res = notion.databases.query(database_id=DATABASE_ID, start_cursor=cursor, page_size=100)
        pages.extend(res["results"])
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return pages

# -----------------------------
# Determine mode
# -----------------------------
def determine_mode(args, imdb_id, tmdb_id):
    if args.force_refresh:
        return "force"
    if args.only_missing:
        if not tmdb_id:
            return "force"  # No TMDb ID: repopulate all fields
        return None         # TMDb ID exists: skip
    return "normal"

# -----------------------------
# Process single page (MODIFIED to use cached TMDb data)
# -----------------------------
def process_page(page, args, tmdb_data_cache, digest_events=None):
    """
    Processes a single Notion page using pre-fetched TMDb data.
    Returns: (status, update_data_dict or None)
    
    update_data_dict contains:
    - page_id: str
    - properties: dict (Notion properties to update)
    - cover_url: str or None
    - title: str (for error reporting)
    """
    if digest_events is None:
        digest_events = []

    props = page.get("properties", {})
    page_id = page["id"]
    title_prop = props.get("Title", {}).get("title", [])
    title = title_prop[0]["plain_text"].strip() if title_prop else "Untitled"

    if page.get("archived"):
        return ("skipped", None)

    # Get cached TMDb data
    tmdb_id, media_type, details, _ = tmdb_data_cache.get(page_id, (None, None, None, None))
    
    if not tmdb_id or not media_type or not details:
        return ("skipped", None)

    imdb_id_prop = props.get("IMDb ID", {}).get("rich_text", [])
    imdb_id = imdb_id_prop[0]["plain_text"] if imdb_id_prop else None
    existing_tmdb_id = get_tmdb_id_from_props(props)

    mode = determine_mode(args, imdb_id, existing_tmdb_id)
    if not mode:
        return ("skipped", None)

    updates = {}
    updates["TMDb ID"] = {"number": tmdb_id}
    updates["Type"] = {"select": {"name": "TV" if media_type == "tv" else "Movie"}}

    # -----------------------------
    # Common fields (Movies & TV)
    # -----------------------------
    if details.get("overview"):
        updates["Overview"] = {"rich_text": [{"text": {"content": details["overview"]}}]}
    if details.get("genres"):
        updates["Genres"] = {"multi_select": [{"name": g["name"]} for g in details["genres"] if g.get("name")]}
    if details.get("poster_path"):
        poster_url = f"https://image.tmdb.org/t/p/original{details['poster_path']}"
        updates["Poster"] = {"files": [{"type": "external", "name": "Poster", "external": {"url": poster_url}}]}
        # Cover will be set in batch update later

    # -----------------------------
    # Streaming
    # -----------------------------
    PROVIDER_MAP = {
        "netflix": "Netflix",
        "prime": "Amazon Prime",
        "amazon": "Amazon Prime",
        "hbo": "HBO Max",
        "max": "HBO Max",
        "amc": "AMC",
        "apple": "Apple TV",
        "hulu": "Hulu",
        "paramount": "Paramount+",
        "peacock": "Peacock",
    }
    providers = get_watch_providers(tmdb_id, media_type, REGION)
    mapped = set()
    for p in providers:
        p_low = p.lower()
        for key, canon in PROVIDER_MAP.items():
            if key in p_low:
                mapped.add(canon)
    if mapped:
        updates["Streaming Services"] = {"multi_select": [{"name": s} for s in sorted(mapped)]}
    if providers and should_update("Streaming First Seen", props.get("Streaming First Seen", {}).get("date"), mode):
        updates["Streaming First Seen"] = {"date": {"start": today_str()}}

    # -----------------------------
    # Trailer
    # -----------------------------
    videos = details.get("videos", {}).get("results", [])
    trailer = next((v for v in videos if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
    if trailer:
        url = f"https://www.youtube.com/watch?v={trailer['key']}"
        updates["Trailer"] = {"url": url}
        updates["Trailer URL"] = {"url": url}

    # -----------------------------
    # Top Cast
    # -----------------------------
    cast = details.get("credits", {}).get("cast", [])[:5]
    if cast:
        # Sanitize cast names - Notion multi_select doesn't allow commas
        sanitized_cast = []
        for c in cast:
            if c.get("name"):
                # Replace commas with semicolons or remove them
                clean_name = c["name"].replace(",", ";")
                sanitized_cast.append({"name": clean_name})
        updates["Top Cast"] = {"multi_select": sanitized_cast}

    # -----------------------------
    # TV-specific fields
    # -----------------------------
    if media_type == "movie":
        # Clear any stale TV-specific fields (e.g. if type was previously wrong)
        for field in ["Last Air Date", "Next Air Date", "First Air Date"]:
            updates[field] = {"date": None}
        for field in ["Air Day of Week", "Season Status", "Series Status", "Next Season Status"]:
            updates[field] = {"select": None}
        for field in ["Season Count", "Latest Season Year",
                      "Current Season Current Episode", "Current Season Total Episodes",
                      "Total Episodes"]:
            updates[field] = {"number": None}
        updates["Bulk Release"] = {"checkbox": False}

    if media_type == "tv":
        last_ep = details.get("last_episode_to_air")
        next_ep = details.get("next_episode_to_air")
        seasons = details.get("seasons", [])

        # Air Day of Week
        air_day = details.get("air_day_of_week") or None
        if not air_day and next_ep and next_ep.get("air_date"):
            air_day = datetime.fromisoformat(next_ep["air_date"]).strftime("%A")
        if air_day:
            updates["Air Day of Week"] = {"select": {"name": air_day}}

        # First Air Date
        if details.get("first_air_date"):
            updates["First Air Date"] = {"date": {"start": details["first_air_date"]}}

        # Last / Next Air Date
        if last_ep and last_ep.get("air_date"):
            updates["Last Air Date"] = {"date": {"start": last_ep["air_date"]}}
        if next_ep and next_ep.get("air_date"):
            updates["Next Air Date"] = {"date": {"start": next_ep["air_date"]}}
        else:
            updates["Next Air Date"] = None

        # Season / Episode info
        current_ep = last_ep.get("episode_number") if last_ep else None
        current_season_number = last_ep.get("season_number") if last_ep else None
        total_eps = None
        if current_season_number:
            for s in seasons:
                if s.get("season_number") == current_season_number:
                    total_eps = s.get("episode_count")
                    break

        if current_season_number:
            if current_ep:
                updates["Current Season Current Episode"] = {"number": current_ep}
            if total_eps:
                updates["Current Season Total Episodes"] = {"number": total_eps}

        # Season Count
        season_count = details.get("number_of_seasons")
        if season_count and seasons:
            latest_season = max((s for s in seasons if s.get("season_number", 0) > 0), key=lambda s: s.get("season_number", 0), default=None)
            if latest_season and latest_season.get("air_date"):
                try:
                    latest_start = date.fromisoformat(latest_season["air_date"])
                    if latest_start > date.today():
                        season_count -= 1
                except ValueError:
                    pass
        if season_count is not None:
            season_count = max(season_count, 0)
            updates["Season Count"] = {"number": season_count}

        # Latest Season Year
        latest_season_year = None
        for s in reversed(seasons):
            air_date = s.get("air_date")
            if air_date and datetime.fromisoformat(air_date).date() <= date.today():
                latest_season_year = datetime.fromisoformat(air_date).year
                break
        if latest_season_year:
            updates["Latest Season Year"] = {"number": latest_season_year}

        # Bulk Release detection
        ep_dates = {ep.get("air_date") for ep in details.get("episodes", []) if ep.get("air_date")} if details.get("episodes") else set()
        bulk_release = len(ep_dates) == 1 if ep_dates else False
        updates["Bulk Release"] = {"checkbox": bulk_release}

        # Digest events (non-watching specific)
        # NEW: Made configurable via NOTIFICATIONS["new_episode_any_show"]
        if last_ep and is_today(last_ep.get("air_date")) and is_notification_enabled("new_episode_any_show"):
            digest_events.append({"type": "episode", "title": title, "detail": f"S{current_season_number}E{current_ep}"})

        # Series / Season Status
        series_status_key = "IN_PRODUCTION" if details.get("in_production") else ("CANCELLED" if details.get("status") == "Canceled" else "ENDED")
        season_finished = current_ep is not None and total_eps is not None and current_ep >= total_eps
        next_ep_air_date = next_ep.get("air_date") if next_ep else None
        next_ep_season = next_ep.get("season_number") if next_ep else None
        has_future_episode_same_season = next_ep_air_date and next_ep_air_date > today_str() and next_ep_season == current_season_number
        has_future_season = next_ep_air_date and next_ep_air_date > today_str() and next_ep_season != current_season_number

        if has_future_episode_same_season:
            season_status_key = "CURRENTLY_AIRING"
        elif season_finished and has_future_season:
            season_status_key = "UPCOMING"
        elif season_finished:
            season_status_key = "SEASON_FINISHED"
        elif series_status_key == "IN_PRODUCTION":
            season_status_key = "BETWEEN_SEASONS"
        else:
            season_status_key = None

        updates["Series Status"] = select_prop_from_map(SERIES_STATUS_MAP, series_status_key)
        if season_status_key:
            updates["Season Status"] = select_prop_from_map(SEASON_STATUS_MAP, season_status_key)

        # Check for currently watching shows airing today
        watch_status_prop = props.get("Watch Status", {}).get("select")
        watch_status = watch_status_prop.get("name") if watch_status_prop else None
        
        # Check for bulk season drop today (for shows you're watching)
        if (bulk_release and watch_status == "Watching" and last_ep and is_today(last_ep.get("air_date")) 
            and is_notification_enabled("bulk_season_drop")):
            digest_events.append({
                "type": "bulk_season_dropped", 
                "title": title, 
                "detail": f"Season {current_season_number} - All {total_eps} episodes now available!"
            })
        
        if (watch_status == "Watching" and 
            season_status_key == "CURRENTLY_AIRING" and 
            next_ep and is_today(next_ep.get("air_date"))):
            next_season_num = next_ep.get("season_number")
            next_ep_num = next_ep.get("episode_number")
            
            # Check if this is a season finale (next episode is the last of the season)
            is_finale = total_eps is not None and next_ep_num == total_eps
            
            if is_finale and is_notification_enabled("season_finale"):
                digest_events.append({
                    "type": "season_finale_today", 
                    "title": title, 
                    "detail": f"S{next_season_num}E{next_ep_num} - Season Finale!"
                })
            elif not is_finale and is_notification_enabled("episode_airing_today"):
                digest_events.append({
                    "type": "watching_airing_today", 
                    "title": title, 
                    "detail": f"S{next_season_num}E{next_ep_num}"
                })
        
        # Check for shows returning soon (within 7 days)
        if (watch_status == "Watching" and 
            season_status_key in ("BETWEEN_SEASONS", "UPCOMING") and 
            next_ep and is_within_days(next_ep.get("air_date"), days=7)
            and is_notification_enabled("returning_soon")):
            next_season_num = next_ep.get("season_number")
            next_air_date = next_ep.get("air_date")
            
            # Check if we've already notified about this return
            last_returning_warning_prop = props.get("Last Returning Soon Warning", {}).get("date")
            last_returning_warning_date = last_returning_warning_prop.get("start") if last_returning_warning_prop else None
            
            # Only notify once per season return (check if last notification was for a different air date)
            should_notify_return = True
            if last_returning_warning_date and last_returning_warning_date == next_air_date:
                should_notify_return = False
            
            if should_notify_return:
                digest_events.append({
                    "type": "returning_soon", 
                    "title": title, 
                    "detail": f"S{next_season_num} returns {next_air_date}"
                })
                # Update the last warning date to be the air date (so we only notify once per return)
                updates["Last Returning Soon Warning"] = {"date": {"start": next_air_date}}
        
        # Check for long gap warning (30+ days since last episode for currently airing shows)
        if (watch_status == "Watching" and 
            season_status_key == "CURRENTLY_AIRING" and 
            last_ep and last_ep.get("air_date")
            and is_notification_enabled("long_gap")):
            try:
                last_air = date.fromisoformat(last_ep.get("air_date"))
                days_since_last = (date.today() - last_air).days
                
                # Check if we've already notified about this gap
                last_gap_warning_prop = props.get("Last Gap Warning Date", {}).get("date")
                last_gap_warning_date = last_gap_warning_prop.get("start") if last_gap_warning_prop else None
                
                # Only notify if:
                # 1. Gap is 30+ days AND
                # 2. Either never notified before OR last notification was 30+ days ago
                should_notify_gap = days_since_last >= 30
                if last_gap_warning_date:
                    days_since_notification = (date.today() - date.fromisoformat(last_gap_warning_date)).days
                    should_notify_gap = should_notify_gap and days_since_notification >= 30
                
                if should_notify_gap:
                    digest_events.append({
                        "type": "long_gap_warning",
                        "title": title,
                        "detail": f"{days_since_last} days since last episode - might be on hiatus"
                    })
                    # Update the last warning date
                    updates["Last Gap Warning Date"] = {"date": {"start": today_str()}}
            except ValueError:
                pass

        # Next Season Status
        next_season_status = get_next_season_status(details, current_season_number)
        updates["Next Season Status"] = {"select": {"name": next_season_status}}

    # -----------------------------
    # Finalize common fields
    # -----------------------------
    updates["Last Synced"] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}
    for field in PROTECTED_FIELDS:
        updates.pop(field, None)

    if args.dry_run:
        return ("updated", None)

    # Prepare cover URL if poster exists
    cover_url = None
    if details.get("poster_path"):
        cover_url = f"https://image.tmdb.org/t/p/original{details['poster_path']}"
    
    # Return update data for batch processing
    update_data = {
        "page_id": page_id,
        "properties": build_notion_props(updates),
        "cover_url": cover_url,
        "title": title
    }
    
    return ("updated", update_data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--debug-json", nargs="+", help="Print TMDb details JSON for given titles or IMDb IDs and exit")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers for TMDb API calls (default: 10)")

    args = parser.parse_args()

    start_time = time.perf_counter()

    # Debug JSON mode
    if args.debug_json:
        debug_json_mode(args.debug_json, retries=args.retries)
        return

    pages = fetch_all_pages()
    print(f"📦 Pages found: {len(pages)}\n")

    # Filter out digest pages before processing
    non_digest_pages = []
    for page in pages:
        props = page.get("properties", {})
        is_digest = props.get("Is Digest", {}).get("checkbox", False)
        if not is_digest:
            non_digest_pages.append(page)
    
    print(f"📺 Shows to process: {len(non_digest_pages)}\n")

    # PARALLEL FETCH: Get all TMDb data at once
    tmdb_data_cache = fetch_tmdb_data_parallel(non_digest_pages, args, max_workers=args.workers)
    
    print(f"\n📝 Processing pages and preparing updates...\n")

    # Now process pages with cached data
    digest_events = []
    stats = {"updated": 0, "skipped": 0}
    would_update = []
    pending_updates = []  # Collect updates for batch processing

    for page in non_digest_pages:
        try:
            result, update_data = process_page(page, args, tmdb_data_cache, digest_events)

            if args.dry_run and result == "updated":
                props = page.get("properties", {})
                title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                would_update.append(title)
            
            if result == "updated" and update_data and not args.dry_run:
                pending_updates.append(update_data)

            stats[result] += 1

        except Exception as e:
            props = page.get("properties", {})
            title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "Unknown")
            print(f"🔥 ERROR: {title} → {e}")
            stats["skipped"] += 1
    
    # Apply all Notion updates in parallel (if not dry-run)
    if pending_updates and not args.dry_run:
        print(f"\n📤 Applying {len(pending_updates)} Notion updates in parallel...\n")
        update_results = update_notion_pages_parallel(pending_updates, max_workers=5)
        
        # Report any errors
        if update_results["errors"]:
            print(f"\n⚠️ ERRORS DURING UPDATE:")
            for err in update_results["errors"]:
                print(f"  • {err['title']}: {err['error']}")

    # Check for multiple episodes airing today (3+)
    if is_notification_enabled("multiple_episodes_tonight"):
        episodes_today = [e for e in digest_events if e["type"] in ("watching_airing_today", "season_finale_today")]
        if len(episodes_today) >= 3:
            show_names = [e["title"] for e in episodes_today[:3]]
            if len(episodes_today) > 3:
                detail = f"{', '.join(show_names)}, and {len(episodes_today) - 3} more"
            else:
                detail = ', '.join(show_names)
            
            digest_events.append({
                "type": "multiple_episodes_tonight",
                "title": f"{len(episodes_today)} shows airing today",
                "detail": detail
            })
    
    # Log digest to Notion
    log_digest_to_notion(digest_events)

    # Build and send SMS digest
    if digest_events:
        digest_lines = []
        for e in digest_events:
            if e["type"] == "movie":
                digest_lines.append(f"🎬 Movie: {e['title']}")
            elif e["type"] == "episode":
                digest_lines.append(f"📺 Episode: {e['title']} ({e['detail']})")
            elif e["type"] == "bulk":
                digest_lines.append(f"📦 Bulk Season: {e['title']} ({e['detail']})")
            elif e["type"] == "bulk_season_dropped":
                digest_lines.append(f"🍿 SEASON DROP: {e['title']} ({e['detail']})")
            elif e["type"] == "upcoming":
                digest_lines.append(f"🔜 Upcoming Season: {e['title']} (airing {e['detail']})")
            elif e["type"] == "watching_airing_today":
                digest_lines.append(f"📺 Watching Today: {e['title']} ({e['detail']})")
            elif e["type"] == "season_finale_today":
                digest_lines.append(f"🎊 FINALE Today: {e['title']} ({e['detail']})")
            elif e["type"] == "returning_soon":
                digest_lines.append(f"🔄 Returning Soon: {e['title']} ({e['detail']})")
            elif e["type"] == "long_gap_warning":
                digest_lines.append(f"⏸️ Long Gap: {e['title']} ({e['detail']})")
            elif e["type"] == "multiple_episodes_tonight":
                digest_lines.append(f"📅 Busy Night: {e['title']} - {e['detail']}")

        digest_message = "\n".join(digest_lines)
        digest_message = digest_message[:160]
        try:
            send_text(digest_message)
            print("✅ Daily digest SMS sent.")
        except Exception as ex:
            print(f"❌ Failed to send digest SMS: {ex}")
    else:
        print("ℹ️ No digest events to send today.")

    # Summary
    print("\n📊 SUMMARY")
    for k, v in stats.items():
        print(f"{k.title()}: {v}")

    if args.dry_run:
        print("\n🧪 DRY RUN SUMMARY")
        if would_update:
            print("Pages that WOULD be updated:")
            for t in would_update:
                print(f"  • {t}")
        else:
            print("No pages would be updated.")
    
    if args.only_missing and pending_updates:
        print("\n📋 UPDATED SHOWS:")
        for update in pending_updates:
            print(f"  • {update['title']}")

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    minutes, seconds = divmod(int(elapsed), 60)
    pages_processed = sum(stats.values())

    print("\n⏱ RUNTIME STATS")
    print(f"Total time: {elapsed:.2f} seconds ({minutes}m {seconds}s)")

    if elapsed > 0:
        rate = pages_processed / elapsed
        print(f"Throughput: {rate:.2f} pages/sec")

if __name__ == "__main__":
    main()