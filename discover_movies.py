#!/usr/bin/env python3
"""
Movie Discovery Script for Watchtower
Automatically finds and adds popular/upcoming movies from TMDb to your Notion database
"""

import argparse
import requests
from notion_client import Client
from datetime import datetime, timedelta
import time

try:
    from config import NOTION_TOKEN, DATABASE_ID, TMDB_API_KEY, REGION
except ImportError:
    print("❌ ERROR: config.py not found!")
    print("Please ensure .env file exists with required credentials.")
    exit(1)

notion = Client(auth=NOTION_TOKEN)

# ==================== TMDb API Functions ====================

def tmdb_get(url, params, retries=3):
    """Make TMDb API request with retry logic"""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"⚠️  API error: {e}")
                return None
            time.sleep(1)
    return None

def get_popular_movies(pages=1):
    """Get currently popular movies"""
    movies = []
    for page in range(1, pages + 1):
        data = tmdb_get(
            "https://api.themoviedb.org/3/movie/popular",
            {"api_key": TMDB_API_KEY, "language": "en-US", "page": page}
        )
        if data:
            movies.extend(data.get("results", []))
    return movies

def get_upcoming_movies(pages=1):
    """Get upcoming theatrical releases"""
    movies = []
    for page in range(1, pages + 1):
        data = tmdb_get(
            "https://api.themoviedb.org/3/movie/upcoming",
            {"api_key": TMDB_API_KEY, "language": "en-US", "region": REGION, "page": page}
        )
        if data:
            movies.extend(data.get("results", []))
    return movies

def get_now_playing(pages=1):
    """Get movies currently in theaters"""
    movies = []
    for page in range(1, pages + 1):
        data = tmdb_get(
            "https://api.themoviedb.org/3/movie/now_playing",
            {"api_key": TMDB_API_KEY, "language": "en-US", "region": REGION, "page": page}
        )
        if data:
            movies.extend(data.get("results", []))
    return movies

def get_top_rated_movies(pages=1):
    """Get highest-rated movies"""
    movies = []
    for page in range(1, pages + 1):
        data = tmdb_get(
            "https://api.themoviedb.org/3/movie/top_rated",
            {"api_key": TMDB_API_KEY, "language": "en-US", "page": page}
        )
        if data:
            movies.extend(data.get("results", []))
    return movies

def get_trending_movies(time_window="week"):
    """Get trending movies (day or week)"""
    data = tmdb_get(
        f"https://api.themoviedb.org/3/trending/movie/{time_window}",
        {"api_key": TMDB_API_KEY}
    )
    return data.get("results", []) if data else []

def get_movie_details(tmdb_id):
    """Get full movie details"""
    return tmdb_get(
        f"https://api.themoviedb.org/3/movie/{tmdb_id}",
        {"api_key": TMDB_API_KEY, "append_to_response": "credits,videos"}
    )

# ==================== Notion Functions ====================

def fetch_existing_movies():
    """Get all existing movies from Notion database"""
    print("📚 Fetching existing movies from Notion...")
    
    pages = []
    cursor = None
    
    while True:
        response = notion.databases.query(
            database_id=DATABASE_ID,
            start_cursor=cursor,
            page_size=100,
            filter={
                "property": "Type",
                "select": {"equals": "Movie"}
            }
        )
        
        pages.extend(response["results"])
        
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    
    # Extract TMDb IDs
    existing_ids = set()
    for page in pages:
        props = page.get("properties", {})
        tmdb_id = props.get("TMDb ID", {}).get("number")
        if tmdb_id:
            existing_ids.add(int(tmdb_id))
    
    print(f"✅ Found {len(existing_ids)} existing movies in Notion")
    return existing_ids

def add_movie_to_notion(movie_data, status="To Watch", dry_run=False):
    """Add a movie to Notion database"""
    
    title = movie_data.get("title", "Unknown Title")
    tmdb_id = movie_data.get("id")
    
    if dry_run:
        print(f"  [DRY RUN] Would add: {title}")
        return True
    
    try:
        # Get full details
        details = get_movie_details(tmdb_id)
        if not details:
            print(f"  ⚠️  Could not fetch details for {title}")
            return False
        
        # Build properties
        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "TMDb ID": {"number": tmdb_id},
            "Type": {"select": {"name": "Movie"}},
            "Watch Status": {"select": {"name": status}}
        }
        
        # Release date
        if details.get("release_date"):
            properties["Release Date"] = {"date": {"start": details["release_date"]}}
        
        # Rating
        if details.get("vote_average"):
            properties["IMDb Rating"] = {"number": details["vote_average"]}
        
        # Overview
        if details.get("overview"):
            properties["Overview"] = {
                "rich_text": [{"text": {"content": details["overview"][:2000]}}]  # Notion limit
            }
        
        # Genres
        if details.get("genres"):
            properties["Genres"] = {
                "multi_select": [{"name": g["name"]} for g in details["genres"][:5]]
            }
        
        # Runtime
        if details.get("runtime"):
            properties["Runtime (min)"] = {"number": details["runtime"]}
        
        # Cast (top 5)
        cast = details.get("credits", {}).get("cast", [])[:5]
        if cast:
            # Sanitize cast names (remove commas for Notion multi_select)
            sanitized_cast = [{"name": c["name"].replace(",", ";")} for c in cast if c.get("name")]
            properties["Top Cast"] = {"multi_select": sanitized_cast}
        
        # Directors
        crew = details.get("credits", {}).get("crew", [])
        directors = [c for c in crew if c.get("job") == "Director"][:3]
        if directors:
            sanitized_directors = [{"name": d["name"].replace(",", ";")} for d in directors if d.get("name")]
            properties["Director(s)"] = {"multi_select": sanitized_directors}
        
        # Poster
        if details.get("poster_path"):
            poster_url = f"https://image.tmdb.org/t/p/original{details['poster_path']}"
            properties["Poster"] = {
                "files": [{"type": "external", "name": "Poster", "external": {"url": poster_url}}]
            }
        
        # Trailer
        videos = details.get("videos", {}).get("results", [])
        trailer = next((v for v in videos if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
        if trailer:
            trailer_url = f"https://www.youtube.com/watch?v={trailer['key']}"
            properties["Trailer URL"] = {"url": trailer_url}
        
        # Create page
        new_page = notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )
        
        # Set cover image
        if details.get("poster_path"):
            notion.pages.update(
                page_id=new_page["id"],
                cover={"type": "external", "external": {"url": poster_url}}
            )
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error adding {title}: {e}")
        return False

# ==================== Filtering Functions ====================

def filter_movies(movies, args):
    """Filter movies based on command-line arguments"""
    
    filtered = movies
    
    # Min rating
    if args.min_rating:
        filtered = [m for m in filtered if m.get("vote_average", 0) >= args.min_rating]
    
    # Min votes (popularity threshold)
    if args.min_votes:
        filtered = [m for m in filtered if m.get("vote_count", 0) >= args.min_votes]
    
    # Release date range
    if args.release_after:
        cutoff = datetime.strptime(args.release_after, "%Y-%m-%d").date()
        filtered = [m for m in filtered if m.get("release_date") and 
                   datetime.strptime(m["release_date"], "%Y-%m-%d").date() >= cutoff]
    
    if args.release_before:
        cutoff = datetime.strptime(args.release_before, "%Y-%m-%d").date()
        filtered = [m for m in filtered if m.get("release_date") and 
                   datetime.strptime(m["release_date"], "%Y-%m-%d").date() <= cutoff]
    
    # Exclude adult content
    if not args.include_adult:
        filtered = [m for m in filtered if not m.get("adult", False)]
    
    return filtered

def display_movie_list(movies, show_all=False):
    """Display formatted movie list"""
    display_count = len(movies) if show_all else min(len(movies), 10)
    
    for i, movie in enumerate(movies[:display_count], 1):
        title = movie.get("title", "Unknown")
        year = movie.get("release_date", "")[:4] if movie.get("release_date") else "N/A"
        rating = movie.get("vote_average", 0)
        print(f"  {i}. {title} ({year}) - ⭐ {rating}/10")
    
    if not show_all and len(movies) > 10:
        print(f"  ... and {len(movies) - 10} more")

def interactive_exclude(movies):
    """Allow user to interactively exclude movies from the list"""
    
    print("\n🎯 Exclude specific movies? (optional)")
    print("   Enter numbers to exclude (e.g., 3,5,7) or press Enter to keep all")
    print()
    
    exclude_input = input("Exclude: ").strip()
    
    if not exclude_input:
        return movies
    
    try:
        # Parse exclusion list
        exclude_indices = [int(x.strip()) for x in exclude_input.split(',')]
        
        # Validate indices
        invalid = [i for i in exclude_indices if i < 1 or i > len(movies)]
        if invalid:
            print(f"⚠️  Invalid numbers: {invalid} (valid range: 1-{len(movies)})")
            return movies
        
        # Remove duplicates and sort
        exclude_indices = sorted(set(exclude_indices))
        
        # Create new list excluding selected movies
        excluded_movies = [movies[i-1] for i in exclude_indices]
        remaining_movies = [m for i, m in enumerate(movies, 1) if i not in exclude_indices]
        
        # Show what was excluded
        print(f"\n❌ Excluded {len(excluded_movies)} movie(s):")
        for movie in excluded_movies:
            title = movie.get("title", "Unknown")
            year = movie.get("release_date", "")[:4] if movie.get("release_date") else "N/A"
            print(f"   • {title} ({year})")
        
        # Show updated list
        if remaining_movies:
            print(f"\n✅ Updated list ({len(remaining_movies)} movies):")
            display_movie_list(remaining_movies, show_all=True)
        
        return remaining_movies
        
    except ValueError:
        print("⚠️  Invalid input format. Use comma-separated numbers (e.g., 1,3,5)")
        return movies

# ==================== Main Function ====================

def main():
    parser = argparse.ArgumentParser(
        description="Discover and add movies from TMDb to your Notion watchlist",
        epilog="Examples:\n"
               "  python discover_movies.py --popular --limit 20\n"
               "  python discover_movies.py --upcoming --min-rating 7.0\n"
               "  python discover_movies.py --trending --limit 10\n"
               "  python discover_movies.py --top-rated --min-rating 8.5 --limit 50",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Source options
    source_group = parser.add_argument_group("Movie Sources (choose one)")
    source = source_group.add_mutually_exclusive_group(required=True)
    source.add_argument("--popular", action="store_true", help="Popular movies right now")
    source.add_argument("--upcoming", action="store_true", help="Upcoming theatrical releases")
    source.add_argument("--now-playing", action="store_true", help="Currently in theaters")
    source.add_argument("--top-rated", action="store_true", help="Highest-rated movies (all-time)")
    source.add_argument("--trending", action="store_true", help="Trending this week")
    
    # Filter options
    filter_group = parser.add_argument_group("Filters")
    filter_group.add_argument("--limit", type=int, default=20, help="Max movies to add (default: 20)")
    filter_group.add_argument("--min-rating", type=float, help="Minimum rating (e.g., 7.0)")
    filter_group.add_argument("--min-votes", type=int, help="Minimum vote count (e.g., 1000)")
    filter_group.add_argument("--release-after", help="Released after date (YYYY-MM-DD)")
    filter_group.add_argument("--release-before", help="Released before date (YYYY-MM-DD)")
    filter_group.add_argument("--include-adult", action="store_true", help="Include adult content")
    
    # Status option
    parser.add_argument("--status", default="To Watch", 
                       choices=["To Watch", "Watching", "Watched", "On Hold"],
                       help="Watch status for added movies (default: To Watch)")
    
    # Other options
    parser.add_argument("--dry-run", action="store_true", help="Preview without adding to Notion")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch (20 movies per page)")
    parser.add_argument("--no-interactive", action="store_true", help="Skip interactive exclusion prompt")
    
    args = parser.parse_args()
    
    print("="*70)
    print("🎬 MOVIE DISCOVERY FOR WATCHTOWER")
    print("="*70)
    print()
    
    # Fetch movies from TMDb
    print("🔍 Fetching movies from TMDb...")
    
    if args.popular:
        movies = get_popular_movies(args.pages)
        source_name = "Popular"
    elif args.upcoming:
        movies = get_upcoming_movies(args.pages)
        source_name = "Upcoming"
    elif args.now_playing:
        movies = get_now_playing(args.pages)
        source_name = "Now Playing"
    elif args.top_rated:
        movies = get_top_rated_movies(args.pages)
        source_name = "Top Rated"
    elif args.trending:
        movies = get_trending_movies()
        source_name = "Trending"
    
    print(f"✅ Found {len(movies)} {source_name.lower()} movies")
    
    # Apply filters
    if args.min_rating or args.min_votes or args.release_after or args.release_before:
        print(f"🔍 Applying filters...")
        movies = filter_movies(movies, args)
        print(f"✅ {len(movies)} movies after filtering")
    
    # Limit results
    movies = movies[:args.limit]
    
    # Get existing movies
    existing_ids = fetch_existing_movies()
    
    # Filter out existing
    new_movies = [m for m in movies if m.get("id") not in existing_ids]
    
    print(f"\n📊 Summary:")
    print(f"  Total found: {len(movies)}")
    print(f"  Already in Notion: {len(movies) - len(new_movies)}")
    print(f"  New to add: {len(new_movies)}")
    
    if not new_movies:
        print("\n✅ No new movies to add!")
        return
    
    # Show preview
    print(f"\n🎬 Movies to add:")
    # Always show all movies if we're going to ask for exclusions
    show_all = not args.no_interactive and not args.dry_run
    display_movie_list(new_movies, show_all=show_all)
    
    # Interactive exclusion
    if not args.no_interactive and not args.dry_run:
        new_movies = interactive_exclude(new_movies)
        
        if not new_movies:
            print("\n❌ No movies remaining after exclusions!")
            return
    
    if args.dry_run:
        print("\n🧪 DRY RUN - No movies were added to Notion")
        return
    
    # Confirm
    print()
    confirm = input(f"Add these {len(new_movies)} movies to Notion? (y/n): ").lower()
    
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    # Add movies
    print(f"\n📝 Adding movies to Notion...")
    added = 0
    failed = 0
    
    for i, movie in enumerate(new_movies, 1):
        title = movie.get("title", "Unknown")
        print(f"  [{i}/{len(new_movies)}] {title}...", end=" ")
        
        if add_movie_to_notion(movie, args.status):
            print("✅")
            added += 1
        else:
            print("❌")
            failed += 1
        
        # Rate limiting
        time.sleep(0.3)
    
    # Summary
    print("\n" + "="*70)
    print("🎉 COMPLETE!")
    print("="*70)
    print(f"  ✅ Added: {added}")
    if failed:
        print(f"  ❌ Failed: {failed}")
    print(f"\n  View in Notion: https://notion.so/{DATABASE_ID.replace('-', '')}")
    print()

if __name__ == "__main__":
    main()