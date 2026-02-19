# Changelog

All notable changes to Watchtower will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive Notion database schema documentation (`docs/notion-schema.md`)
- `.env.example` template with detailed configuration comments
- Environment variable support via `python-dotenv`
- Movie cleanup: TV-specific fields are now cleared when content is reclassified as a movie
- Fallback resolution for bad TMDb IDs - 404 errors trigger IMDb/title search retry
- Interactive movie exclusion in `discover_movies.py` - select specific movies to skip before adding
- Parallel TMDb API processing with configurable worker count (`--workers` flag)
- `Total Episodes` field now cleared for movies
- Project structure with `tools/` directory for utilities

### Changed
- **Breaking**: Migrated from hardcoded credentials to `.env` configuration
- **Breaking**: `--only-missing-summary` renamed to `--only-missing` with enhanced functionality
- `--only-missing` now force-repopulates all fields (except protected) when TMDb ID is empty
- TMDb ID resolution priority: existing TMDb ID → IMDb ID → title search (was: IMDb or title only)
- Protected fields reduced to: `Status`, `Your Rating`, `Date Watched`
- Removed `Current Season`, `Is Finished`, `Last Long Gap Warning`, `Last Returning Soon Warning` from protected fields
- Property name standardization: `Last Long Gap Warning` → `Last Gap Warning Date`
- Improved error handling and progress reporting in parallel sync operations
- `research_imdb.py` moved to `tools/` directory with parent path imports

### Fixed
- Media type misidentification (e.g., The Running Man movie incorrectly tagged as TV show)
- TMDb ID fallback now properly uses IMDb ID when existing TMDb ID returns 404
- Indentation bug in TV show episode tracking logic
- `discover_movies.py` help examples now show correct flag syntax (`--popular --limit 20`)
- All movies in initial list now visible when using interactive exclusion feature

### Removed
- `--auto-type` flag (media type inference now automatic)
- `--only-missing-summary` flag (merged into `--only-missing`)
- Hardcoded API tokens and credentials from all scripts

## [1.0.0] - 2025-02-01

### Added
- Initial release of Watchtower
- Automated TMDb/IMDb metadata sync to Notion database
- TV show progress tracking (seasons, episodes, air dates)
- Movie metadata management
- Daily digest system with configurable notifications
- SMS notifications via email-to-SMS gateways
- Support for multiple notification types:
  - New episodes airing today
  - Season finales
  - Bulk season drops (Netflix-style releases)
  - Shows returning soon (within 7 days)
  - Long gap warnings (30+ days between episodes)
  - Multiple episodes tonight (3+ shows)
- Streaming service tracking across 45+ platforms
- Cast, crew, and genre metadata
- Poster and trailer integration
- Watch status management
- IMDb and TMDb rating integration
- Series and season status tracking
- Digest page creation in Notion
- Helper scripts:
  - `discover_movies.py` - Add popular/trending movies from TMDb
  - `research_imdb.py` - Interactive TMDb/IMDb lookup tool
  - `inspect_notion.py` - Database inspection utility
  - `add_release.py` - Add release notes to Notion
  - `view_release_notes.py` - View release history

### Technical Details
- Built with Python 3.x
- Uses Notion API for database operations
- Integrates with TMDb API for metadata
- Supports parallel processing for improved performance
- Configurable notification preferences
- Protected fields prevent overwriting user data

---

## Migration Guide

### Upgrading to Unreleased (from 1.0.0)

#### Required Actions

1. **Create `.env` file** from template:
   ```bash
   cp .env.example .env
   ```

2. **Migrate your credentials** to `.env`:
   - Move `NOTION_TOKEN` from hardcoded config
   - Move `DATABASE_ID` from hardcoded config
   - Move `TMDB_API_KEY` from hardcoded config
   - Configure email/SMS settings
   - Set notification preferences

3. **Add new Notion property**:
   - Create `Last Returning Soon Warning` (Date) in your Notion database
   - `Last Gap Warning Date` should already exist

4. **Update property name** (if you have the old one):
   - Rename `Last Long Gap Warning` → `Last Gap Warning Date` in Notion

5. **Install new dependency**:
   ```bash
   pip install python-dotenv
   ```

#### Optional Actions

- Review and adjust notification preferences in `.env`
- Update protected fields if you were relying on old behavior
- Move utility scripts to `tools/` directory if following new structure

#### Command Changes

- Replace `--only-missing-summary` with `--only-missing` in your scripts/cron jobs
- Remove `--auto-type` flag if used (it's now automatic)

---

## Support

For issues, questions, or contributions, please refer to the project README.
