"""
Mock data generator for notion_sync tests.
Generates realistic Notion pages and TMDb API responses for testing.
"""

from datetime import date, timedelta, datetime, timezone

def today_str():
    return date.today().isoformat()

def days_ago(days):
    return (date.today() - timedelta(days=days)).isoformat()

def days_ahead(days):
    return (date.today() + timedelta(days=days)).isoformat()

# ==============================================================================
# MOCK NOTION PAGES
# ==============================================================================

def create_mock_notion_page(title, tmdb_id, watch_status=None, **extra_props):
    """
    Create a mock Notion page structure.
    
    Args:
        title: Show/movie title
        tmdb_id: TMDb ID (or None if not set)
        watch_status: "Watching", "To Watch", "Finished", etc.
        **extra_props: Additional properties like Last Long Gap Warning date
    """
    page = {
        "id": f"mock-page-{tmdb_id or title}",
        "archived": False,
        "properties": {
            "Title": {
                "title": [{"plain_text": title}]
            }
        }
    }
    
    if tmdb_id:
        page["properties"]["TMDb ID"] = {"number": tmdb_id}
    
    if watch_status:
        page["properties"]["Watch Status"] = {
            "select": {"name": watch_status}
        }
    
    # Add extra properties
    for key, value in extra_props.items():
        if key == "Last Long Gap Warning" and value:
            page["properties"][key] = {"date": {"start": value}}
        elif key == "Last Returning Soon Warning" and value:
            page["properties"][key] = {"date": {"start": value}}
    
    return page

# ==============================================================================
# MOCK TMDb API RESPONSES
# ==============================================================================

def create_mock_tv_details(
    tmdb_id,
    title,
    in_production=True,
    status="Returning Series",
    last_episode_air_date=None,
    last_episode_season=None,
    last_episode_number=None,
    next_episode_air_date=None,
    next_episode_season=None,
    next_episode_number=None,
    total_episodes_in_season=None,
    air_day_of_week=None
):
    """
    Create a mock TMDb TV show details response.
    """
    details = {
        "id": tmdb_id,
        "name": title,
        "overview": f"Mock overview for {title}",
        "status": status,
        "in_production": in_production,
        "genres": [{"name": "Drama"}],
        "poster_path": "/mock_poster.jpg",
        "first_air_date": "2020-01-01",
        "number_of_seasons": next_episode_season or last_episode_season or 1,
        "seasons": [],
        "credits": {
            "cast": [
                {"name": "Actor One"},
                {"name": "Actor Two"},
            ]
        },
        "videos": {"results": []},
        "external_ids": {}
    }
    
    if air_day_of_week:
        details["air_day_of_week"] = air_day_of_week
    
    # Last episode to air
    if last_episode_air_date:
        details["last_episode_to_air"] = {
            "air_date": last_episode_air_date,
            "episode_number": last_episode_number or 1,
            "season_number": last_episode_season or 1
        }
    
    # Next episode to air
    if next_episode_air_date:
        details["next_episode_to_air"] = {
            "air_date": next_episode_air_date,
            "episode_number": next_episode_number or 2,
            "season_number": next_episode_season or 1
        }
    
    # Seasons info
    if last_episode_season or next_episode_season:
        season_num = last_episode_season or next_episode_season
        details["seasons"] = [
            {
                "season_number": season_num,
                "episode_count": total_episodes_in_season or 10,
                "air_date": "2020-01-01"
            }
        ]
    
    return details

# ==============================================================================
# TEST SCENARIOS
# ==============================================================================

def get_test_scenarios():
    """
    Returns a list of test scenarios with mock Notion pages and TMDb responses.
    Each scenario tests specific digest notification logic.
    """
    return [
        {
            "name": "Episode airing today - regular episode",
            "notion_page": create_mock_notion_page(
                title="The Test Show",
                tmdb_id=12345,
                watch_status="Watching"
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=12345,
                title="The Test Show",
                last_episode_air_date=days_ago(7),
                last_episode_season=2,
                last_episode_number=5,
                next_episode_air_date=today_str(),
                next_episode_season=2,
                next_episode_number=6,
                total_episodes_in_season=10
            ),
            "expected_events": ["watching_airing_today"]
        },
        
        {
            "name": "Season finale airing today",
            "notion_page": create_mock_notion_page(
                title="Finale Show",
                tmdb_id=23456,
                watch_status="Watching"
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=23456,
                title="Finale Show",
                last_episode_air_date=days_ago(7),
                last_episode_season=1,
                last_episode_number=9,
                next_episode_air_date=today_str(),
                next_episode_season=1,
                next_episode_number=10,
                total_episodes_in_season=10
            ),
            "expected_events": ["season_finale_today"]
        },
        
        {
            "name": "Bulk season drop today",
            "notion_page": create_mock_notion_page(
                title="Netflix Drop",
                tmdb_id=34567,
                watch_status="Watching"
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=34567,
                title="Netflix Drop",
                last_episode_air_date=today_str(),
                last_episode_season=2,
                last_episode_number=8,
                total_episodes_in_season=8
            ),
            "expected_events": ["bulk_season_dropped"],
            "bulk_release": True  # All episodes air on same date
        },
        
        {
            "name": "Show returning in 3 days - first notification",
            "notion_page": create_mock_notion_page(
                title="Coming Back Soon",
                tmdb_id=45678,
                watch_status="Watching"
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=45678,
                title="Coming Back Soon",
                in_production=True,
                last_episode_air_date=days_ago(90),
                last_episode_season=2,
                last_episode_number=10,
                next_episode_air_date=days_ahead(3),
                next_episode_season=3,
                next_episode_number=1,
                total_episodes_in_season=10  # Season 2 had 10 episodes, now finished
            ),
            "expected_events": ["returning_soon"],
            "note": "Season 2 is complete (10/10), Season 3 starts in 3 days"
        },
        
        {
            "name": "Show returning in 3 days - already notified",
            "notion_page": create_mock_notion_page(
                title="Coming Back Soon",
                tmdb_id=45678,
                watch_status="Watching",
                **{"Last Returning Soon Warning": days_ahead(3)}
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=45678,
                title="Coming Back Soon",
                in_production=True,
                last_episode_air_date=days_ago(90),
                last_episode_season=2,
                last_episode_number=10,
                next_episode_air_date=days_ahead(3),
                next_episode_season=3,
                next_episode_number=1,
                total_episodes_in_season=10
            ),
            "expected_events": []  # Should not notify again
        },
        
        {
            "name": "Long gap - 35 days since last episode - first warning",
            "notion_page": create_mock_notion_page(
                title="On Hiatus",
                tmdb_id=56789,
                watch_status="Watching"
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=56789,
                title="On Hiatus",
                in_production=True,
                last_episode_air_date=days_ago(35),
                last_episode_season=3,
                last_episode_number=4,
                next_episode_air_date=days_ahead(30),  # Far in future
                next_episode_season=3,
                next_episode_number=5,
                total_episodes_in_season=10
            ),
            "expected_events": ["long_gap_warning"]
        },
        
        {
            "name": "Long gap - already notified 10 days ago",
            "notion_page": create_mock_notion_page(
                title="On Hiatus",
                tmdb_id=56789,
                watch_status="Watching",
                **{"Last Long Gap Warning": days_ago(10)}
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=56789,
                title="On Hiatus",
                in_production=True,
                last_episode_air_date=days_ago(35),
                last_episode_season=3,
                last_episode_number=4,
                next_episode_air_date=days_ahead(30),
                next_episode_season=3,
                next_episode_number=5,
                total_episodes_in_season=10
            ),
            "expected_events": []  # Should not notify again (only 10 days since last)
        },
        
        {
            "name": "Long gap - notified 35 days ago, should notify again",
            "notion_page": create_mock_notion_page(
                title="Still On Hiatus",
                tmdb_id=67890,
                watch_status="Watching",
                **{"Last Long Gap Warning": days_ago(35)}
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=67890,
                title="Still On Hiatus",
                in_production=True,
                last_episode_air_date=days_ago(70),
                last_episode_season=1,
                last_episode_number=3,
                next_episode_air_date=days_ahead(30),
                next_episode_season=1,
                next_episode_number=4,
                total_episodes_in_season=10
            ),
            "expected_events": ["long_gap_warning"]
        },
        
        {
            "name": "Not watching - should not notify",
            "notion_page": create_mock_notion_page(
                title="Not Watching This",
                tmdb_id=78901,
                watch_status="To Watch"
            ),
            "tmdb_details": create_mock_tv_details(
                tmdb_id=78901,
                title="Not Watching This",
                next_episode_air_date=today_str(),
                next_episode_season=1,
                next_episode_number=1
            ),
            "expected_events": []
        }
    ]
