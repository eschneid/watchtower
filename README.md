# 🗼 Watchtower

Automatically sync TV show/movie data from TMDb to Notion and receive daily digest notifications via SMS.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Settings
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env with your credentials
# - Notion token and database ID
# - TMDb API key
# - Gmail/SMS settings
```

### 3. Run Watchtower
```bash
# Full sync with notifications
python watchtower.py --workers 20 --force-refresh

# Dry run (preview changes)
python watchtower.py --dry-run

# Only update missing data
python watchtower.py --only-missing
```

## 📋 Configuration

All settings are in `.env`:

### Required Settings
- `NOTION_TOKEN` - Your Notion integration token
- `DATABASE_ID` - Your Notion database ID
- `TMDB_API_KEY` - TMDb API key

### Optional Settings
- `EMAIL_FROM` / `EMAIL_PASSWORD` - For SMS notifications
- `VERIZON_NUMBER` - Your phone@carrier-gateway.com
- `NOTIFY_*` - Enable/disable specific notification types

### Notification Types
Toggle notifications in `.env`:
- `NOTIFY_EPISODE_AIRING_TODAY` - Episodes airing today
- `NOTIFY_SEASON_FINALE` - Season finales
- `NOTIFY_BULK_SEASON_DROP` - Netflix-style season drops
- `NOTIFY_RETURNING_SOON` - Shows returning within 7 days
- `NOTIFY_LONG_GAP` - Shows on hiatus (30+ days)
- `NOTIFY_MULTIPLE_EPISODES_TONIGHT` - Busy TV nights (3+ shows)

## 🎯 Command Line Options

```bash
--workers N              # Parallel TMDb API workers (default: 10)
--force-refresh          # Update all fields (recommended for daily runs)
--dry-run                # Preview changes without updating
--only-missing           # Only process shows without TMDb ID
--debug-json "Title"     # Print raw TMDb JSON for debugging
```

## 📱 SMS Setup

1. Get Gmail app password: https://myaccount.google.com/apppasswords
2. Find your carrier's SMS gateway:
   - Verizon: `@vtext.com`
   - AT&T: `@txt.att.net`
   - T-Mobile: `@tmomail.net`
3. Update `.env` with your credentials

## 🧪 Testing

```bash
# Run test suite
python test_watchtower.py

# Test SMS
python send_text.py "Test message"
```

## ⚡ Performance

- **164 shows**: ~4 minutes (down from 12 minutes!)
- **Parallel processing**: TMDb API + Notion updates
- **Smart caching**: Reduces unnecessary API calls

## 🔒 Security

- `.env` file is git-ignored (never committed)
- `.env.example` is the template (safe to share)
- All secrets stored in environment variables

## 📚 Documentation

- `README.md` - This file (setup & usage)
- `FUTURE_FEATURES.md` - Roadmap & feature ideas
- `README_TESTS.md` - Testing documentation

## 💡 Tips

- Run with `--force-refresh` daily to catch episode updates
- Use `--workers 20` for fastest TMDb fetching
- Notion updates limited to 5 workers (API rate limits)

## 🆘 Troubleshooting

**SMS not sending?**
- Verify Gmail app password is correct
- Check carrier gateway address
- Test with: `python send_text.py "Test"`

**Slow performance?**
- Increase workers: `--workers 20`
- Use `--only-missing` for quick updates
- Check network connection

**Missing configuration?**
- Ensure `.env` exists (copy from `.env.example`)
- Verify all required fields are filled
- Check for typos in environment variable names