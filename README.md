# 📺 Watchtower

**Watchtower** is an automated media tracking and alert system that keeps your TV shows and movies in sync with real-world release data.

It pulls rich metadata from TMDb, updates a Notion database, tracks season and episode status, detects bulk releases, and sends timely alerts when something important happens — like a new episode dropping or a season finishing.

Think of it as a *release intelligence engine* for streaming content.

---

## ✨ Features

### 🎬 Media Intelligence
- Automatically resolves **movie vs TV** from title or IMDb ID
- Pulls full TMDb **details JSON** (seasons, episodes, cast, networks, trailers)
- Tracks:
  - Season count (excluding future seasons)
  - Total episodes
  - Current season & episode
  - First air date
  - Last air date
  - Next air date
  - Latest season year

### 📡 Streaming Awareness
- Detects where content is streaming (US region)
- Normalizes providers into:
  - Netflix
  - Amazon Prime
  - HBO Max
  - Apple TV
  - Hulu
  - Paramount+
  - Peacock
  - AMC
- Populates **Streaming Services** (multi-select)
- Tracks **Streaming First Seen**

### 🧭 Status Tracking
- **Series Status**
  - In Production 🟢
  - Ended ⚪
  - Cancelled 🔴
- **Season Status**
  - Currently Airing 📺
  - Season Finished ✅
  - Between Seasons ⏸️
  - Upcoming 🔜
- **Next Season Status**
  - Announced
  - Coming Soon
  - No Info
  - Canceled

### 🧠 Smart Logic
- Detects **bulk season releases**
- Adjusts season count when a future season exists
- Always maintains a valid **Next Air Date** when possible
- Auto-handles finales vs future seasons
- Preserves user-controlled fields

### 🗂 Notion Enhancements
- Updates:
  - Genres (multi-select)
  - Top Cast (multi-select)
  - Overview (text)
  - Poster (Files & Media)
  - Page cover image
- Protects manual fields like ratings and watch status

### 🔔 Alerts & Digest
- Generates a **daily digest page** in Notion
- Sends SMS alerts for:
  - New episodes
  - Bulk season drops
  - New movie releases
  - Upcoming seasons

---

## 🛠 Tech Stack

- **Python 3.10+**
- **TMDb API**
- **Notion API**
- Optional SMS integration (Twilio or similar)

---

## 🚀 CLI Usage

```bash
python watchtower.py [options]


Available Flags
Flag	Description
--dry-run	Show what would change without updating Notion
--force-refresh	Re-sync all fields
--only-missing	Only populate missing fields
--only-missing-summary	Skip fully populated pages
--retries N	Retry failed TMDb calls (default: 3)
--debug-json "Title"	Dump full TMDb details JSON and exit


Examples:
python watchtower.py --force-refresh
python watchtower.py --debug-json "The Night Agent"

Debugging:
python watchtower.py --debug-json "Cross"



Notion Database Requirements

Your Notion database should include (at minimum):

Required

Title (Title)

TMDb ID (Number)

IMDb ID (Text)

Supported Properties

Season Count (Number)

Total Episodes (Number)

Current Season (Number)

First Air Date (Date)

Last Air Date (Date)

Next Air Date (Date)

Latest Season Year (Number)

Series Status (Select)

Season Status (Select)

Next Season Status (Select)

Streaming Services (Multi-select)

Genres (Multi-select)

Top Cast (Multi-select)

Overview (Text)

Poster (Files & Media)

Is Digest (Checkbox)



Configuration

Set these at the top of the script:

TMDB_API_KEY = "your_tmdb_key"
NOTION_TOKEN = "your_notion_token"
DATABASE_ID = "your_database_id"
REGION = "US"



## Why “Watchtower”?
Because it:

Watches release schedules
Detects changes
Alerts you before you miss something
Never asks “are we there yet?”







