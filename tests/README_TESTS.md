# Watchtower Test Suite

This test suite allows you to test the digest notification logic without needing an actual Notion database or TMDb API access.

## Files

- **`test_data.py`** - Mock data generator that creates realistic Notion pages and TMDb API responses
- **`test_watchtower.py`** - Test runner that executes all test scenarios
- **`README_TESTS.md`** - This file

## Running Tests

```bash
python test_watchtower.py
```

## Test Scenarios

The test suite includes scenarios for:

1. ✅ **Regular episode airing today** - Should trigger `watching_airing_today`
2. ✅ **Season finale airing today** - Should trigger `season_finale_today`
3. ✅ **Bulk season drop today** - Should trigger `bulk_season_dropped`
4. ✅ **Show returning in 3 days (first time)** - Should trigger `returning_soon`
5. ✅ **Show returning in 3 days (already notified)** - Should NOT trigger (prevents duplicates)
6. ✅ **Long gap - 35 days since last episode (first warning)** - Should trigger `long_gap_warning`
7. ✅ **Long gap - already notified 10 days ago** - Should NOT trigger (too soon)
8. ✅ **Long gap - notified 35 days ago** - Should trigger again (enough time passed)
9. ✅ **Not watching status** - Should NOT trigger any notifications
10. ✅ **Multiple episodes tonight (3+ shows)** - Should aggregate and create summary
11. ✅ **Multiple episodes tonight (<3 shows)** - Should NOT create summary

## Adding New Test Scenarios

Edit `test_data.py` and add a new scenario to the `get_test_scenarios()` function:

```python
{
    "name": "Your test scenario name",
    "notion_page": create_mock_notion_page(
        title="Show Title",
        tmdb_id=99999,
        watch_status="Watching",
        **{"Last Long Gap Warning": days_ago(10)}  # Optional tracking fields
    ),
    "tmdb_details": create_mock_tv_details(
        tmdb_id=99999,
        title="Show Title",
        last_episode_air_date=days_ago(7),
        last_episode_season=2,
        last_episode_number=5,
        next_episode_air_date=today_str(),
        next_episode_season=2,
        next_episode_number=6,
        total_episodes_in_season=10
    ),
    "expected_events": ["watching_airing_today"],  # What you expect to see
    "bulk_release": False  # Set to True for bulk season drops
}
```

## Understanding Test Output

### Passing Test
```
✅ PASS: Episode airing today - regular episode
```

### Failing Test
```
❌ FAIL: Long gap - already notified 10 days ago
   Reason: Expected [], got ['long_gap_warning']
```

## Key Test Dates

Tests use relative dates:
- `today_str()` - Today's date
- `days_ago(7)` - 7 days before today
- `days_ahead(3)` - 3 days from today

This ensures tests always work regardless of when you run them.

## What's Being Tested

The test suite validates:

### Notification Triggers
- Episodes airing today are detected
- Season finales are identified correctly
- Bulk releases are detected
- Return dates within 7 days trigger alerts
- Long gaps (30+ days) are flagged

### Notification Deduplication
- `Last Returning Soon Warning` prevents duplicate alerts
- `Last Long Gap Warning` prevents spam (30-day cooldown)
- Shows without "Watching" status don't trigger alerts

### Aggregation Logic
- Multiple episodes (3+) trigger summary notification
- Fewer than 3 episodes don't trigger summary

## Debugging Failed Tests

If a test fails:

1. Check the expected vs actual events in the output
2. Review the test scenario in `test_data.py`
3. Verify the date logic (is_today, is_within_days)
4. Check the notification tracking fields
5. Ensure the season status logic is correct

## Integration with Real Script

These tests mirror the logic in `watchtower.py` but don't require:
- Actual Notion API credentials
- TMDb API key
- Network access
- Real database

This makes testing fast, reliable, and safe for development.
