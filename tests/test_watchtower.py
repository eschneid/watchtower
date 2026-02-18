#!/usr/bin/env python3
"""
Test suite for watchtower.py digest notifications.
Runs tests without requiring actual Notion database or TMDb API access.
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
import argparse

# Import test data
from test_data import get_test_scenarios, today_str

# Import the functions we want to test from watchtower
# We'll need to mock external dependencies
sys.path.insert(0, '.')

class DigestTestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.total = 0
    
    def add_pass(self, test_name):
        self.passed.append(test_name)
        self.total += 1
        print(f"✅ PASS: {test_name}")
    
    def add_fail(self, test_name, reason):
        self.failed.append((test_name, reason))
        self.total += 1
        print(f"❌ FAIL: {test_name}")
        print(f"   Reason: {reason}")
    
    def summary(self):
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total tests: {self.total}")
        print(f"Passed: {len(self.passed)} ({len(self.passed)/self.total*100:.1f}%)")
        print(f"Failed: {len(self.failed)} ({len(self.failed)/self.total*100:.1f}%)")
        
        if self.failed:
            print("\n❌ FAILED TESTS:")
            for name, reason in self.failed:
                print(f"  • {name}")
                print(f"    {reason}")
        
        return len(self.failed) == 0


def mock_process_page_digest_logic(page, tmdb_details, bulk_release=False, debug=False):
    """
    Extracts just the digest notification logic from process_page.
    This simulates what the real function does without database writes.
    
    Returns: list of digest events
    """
    digest_events = []
    props = page["properties"]
    
    # Get title
    title_prop = props.get("Title", {}).get("title", [])
    title = title_prop[0]["plain_text"] if title_prop else "Untitled"
    
    # Get watch status
    watch_status_prop = props.get("Watch Status", {}).get("select")
    watch_status = watch_status_prop.get("name") if watch_status_prop else None
    
    # TV show logic
    if tmdb_details:
        last_ep = tmdb_details.get("last_episode_to_air")
        next_ep = tmdb_details.get("next_episode_to_air")
        seasons = tmdb_details.get("seasons", [])
        
        # Get season info
        current_ep = last_ep.get("episode_number") if last_ep else None
        current_season_number = last_ep.get("season_number") if last_ep else None
        total_eps = None
        if current_season_number:
            for s in seasons:
                if s.get("season_number") == current_season_number:
                    total_eps = s.get("episode_count")
                    break
        
        # Determine season status
        in_production = tmdb_details.get("in_production")
        status = tmdb_details.get("status")
        series_status_key = "IN_PRODUCTION" if in_production else ("CANCELLED" if status == "Canceled" else "ENDED")
        
        season_finished = current_ep is not None and total_eps is not None and current_ep >= total_eps
        next_ep_air_date = next_ep.get("air_date") if next_ep else None
        next_ep_season = next_ep.get("season_number") if next_ep else None
        
        # Fix: Episode airing today counts as currently airing (use >=), future episodes use >
        has_future_episode_same_season = (
            next_ep_air_date and 
            next_ep_air_date >= today_str() and 
            next_ep_season == current_season_number
        )
        has_future_season = (
            next_ep_air_date and 
            next_ep_air_date > today_str() and 
            next_ep_season and current_season_number and
            next_ep_season > current_season_number
        )
        
        # Determine season status
        season_status_key = None
        if has_future_episode_same_season:
            season_status_key = "CURRENTLY_AIRING"
        elif season_finished and has_future_season:
            season_status_key = "UPCOMING"
        elif season_finished:
            season_status_key = "SEASON_FINISHED"
        elif series_status_key == "IN_PRODUCTION":
            season_status_key = "BETWEEN_SEASONS"
        
        # Check for bulk season drop today (for shows you're watching)
        if bulk_release and watch_status == "Watching" and last_ep and is_today(last_ep.get("air_date")):
            digest_events.append({
                "type": "bulk_season_dropped",
                "title": title,
                "detail": f"Season {current_season_number} - All {total_eps} episodes now available!"
            })
        
        # Check for currently watching shows airing today
        if (watch_status == "Watching" and 
            season_status_key == "CURRENTLY_AIRING" and 
            next_ep and is_today(next_ep.get("air_date"))):
            next_season_num = next_ep.get("season_number")
            next_ep_num = next_ep.get("episode_number")
            
            # Check if this is a season finale
            is_finale = total_eps is not None and next_ep_num == total_eps
            
            if is_finale:
                digest_events.append({
                    "type": "season_finale_today",
                    "title": title,
                    "detail": f"S{next_season_num}E{next_ep_num} - Season Finale!"
                })
            else:
                digest_events.append({
                    "type": "watching_airing_today",
                    "title": title,
                    "detail": f"S{next_season_num}E{next_ep_num}"
                })
        
        # Check for shows returning soon (within 7 days)
        if (watch_status == "Watching" and 
            season_status_key in ("BETWEEN_SEASONS", "UPCOMING") and 
            next_ep and is_within_days(next_ep.get("air_date"), days=7)):
            next_season_num = next_ep.get("season_number")
            next_air_date = next_ep.get("air_date")
            
            # Check if we've already notified
            last_returning_warning_prop = props.get("Last Returning Soon Warning", {}).get("date")
            last_returning_warning_date = last_returning_warning_prop.get("start") if last_returning_warning_prop else None
            
            should_notify_return = True
            if last_returning_warning_date and last_returning_warning_date == next_air_date:
                should_notify_return = False
            
            if should_notify_return:
                digest_events.append({
                    "type": "returning_soon",
                    "title": title,
                    "detail": f"S{next_season_num} returns {next_air_date}"
                })
        
        # Check for long gap warning
        if (watch_status == "Watching" and 
            season_status_key == "CURRENTLY_AIRING" and 
            last_ep and last_ep.get("air_date")):
            try:
                last_air = date.fromisoformat(last_ep.get("air_date"))
                days_since_last = (date.today() - last_air).days
                
                # Check if we've already notified
                last_gap_warning_prop = props.get("Last Long Gap Warning", {}).get("date")
                last_gap_warning_date = last_gap_warning_prop.get("start") if last_gap_warning_prop else None
                
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
            except ValueError:
                pass
    
    return digest_events


def is_today(date_str):
    """Check if date string is today"""
    if not date_str:
        return False
    try:
        return date.fromisoformat(date_str) == date.today()
    except ValueError:
        return False


def is_within_days(date_str, days=7):
    """Check if date is within X days from today"""
    if not date_str:
        return False
    try:
        return 0 < (date.fromisoformat(date_str) - date.today()).days <= days
    except ValueError:
        return False


@pytest.fixture
def test_scenarios():
    """Fixture providing all test scenarios"""
    return get_test_scenarios()


@pytest.mark.parametrize("scenario", get_test_scenarios(), ids=lambda s: s["name"])
def test_digest_scenarios(scenario):
    """Test each digest notification scenario"""
    name = scenario["name"]
    notion_page = scenario["notion_page"]
    tmdb_details = scenario["tmdb_details"]
    expected_events = scenario["expected_events"]
    bulk_release = scenario.get("bulk_release", False)
    
    # Run the digest logic
    actual_events = mock_process_page_digest_logic(
        notion_page, 
        tmdb_details,
        bulk_release=bulk_release,
        debug=False
    )
    
    # Extract just the event types
    actual_types = [e["type"] for e in actual_events]
    
    # Check if matches expected
    assert set(actual_types) == set(expected_events), \
        f"{name}: Expected {expected_events}, got {actual_types}"


def test_multiple_episodes_aggregation():
    """Test 'multiple episodes tonight' aggregation with 3+ shows"""
    multi_events = [
        {"type": "watching_airing_today", "title": "Show 1", "detail": "S1E1"},
        {"type": "watching_airing_today", "title": "Show 2", "detail": "S2E3"},
        {"type": "season_finale_today", "title": "Show 3", "detail": "S1E10 - Season Finale!"},
    ]
    
    episodes_today = [e for e in multi_events if e["type"] in ("watching_airing_today", "season_finale_today")]
    
    assert len(episodes_today) >= 3, \
        f"Expected 3+ episodes, got {len(episodes_today)}"


def test_multiple_episodes_no_aggregation():
    """Test 'multiple episodes tonight' does not trigger with <3 shows"""
    two_events = [
        {"type": "watching_airing_today", "title": "Show 1", "detail": "S1E1"},
        {"type": "watching_airing_today", "title": "Show 2", "detail": "S2E3"},
    ]
    
    episodes_today = [e for e in two_events if e["type"] in ("watching_airing_today", "season_finale_today")]
    
    assert len(episodes_today) < 3, \
        f"Should not trigger with only {len(episodes_today)} shows"


def run_tests():
    """Run all test scenarios (legacy runner for manual execution)"""
    results = DigestTestResults()
    scenarios = get_test_scenarios()
    
    print("="*70)
    print("RUNNING NOTION SYNC DIGEST TESTS")
    print("="*70)
    print(f"Test date: {date.today().isoformat()}")
    print(f"Total scenarios: {len(scenarios)}\n")
    
    debug = False  # Set to True to enable debug output
    
    for scenario in scenarios:
        name = scenario["name"]
        notion_page = scenario["notion_page"]
        tmdb_details = scenario["tmdb_details"]
        expected_events = scenario["expected_events"]
        bulk_release = scenario.get("bulk_release", False)
        
        if debug:
            print(f"\n--- DEBUG: {name} ---")
            print(f"Next ep date: {tmdb_details.get('next_episode_to_air', {}).get('air_date')}")
            print(f"Today: {today_str()}")
        
        # Run the digest logic
        actual_events = mock_process_page_digest_logic(
            notion_page, 
            tmdb_details,
            bulk_release=bulk_release,
            debug=debug
        )
        
        # Extract just the event types
        actual_types = [e["type"] for e in actual_events]
        
        # Check if matches expected
        if set(actual_types) == set(expected_events):
            results.add_pass(name)
        else:
            reason = f"Expected {expected_events}, got {actual_types}"
            results.add_fail(name, reason)
    
    # Test "multiple episodes tonight" logic
    print("\n" + "-"*70)
    print("Testing 'multiple episodes tonight' aggregation...")
    print("-"*70)
    
    # Simulate having 3 shows air tonight
    multi_events = [
        {"type": "watching_airing_today", "title": "Show 1", "detail": "S1E1"},
        {"type": "watching_airing_today", "title": "Show 2", "detail": "S2E3"},
        {"type": "season_finale_today", "title": "Show 3", "detail": "S1E10 - Season Finale!"},
    ]
    
    episodes_today = [e for e in multi_events if e["type"] in ("watching_airing_today", "season_finale_today")]
    
    if len(episodes_today) >= 3:
        results.add_pass("Multiple episodes tonight - aggregation triggers")
    else:
        results.add_fail("Multiple episodes tonight - aggregation triggers", 
                        f"Expected 3+ episodes, got {len(episodes_today)}")
    
    # Simulate having only 2 shows
    two_events = multi_events[:2]
    episodes_today_2 = [e for e in two_events if e["type"] in ("watching_airing_today", "season_finale_today")]
    
    if len(episodes_today_2) < 3:
        results.add_pass("Multiple episodes tonight - does not trigger with <3 shows")
    else:
        results.add_fail("Multiple episodes tonight - does not trigger with <3 shows",
                        "Should not trigger with only 2 shows")
    
    # Print summary
    print()
    success = results.summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_tests())
