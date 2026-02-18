# 🎬 Movie Discovery for Watchtower

Automatically discover and add popular movies from TMDb to your Notion watchlist.

## 🚀 Quick Start

### Basic Usage

```bash
# Add 20 popular movies
python discover_movies.py --popular

# Add upcoming releases
python discover_movies.py --upcoming

# Add top-rated classics
python discover_movies.py --top-rated

# Add trending movies this week
python discover_movies.py --trending
```

---

## 📊 Movie Sources

### **--popular**
Currently popular movies based on TMDb's algorithm
```bash
python discover_movies.py --popular --limit 30
```

### **--upcoming**
Movies coming to theaters soon (next 4 weeks typically)
```bash
python discover_movies.py --upcoming --limit 20
```

### **--now-playing**
Movies currently in theaters
```bash
python discover_movies.py --now-playing --limit 15
```

### **--top-rated**
Highest-rated movies of all time
```bash
python discover_movies.py --top-rated --limit 50
```

### **--trending**
Hot movies trending this week
```bash
python discover_movies.py --trending
```

---

## 🎯 Filtering Options

### Minimum Rating
Only add highly-rated movies:
```bash
python discover_movies.py --popular --min-rating 7.5
python discover_movies.py --top-rated --min-rating 8.5
```

### Minimum Votes
Filter out movies with few ratings (more reliable):
```bash
python discover_movies.py --upcoming --min-votes 1000
```

### Release Date Range
Only movies from specific time periods:
```bash
# Only 2024 releases
python discover_movies.py --popular --release-after 2024-01-01

# Classic movies (pre-2000)
python discover_movies.py --top-rated --release-before 2000-01-01 --min-rating 8.0

# Movies from 2020-2023
python discover_movies.py --popular --release-after 2020-01-01 --release-before 2024-01-01
```

### Limit Results
Control how many movies to add:
```bash
python discover_movies.py --trending --limit 10
```

### Multiple Pages
Fetch more results (20 per page):
```bash
python discover_movies.py --popular --pages 3 --limit 50
```

---

## ⚙️ Advanced Examples

### High-Quality Recent Movies
```bash
python discover_movies.py --popular \
  --min-rating 7.5 \
  --min-votes 1000 \
  --release-after 2023-01-01 \
  --limit 30
```

### Classic Cinema Collection
```bash
python discover_movies.py --top-rated \
  --min-rating 8.0 \
  --release-before 2000-01-01 \
  --limit 100
```

### Upcoming Blockbusters
```bash
python discover_movies.py --upcoming \
  --min-votes 500 \
  --limit 20
```

### This Year's Best
```bash
python discover_movies.py --popular \
  --release-after 2024-01-01 \
  --min-rating 7.0 \
  --limit 50
```

---

## 🔧 Options Reference

```
Movie Sources (choose one):
  --popular              Popular movies right now
  --upcoming             Upcoming theatrical releases
  --now-playing          Currently in theaters
  --top-rated            Highest-rated movies (all-time)
  --trending             Trending this week

Filters:
  --limit N              Max movies to add (default: 20)
  --min-rating X.X       Minimum rating (e.g., 7.0)
  --min-votes N          Minimum vote count (e.g., 1000)
  --release-after DATE   Released after date (YYYY-MM-DD)
  --release-before DATE  Released before date (YYYY-MM-DD)
  --include-adult        Include adult content (default: excluded)
  --pages N              Number of pages to fetch (20 per page)

Other Options:
  --status STATUS        Watch status (default: "To Watch")
                        Choices: To Watch, Watching, Watched, On Hold
  --dry-run              Preview without adding to Notion
```

---

## 📝 What Gets Added

For each movie, the script adds:

✅ **Basic Info:**
- Title
- TMDb ID
- Type (Movie)
- Watch Status

✅ **Details:**
- Release Date
- IMDb Rating
- Overview/Synopsis
- Runtime
- Genres

✅ **Media:**
- Poster image
- Trailer link (if available)

✅ **Credits:**
- Top 5 cast members
- Director(s)

---

## 🎬 Typical Workflows

### Weekly Movie Discovery
```bash
# Every Friday, add new popular movies
python discover_movies.py --popular --min-rating 7.0 --limit 10
```

### Build "To Watch" Queue
```bash
# One-time: Add 100 top-rated classics
python discover_movies.py --top-rated --min-rating 8.0 --limit 100
```

### Track New Releases
```bash
# Monthly: Add upcoming releases
python discover_movies.py --upcoming --release-after 2024-03-01 --limit 20
```

### Curated Collection
```bash
# Add high-quality 2023 movies you missed
python discover_movies.py --popular \
  --release-after 2023-01-01 \
  --release-before 2024-01-01 \
  --min-rating 7.5 \
  --min-votes 2000 \
  --limit 50
```

---

## 🔍 Dry Run Mode

Preview what would be added without making changes:

```bash
python discover_movies.py --popular --dry-run
```

Output:
```
🎬 Movies to add:
  1. Dune: Part Two (2024) - ⭐ 8.4/10
  2. Oppenheimer (2023) - ⭐ 8.3/10
  3. Poor Things (2023) - ⭐ 7.9/10
  ...

🧪 DRY RUN - No movies were added to Notion
```

---

## 🚨 Duplicate Prevention

The script automatically:
- ✅ Checks existing movies in Notion
- ✅ Skips duplicates (matches by TMDb ID)
- ✅ Only adds new movies

Example output:
```
📊 Summary:
  Total found: 40
  Already in Notion: 25
  New to add: 15
```

---

## ⏰ Automation Ideas

### Windows Task Scheduler
Run every Sunday at 8 PM:
```
Program: python
Arguments: C:\path\to\discover_movies.py --popular --limit 10
Start in: C:\path\to\watchtower
```

### Daily Upcoming Check
```
python discover_movies.py --upcoming --limit 5
```

### Weekly Trending Update
```
python discover_movies.py --trending --min-rating 7.0
```

---

## 💡 Pro Tips

1. **Start with top-rated** to build a solid foundation:
   ```bash
   python discover_movies.py --top-rated --min-rating 8.5 --limit 100
   ```

2. **Use min-votes** for reliability - more votes = more reliable rating:
   ```bash
   --min-votes 1000
   ```

3. **Combine filters** for precise curation:
   ```bash
   --min-rating 7.5 --min-votes 2000 --release-after 2020-01-01
   ```

4. **Use --dry-run** first to preview before committing

5. **Schedule weekly runs** to keep discovering new movies automatically

---

## 🎯 Common Use Cases

| Goal | Command |
|------|---------|
| Build initial watchlist | `--top-rated --min-rating 8.0 --limit 100` |
| Weekly new movies | `--popular --min-rating 7.0 --limit 10` |
| Theater planning | `--now-playing --min-votes 500` |
| Classics collection | `--top-rated --release-before 2000-01-01` |
| 2024 best movies | `--popular --release-after 2024-01-01 --min-rating 7.5` |

---

## 🐛 Troubleshooting

**No movies added:**
- Check if they're already in your database
- Lower `--min-rating` threshold
- Increase `--limit`

**API errors:**
- Verify TMDb API key in `.env`
- Check internet connection
- TMDb might be rate-limiting (wait 10 seconds)

**Movies missing details:**
- Some movies may not have full data yet
- Script will skip movies it can't fetch details for

---

## 🎬 Example Session

```bash
$ python discover_movies.py --popular --min-rating 7.5 --limit 15

======================================================================
🎬 MOVIE DISCOVERY FOR WATCHTOWER
======================================================================

🔍 Fetching movies from TMDb...
✅ Found 40 popular movies
🔍 Applying filters...
✅ 28 movies after filtering
📚 Fetching existing movies from Notion...
✅ Found 145 existing movies in Notion

📊 Summary:
  Total found: 15
  Already in Notion: 8
  New to add: 7

🎬 Movies to add:
  1. Dune: Part Two (2024) - ⭐ 8.4/10
  2. Civil War (2024) - ⭐ 7.8/10
  3. Monkey Man (2024) - ⭐ 7.6/10
  4. Godzilla x Kong (2024) - ⭐ 7.5/10
  5. The Fall Guy (2024) - ⭐ 7.9/10
  6. Challengers (2024) - ⭐ 7.7/10
  7. Abigail (2024) - ⭐ 7.5/10

Add these 7 movies to Notion? (y/n): y

📝 Adding movies to Notion...
  [1/7] Dune: Part Two... ✅
  [2/7] Civil War... ✅
  [3/7] Monkey Man... ✅
  [4/7] Godzilla x Kong... ✅
  [5/7] The Fall Guy... ✅
  [6/7] Challengers... ✅
  [7/7] Abigail... ✅

======================================================================
🎉 COMPLETE!
======================================================================
  ✅ Added: 7

  View in Notion: https://notion.so/2f441253de01808a8146ea6fb613f163
```

Happy movie discovering! 🍿
