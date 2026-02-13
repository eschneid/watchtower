import requests
import argparse
import time
from notion_client import Client
from datetime import datetime, date, timezone
import re
from send_text import send_text


# ================= CONFIG =================
NOTION_TOKEN = ""
DATABASE_ID = ""
TMDB_API_KEY = ""
REGION = "US"
DIGEST_PAGE_TITLE = "📩 DAILY DIGEST"
# ==========================================

PROTECTED_FIELDS = {
    "Status",
    "Your Rating",
    "Date Watched",
    "Current Season",
    "Is Finished",
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

        print(f"\n--- TMDb JSON for '{identifier}' ({media_type}) ---")
        print(json.dumps(details, indent=2))



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
        elif e["type"] == "upcoming":
            content = f"🔜 Upcoming season soon: {e['title']} (airing {e['detail']})"
        else:
            continue

        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        })

    notion.pages.create(
        parent={"type": "database_id", "database_id": DATABASE_ID},
        properties={
            "Title": {  # <-- use the exact title property of your database
                "title": [{"text": {"content": f"{DIGEST_PAGE_TITLE} {date.today().isoformat()}"}}]
            },
            "Is Digest": {"checkbox": True}  # <--- Add this line
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
    if args.only_missing or args.only_missing_summary:
        if not tmdb_id:
            return "only-missing"
        return None
    return "normal"

# -----------------------------
# Process single page
# -----------------------------
def process_page(page, args, digest_events=None):
    if digest_events is None:
        digest_events = []

    props = page.get("properties", {})
    page_id = page["id"]

    title_prop = props.get("Title", {}).get("title", [])
    title = title_prop[0]["plain_text"].strip() if title_prop else "Untitled"

    if page.get("archived"):
        print(f"⏭ Archived: {title}")
        return "skipped"

    imdb_id_prop = props.get("IMDb ID", {}).get("rich_text", [])
    imdb_id = imdb_id_prop[0]["plain_text"] if imdb_id_prop else None
    tmdb_id = get_tmdb_id_from_props(props)

    mode = determine_mode(args, imdb_id, tmdb_id)
    if not mode:
        print(f"⏭ Skipped (mode rules): {title}")
        return "skipped"

    if imdb_id and not tmdb_id:
        tmdb_id, media_type = get_tmdb_from_imdb(imdb_id, args.retries)
    else:
        tmdb_id, media_type = search_tmdb(title, args.retries)

    if not tmdb_id or not media_type:
        print(f"⚠️ Could not resolve TMDb for {title}")
        return "skipped"

    details = get_details(tmdb_id, media_type, args.retries)
    if not details:
        print(f"⚠️ TMDb details empty for {title}")
        return "skipped"

    updates = {}

    # -----------------------------
    # Shared fields
    # -----------------------------
    updates["TMDb ID"] = {"number": tmdb_id}

    if details.get("overview"):
        updates["Overview"] = {
            "rich_text": [{"text": {"content": details["overview"]}}]
        }

    if details.get("genres"):
        updates["Genres"] = {
            "multi_select": [{"name": g["name"]} for g in details["genres"] if g.get("name")]
        }

    # Poster (Files & Media) + Page cover
    if details.get("poster_path"):
        poster_url = f"https://image.tmdb.org/t/p/original{details['poster_path']}"
        updates["Poster"] = {
            "files": [{
                "type": "external",
                "name": "Poster",
                "external": {"url": poster_url}
            }]
        }
        notion.pages.update(
            page_id=page_id,
            cover={"type": "external", "external": {"url": poster_url}}
        )

    # -----------------------------
    # Streaming Services
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
        updates["Streaming Services"] = {
            "multi_select": [{"name": s} for s in sorted(mapped)]
        }

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
        updates["Top Cast"] = {
            "multi_select": [{"name": c["name"]} for c in cast if c.get("name")]
        }

    # -----------------------------
    # TV-specific logic
    # -----------------------------

    if media_type == "tv":
        last_ep = details.get("last_episode_to_air")
        next_ep = details.get("next_episode_to_air")
        seasons = details.get("seasons", [])

        # -----------------------------
        # Last / Next Air Dates (FINAL LOGIC)
        # -----------------------------
        last_air_date = last_ep.get("air_date") if last_ep else None
        next_air_date = next_ep.get("air_date") if next_ep else None

        # Last Air Date → always store if present
        if last_air_date:
            updates["Last Air Date"] = {
                "date": {"start": last_air_date}
            }

        # Next Air Date → ONLY based on TMDb next_episode_to_air
        if next_air_date:
            updates["Next Air Date"] = {
                "date": {"start": next_air_date}
            }
        else:
            # No future episode known → clear
            updates["Next Air Date"] = None




        current_ep = None
        total_eps = None
        current_season_number = None

        if last_ep:
            current_ep = last_ep.get("episode_number")
            current_season_number = last_ep.get("season_number")

            for s in seasons:
                if s.get("season_number") == current_season_number:
                    total_eps = s.get("episode_count")
                    break

        # -----------------------------
        # Bulk release detection (UNCHANGED LOGIC)
        # -----------------------------
        bulk_release = False
        if current_season_number:
            ep_dates = {
                ep.get("air_date")
                for ep in details.get("episodes", [])
                if ep.get("air_date")
            }
            bulk_release = len(ep_dates) == 1 if ep_dates else False

        updates["Bulk Release"] = {"checkbox": bulk_release}

        # -----------------------------
        # Digest events
        # -----------------------------
        if last_ep and is_today(last_ep.get("air_date")):
            digest_events.append({
                "type": "episode",
                "title": title,
                "detail": f"S{current_season_number}E{current_ep}"
            })

        if bulk_release:
            digest_events.append({
                "type": "bulk",
                "title": title,
                "detail": f"Season {current_season_number}"
            })

        # -----------------------------
        # Series / Season Status (existing logic preserved)
        # -----------------------------
        series_status_key = (
            "IN_PRODUCTION"
            if details.get("in_production")
            else ("CANCELLED" if details.get("status") == "Canceled" else "ENDED")
        )

        season_finished = (
            current_ep is not None
            and total_eps is not None
            and current_ep >= total_eps
        )

        next_ep_air_date = next_ep.get("air_date") if next_ep else None
        next_ep_season = next_ep.get("season_number") if next_ep else None

        has_future_episode_same_season = (
            next_ep_air_date
            and next_ep_air_date > today_str()
            and next_ep_season == current_season_number
        )

        has_future_season = (
            next_ep_air_date
            and next_ep_air_date > today_str()
            and next_ep_season
            and next_ep_season != current_season_number
        )

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

        updates["Series Status"] = select_prop_from_map(
            SERIES_STATUS_MAP, series_status_key
        )

        if season_status_key:
            updates["Season Status"] = select_prop_from_map(
                SEASON_STATUS_MAP, season_status_key
            )

        # -----------------------------
        # NEW: Next Season Status
        # -----------------------------
        next_season_status = get_next_season_status(
            details, current_season_number
        )

        updates["Next Season Status"] = {
            "select": {"name": next_season_status}
        }

        # -----------------------------
        # Progress fields
        # -----------------------------
        if current_season_number:
            updates["Current Season"] = {"number": current_season_number}

        if current_ep:
            updates["Current Season Current Episode"] = {"number": current_ep}

        if total_eps:
            updates["Current Season Total Episodes"] = {"number": total_eps}


        # -----------------------------
        # Season Count (corrected)
        # -----------------------------
        season_count = details.get("number_of_seasons")
        seasons = details.get("seasons", [])

        if season_count and seasons:
            # Find the latest season by season_number
            latest_season = max(
                (s for s in seasons if s.get("season_number", 0) > 0),
                key=lambda s: s.get("season_number", 0),
                default=None
            )

            if latest_season:
                latest_air_date = latest_season.get("air_date")
                if latest_air_date:
                    try:
                        latest_start = date.fromisoformat(latest_air_date)
                        if latest_start > date.today():
                            season_count -= 1
                    except ValueError:
                        pass

        # Never allow negative seasons
        if season_count is not None:
            season_count = max(season_count, 0)
            updates["Season Count"] = {"number": season_count}




    # -----------------------------
    # Finalize
    # -----------------------------
    updates["Last Synced"] = {
        "date": {"start": datetime.now(timezone.utc).isoformat()}
    }

    for field in PROTECTED_FIELDS:
        updates.pop(field, None)

    if args.dry_run:
        print(f"🧪 DRY-RUN: {title} → {list(updates.keys())}")
        return "updated"

    notion.pages.update(page_id=page_id, properties=build_notion_props(updates))
    print(f"✅ Updated: {title}")
    return "updated"





def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--auto-type", action="store_true")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--only-missing-summary", action="store_true")
    parser.add_argument( "--debug-json", nargs="+", help="Print TMDb details JSON for given titles or IMDb IDs and exit")

    args = parser.parse_args()
    

    start_time = time.perf_counter()

    # Debug JSON mode
    if args.debug_json:
        debug_json_mode(args.debug_json, retries=args.retries)
        return  # exit immediately after printing






    pages = fetch_all_pages()
    print(f"📦 Pages found: {len(pages)}\n")

    digest_events = []
    stats = {"updated": 0, "skipped": 0, "dry": 0, "summary": 0}
    would_update = []

    for page in pages:
        try:
            # Skip pages already included in the digest
            props = page.get("properties", {})
            is_digest = props.get("Is Digest", {}).get("checkbox", False)
            if is_digest:
                stats["skipped"] += 1
                continue

            result = process_page(page, args, digest_events)

            if args.dry_run and result == "updated":
                title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                would_update.append(title)

            stats[result] += 1

        except Exception as e:
            title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "Unknown")
            print(f"🔥 ERROR: {title} → {e}")

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
            elif e["type"] == "upcoming":
                digest_lines.append(f"🔜 Upcoming Season: {e['title']} (airing {e['detail']})")

        digest_message = "\n".join(digest_lines)
        digest_message = digest_message[:160]  # truncate to fit SMS
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

