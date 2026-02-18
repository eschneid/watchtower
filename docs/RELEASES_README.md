# 📝 Watchtower Release Notes System

Automated release notes management for Watchtower using Notion.

## 🚀 Quick Start

### 1. Initial Setup (One Time)

```bash
python setup_releases.py
```

This will:
- ✅ Create "🗼 Watchtower Releases" database in Notion
- ✅ Add initial release history (v1.0.0, v1.1.0, v1.2.0)
- ✅ Update your `.env` with `RELEASES_DATABASE_ID`

### 2. Add New Releases

**Quick command line:**
```bash
python add_release.py 1.3.0 "Added movie support" "Movie notifications" "Movie tracking" "Movie-specific fields"
```

**Interactive mode:**
```bash
python add_release.py -i
```

## 📋 Database Schema

Your Releases database has these fields:

| Field | Type | Description |
|-------|------|-------------|
| **Version** | Title | Version number (e.g., v1.3.0) |
| **Date** | Date | Release date (auto-set to today) |
| **Type** | Select | ✨ Feature, 🐛 Bug Fix, ⚡ Performance, etc. |
| **Status** | Select | ✅ Released, 🚧 In Progress, 📋 Planned |
| **Description** | Text | Brief description of release |
| **Changes** | Page content | Bulleted list of changes |

## 🎯 Usage Examples

### Quick Release (Command Line)
```bash
# Simple
python add_release.py 1.3.0 "Bug fixes"

# With changes
python add_release.py 1.3.0 "Performance improvements" \
    "Fixed memory leak" \
    "Optimized database queries" \
    "Added caching"

# Specify type and status
python add_release.py 1.4.0 "Upcoming features" -t 1 -s planned
```

### Interactive Mode
```bash
python add_release.py -i

# Then answer the prompts:
Version (e.g., 1.3.0): 1.3.0
Description: Added movie support
Release Type:
  1. ✨ Feature
  2. 🐛 Bug Fix
  3. ⚡ Performance
  4. 💥 Breaking Change
  5. 📚 Documentation
  6. 🔧 Configuration
Choose type (1-6): 1
Status:
  1. ✅ Released
  2. 🚧 In Progress
  3. 📋 Planned
Choose status (1-3, default=1): 1
Changes (enter one per line, empty line to finish):
  - Movie notifications
  - Movie tracking fields
  - Movie poster support
  - (press Enter)
```

## 🎨 Release Types

1. **✨ Feature** - New functionality
2. **🐛 Bug Fix** - Fixed issues
3. **⚡ Performance** - Speed/efficiency improvements
4. **💥 Breaking Change** - Incompatible changes
5. **📚 Documentation** - Docs updates
6. **🔧 Configuration** - Config changes

## 📊 Command Reference

```bash
# Basic usage
python add_release.py <version> "<description>" [changes...]

# Options
-t, --type          Release type (1-6)
-s, --status        Status: released, progress, planned
-i, --interactive   Interactive mode

# Examples
python add_release.py 1.3.0 "Bug fixes"
python add_release.py 1.4.0 "New feature" -t 1 -s planned
python add_release.py -i
```

## 🔍 View Your Releases

After running `setup_releases.py`, you'll get a Notion link like:
```
https://notion.so/your-workspace/database-id
```

You can:
- ✅ View all releases in Notion
- ✅ Filter by type or status
- ✅ Sort by date
- ✅ Search versions
- ✅ Add custom fields

## 💡 Tips

1. **Version numbering**: Use semantic versioning (major.minor.patch)
   - `1.0.0` → First release
   - `1.1.0` → New feature
   - `1.1.1` → Bug fix
   - `2.0.0` → Breaking change

2. **Keep it brief**: Description should be 1 sentence
   - ✅ "Added movie support"
   - ❌ "In this release we have added support for movies which includes..."

3. **Atomic changes**: Each bullet should be one thing
   - ✅ "Fixed SMS sending error"
   - ❌ "Fixed bugs and improved performance"

4. **Use emojis**: They make it easier to scan
   - Already included in the Type field!

## 🔧 Troubleshooting

**"RELEASES_DATABASE_ID not found"**
- Run `python setup_releases.py` first

**"Permission denied"**
- Make sure your Notion integration has access to the workspace

**Database not showing up**
- Check your Notion workspace
- Look for "🗼 Watchtower Releases"
- It should be at the top level or near your main Watchtower database

## 📚 Sample Release History

The setup script adds these sample releases:

- **v1.2.0** (2026-02-14) - Performance improvements
  - Parallel TMDb processing
  - Parallel Notion updates
  - 67% faster runtime

- **v1.1.0** (2026-02-14) - Configuration modernization
  - Switched to .env
  - Carrier-agnostic SMS
  - BCC-style sending

- **v1.0.0** (2026-02-13) - Initial release
  - TMDb sync
  - Daily digests
  - Episode alerts

You can edit or delete these after setup!
