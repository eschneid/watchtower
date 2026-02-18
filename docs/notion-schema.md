# Notion Database Schema

This document describes the complete structure of the Notion database used by Watchtower.

## Database Overview

**Database Name:** ERS Movies & Shows  
**Database ID:** `2f441253de01808a8146ea6fb613f163`  
**Icon:** 🎬

## Required Properties

### Core Identification Fields

| Property | Type | Description |
|----------|------|-------------|
| **Title** | Title | Show or movie name |
| **Type** | Select | "Movie" or "TV" |
| **TMDb ID** | Number | The Movie Database identifier |
| **IMDb ID** | Rich Text | IMDb identifier (e.g., tt1234567) |
| **IMDb Link** | URL | Direct link to IMDb page |

### User Management Fields

| Property | Type | Description |
|----------|------|-------------|
| **Watch Status** | Select | Current viewing status |
| **Your Rating** | Select | User's personal rating (★ to ★★★★★) |
| **Date Watched** | Date | When you watched it |
| **Tags** | Multi-select | Custom tags (default: "Eric") |

**Watch Status Options:**
- Wish List
- Watching
- On Hold
- Watched
- Not started
- Abandoned
- Not watched

**Your Rating Options:**
- ★★★★★ (5 stars)
- ★★★★ (4 stars)
- ★★★ (3 stars)
- ★★ (2 stars)
- ★ (1 star)

### TV Show Tracking Fields

| Property | Type | Description |
|----------|------|-------------|
| **Season Status** | Select | Current season viewing status |
| **Series Status** | Select | Production status of the show |
| **Next Season Status** | Select | Status of upcoming season |
| **Current Season Current Episode** | Number | Episode number you're on |
| **Current Season Total Episodes** | Number | Total episodes in current season |
| **Season Count** | Number | Total number of seasons |
| **Latest Season Year** | Number | Year of most recent season |
| **Total Episodes** | Number | Total episodes across all seasons |

**Season Status Options:**
- Currently Airing 📺
- Season Finished ✅
- Between Seasons ⏸️
- Upcoming Season 🔜

**Series Status Options:**
- In Production 🟢
- Ended ⚪
- Cancelled 🔴

**Next Season Status Options:**
- Cancelled
- Coming Soon
- Announced
- No Info

### Air Date Tracking

| Property | Type | Description |
|----------|------|-------------|
| **First Air Date** | Date | When the show first aired |
| **Last Air Date** | Date | Most recent episode air date |
| **Next Air Date** | Date | Upcoming episode air date |
| **Next Season Release Date** | Date | When next season starts |
| **Air Day of Week** | Select | Day of week show airs |
| **Release Date** | Date | Movie release date |

**Air Day of Week Options:**
- Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday

### Notification Tracking (for digest system)

| Property | Type | Description |
|----------|------|-------------|
| **Last Returning Soon Warning** | Date | Last time "returning soon" notification sent |
| **Last Gap Warning Date** | Date | Last time "long gap" warning sent |
| **Last Returning Soon Date** | Date | (legacy field) |
| **Last Long Gap Warning** | Date | (legacy field - use Last Gap Warning Date instead) |

### Content Metadata

| Property | Type | Description |
|----------|------|-------------|
| **Overview** | Rich Text | Plot summary/description |
| **Genres** | Multi-select | Content genres |
| **Top Cast** | Multi-select | Top 5 cast members |
| **Director(s)** | Multi-select | Directors |
| **Poster** | Files & Media | Show/movie poster image |
| **Trailer URL** | URL | YouTube trailer link |
| **Trailer** | Formula | Formatted trailer link with styling |

**Common Genres:**
- Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, History, Horror, Kids, Music, Mystery, News, Reality, Romance, Science Fiction, Sci-Fi & Fantasy, Talk, Thriller, TV Movie, War, War & Politics, Western

### Streaming & Availability

| Property | Type | Description |
|----------|------|-------------|
| **Streaming Services** | Multi-select | Where content is available |
| **Streaming First Seen** | Date | When first detected on streaming |

**Supported Streaming Services:**
- Netflix, Netflix Standard with Ads
- Amazon Prime Video, Amazon Prime Video with Ads, Amazon Prime
- HBO Max, HBO Max Amazon Channel
- Hulu
- Disney Plus
- Apple TV, Apple TV Amazon Channel
- Paramount+, Paramount Plus Essential, Paramount Plus Premium, Paramount+ Amazon Channel, Paramount+ Roku Premium Channel, Paramount Plus Apple TV Channel
- Peacock, Peacock Premium, Peacock Premium Plus
- AMC, AMC+, AMC Plus Apple TV Channel, AMC+ Amazon Channel
- Crunchyroll, Crunchyroll Amazon Channel
- Starz, Starz Apple TV Channel, Starz Roku Premium Channel, Starz Amazon Channel
- MGM Plus, MGM+ Amazon Channel
- And many more...

### Technical/Admin Fields

| Property | Type | Description |
|----------|------|-------------|
| **Last Synced** | Date | Last time Watchtower updated this entry |
| **Last Updated** | Date | General last updated timestamp |
| **Is Digest** | Checkbox | Marks daily digest summary pages |
| **Upcoming** | Checkbox | Marks upcoming releases |
| **Bulk Release** | Checkbox | Season dropped all at once (e.g., Netflix) |

### Ratings & Statistics

| Property | Type | Description |
|----------|------|-------------|
| **IMDb Rating** | Number | IMDb average rating |
| **Runtime (min)** | Number | Runtime in minutes |
| **Runtime** | Number | (duplicate field) |
| **Episode Length** | Select | Typical episode length |
| **Release Year** | Formula | Extracted from Release Date |

### Formula Fields (Auto-calculated)

These fields are calculated by Notion formulas and should not be manually edited:

| Property | Formula Purpose |
|----------|-----------------|
| **Release Year** | Extracts year from Release Date |
| **Episode Progress** | Shows "S1 • E5 / 10" format |
| **Progress %** | Calculates % of season watched |
| **Release Style** | Shows "🍿 Full season drop" or "📺 Weekly episodes" |
| **Trailer** | Formatted trailer link with styling |
| Various **label:** fields | Prefixes for UI display |

### Action Buttons

| Property | Type | Action |
|----------|------|--------|
| **Fetch Metadata** | Button | Triggers metadata refresh |
| **Mark Finished** | Button | Marks show/movie as watched |

## Database Setup Instructions

### 1. Create the Database

1. In Notion, create a new **Database - Full Page**
2. Name it "ERS Movies & Shows" (or your preferred name)
3. Add the 🎬 icon

### 2. Add Required Properties

You don't need to add ALL properties at once. The minimum required for Watchtower to function:

**Minimum Required:**
- Title (default)
- Type (Select: "Movie", "TV")
- TMDb ID (Number)
- IMDb ID (Rich Text)
- Watch Status (Select: see options above)
- Last Synced (Date)
- Is Digest (Checkbox)

**For TV Shows, also add:**
- Season Status (Select: see options above)
- Series Status (Select: see options above)
- Current Season Current Episode (Number)
- Current Season Total Episodes (Number)
- Last Returning Soon Warning (Date)
- Last Gap Warning Date (Date)

**Recommended Additional Fields:**
- All the metadata fields (Overview, Genres, Top Cast, Poster, etc.)
- Streaming Services (Multi-select)
- Last/Next Air Date (Date fields)

### 3. Get Your Database ID

1. Open your database in Notion
2. Copy the URL - it will look like:
   ```
   https://www.notion.so/YOUR_WORKSPACE/2f441253de01808a8146ea6fb613f163?v=...
   ```
3. The DATABASE_ID is the long string: `2f441253de01808a8146ea6fb613f163`
4. Add it to your `.env` file:
   ```
   DATABASE_ID=your_database_id_here
   ```

### 4. Configure Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Give it a name (e.g., "Watchtower")
4. Copy the **Internal Integration Token**
5. Add it to your `.env` file:
   ```
   NOTION_TOKEN=secret_xxxxxxxxxxxxx
   ```
6. In your Notion database, click **•••** → **Connections** → Add your integration

## Field Notes

### Protected Fields

The following fields are **never** overwritten by Watchtower (they preserve your manual data):

- Watch Status
- Your Rating
- Date Watched

### TV-Specific Fields

These fields are only populated for TV shows and are cleared for movies:

- All Season/Series Status fields
- Episode counts
- Air dates (Last/Next/First)
- Bulk Release checkbox

### Legacy Fields

Some fields may exist in older databases but are no longer actively used:
- Last Long Gap Warning (replaced by Last Gap Warning Date)
- Last Returning Soon Date (replaced by Last Returning Soon Warning)

## Multi-Select Property Limits

Notion has limits on multi-select options. The following properties may have large option lists:

- **Director(s)**: 128+ options
- **Top Cast**: 1000+ options
- **Genres**: 26 options
- **Streaming Services**: 45+ options

Watchtower automatically creates new options as needed when syncing from TMDb.

## Tips

- Use **Views** to filter by Watch Status (Watching, Wish List, etc.)
- Create a **Gallery view** and set the card preview to "Poster" for a visual browsing experience
- Filter by **Season Status = "Currently Airing 📺"** to see active shows
- Sort by **Next Air Date** to see what's coming up next
- Use the **Is Digest** checkbox filter to hide daily digest entries
