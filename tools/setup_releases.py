#!/usr/bin/env python3
"""
Setup script for Watchtower Release Notes
Creates a Releases database in Notion and configures it for use.
"""

import sys
from pathlib import Path
from notion_client import Client
from datetime import datetime
import os

# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))


try:
    from config import NOTION_TOKEN, DATABASE_ID
except ImportError:
    print("❌ ERROR: config.py not found!")
    print("Please ensure .env file exists with NOTION_TOKEN")
    exit(1)

notion = Client(auth=NOTION_TOKEN)

def create_releases_database():
    """Create the Releases database in Notion"""
    
    print("🚀 Creating Watchtower Releases database in Notion...")
    
    # Try to get the parent page from the main Watchtower database
    parent_id = None
    try:
        main_db = notion.databases.retrieve(database_id=DATABASE_ID)
        parent_info = main_db.get("parent", {})
        
        if parent_info.get("type") == "page_id":
            parent_id = parent_info.get("page_id")
            print(f"✅ Found parent page from Watchtower database")
        elif parent_info.get("type") == "workspace":
            print("⚠️  Main database is at workspace root")
            
    except Exception as e:
        print(f"⚠️  Could not retrieve main database: {e}")
    
    # If no parent found, ask user for a page ID
    if not parent_id:
        print("\n📝 Notion databases need a parent page.")
        print("   Options:")
        print("   1. Open any page in Notion")
        print("   2. Copy the page URL")
        print("   3. Paste the URL or just the page ID below")
        print("\n   Example URL: https://notion.so/My-Page-1234567890abcdef...")
        print("   Example ID: 1234567890abcdef1234567890abcdef")
        
        user_input = input("\n   Enter page URL or ID: ").strip()
        
        if not user_input:
            print("❌ No parent page provided. Exiting.")
            exit(1)
        
        # Extract page ID from URL if needed
        if "notion.so/" in user_input:
            # Extract ID from URL
            parts = user_input.split("/")[-1].split("?")[0].split("#")[0]
            # Remove dashes and get last 32 chars
            parent_id = parts.replace("-", "")[-32:]
        else:
            parent_id = user_input.replace("-", "")
        
        # Validate it's a proper ID (32 hex chars)
        if len(parent_id) != 32:
            print(f"❌ Invalid page ID: {parent_id}")
            print("   Page IDs should be 32 characters long")
            exit(1)
        
        print(f"✅ Using parent page: {parent_id}")
    
    parent_spec = {"type": "page_id", "page_id": parent_id}
    
    # Create the database
    new_database = notion.databases.create(
        parent=parent_spec,
        icon={
            "type": "emoji",
            "emoji": "📝"
        },
        title=[
            {
                "type": "text",
                "text": {"content": "🗼 Watchtower Releases"}
            }
        ],
        properties={
            "Version": {
                "title": {}  # Title column
            },
            "Date": {
                "date": {}
            },
            "Type": {
                "select": {
                    "options": [
                        {"name": "✨ Feature", "color": "green"},
                        {"name": "🐛 Bug Fix", "color": "red"},
                        {"name": "⚡ Performance", "color": "blue"},
                        {"name": "💥 Breaking Change", "color": "orange"},
                        {"name": "📚 Documentation", "color": "gray"},
                        {"name": "🔧 Configuration", "color": "purple"}
                    ]
                }
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "✅ Released", "color": "green"},
                        {"name": "🚧 In Progress", "color": "yellow"},
                        {"name": "📋 Planned", "color": "blue"}
                    ]
                }
            },
            "Description": {
                "rich_text": {}
            }
        }
    )
    
    db_id = new_database['id']
    print(f"✅ Database created successfully!")
    print(f"   Database ID: {db_id}")
    print(f"   View it in Notion: https://notion.so/{db_id.replace('-', '')}")
    
    return db_id

def add_initial_releases(db_id):
    """Add initial release notes to demonstrate the system"""
    
    print("\n📝 Adding initial release notes...")
    
    releases = [
        {
            "version": "v1.2.0",
            "date": "2026-02-14",
            "type": "⚡ Performance",
            "status": "✅ Released",
            "description": "Major performance improvements",
            "changes": [
                "Added parallel TMDb API processing (10-20 workers)",
                "Added parallel Notion updates (5 workers)",
                "Runtime reduced from 12 minutes to 4 minutes (67% faster)",
                "Added progress indicators for long-running operations"
            ]
        },
        {
            "version": "v1.1.0",
            "date": "2026-02-14",
            "type": "🔧 Configuration",
            "status": "✅ Released",
            "description": "Modernized configuration system",
            "changes": [
                "Switched from config.py to .env files",
                "Added python-dotenv support",
                "Renamed VERIZON_NUMBER to SMS_RECIPIENTS (carrier-agnostic)",
                "Added SMS_SEND_MODE (individual/group sending)",
                "Added BCC-style SMS sending (recipients hidden from each other)"
            ]
        },
        {
            "version": "v1.0.0",
            "date": "2026-02-13",
            "type": "✨ Feature",
            "status": "✅ Released",
            "description": "Initial release of Watchtower",
            "changes": [
                "TMDb to Notion sync for TV shows",
                "Daily digest notifications via SMS",
                "Episode airing alerts",
                "Season finale detection",
                "Returning soon notifications",
                "Long gap warnings (30+ days)",
                "Configurable notification preferences"
            ]
        }
    ]
    
    for release in releases:
        # Create bullet list blocks for changes
        change_blocks = [
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": change}}]
                }
            }
            for change in release["changes"]
        ]
        
        # Create the release page
        notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "Version": {
                    "title": [{"text": {"content": release["version"]}}]
                },
                "Date": {
                    "date": {"start": release["date"]}
                },
                "Type": {
                    "select": {"name": release["type"]}
                },
                "Status": {
                    "select": {"name": release["status"]}
                },
                "Description": {
                    "rich_text": [{"text": {"content": release["description"]}}]
                }
            },
            children=change_blocks
        )
        
        print(f"   ✅ Added {release['version']}")
    
    print(f"\n✅ Added {len(releases)} release notes")

def update_env_file(db_id):
    """Add RELEASES_DATABASE_ID to .env file"""
    
    print("\n📝 Updating .env file...")
    
    env_path = ".env"
    
    # Read current .env with UTF-8 encoding
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Fallback to reading with errors ignored
            with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
    else:
        print("⚠️  .env file not found, cannot update automatically")
        print(f"   Please manually add: RELEASES_DATABASE_ID={db_id}")
        return
    
    # Check if RELEASES_DATABASE_ID already exists
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("RELEASES_DATABASE_ID="):
            lines[i] = f"RELEASES_DATABASE_ID={db_id}\n"
            updated = True
            break
    
    # If not found, add it after DATABASE_ID
    if not updated:
        for i, line in enumerate(lines):
            if line.startswith("DATABASE_ID="):
                lines.insert(i + 1, f"RELEASES_DATABASE_ID={db_id}\n")
                updated = True
                break
    
    # Write back to .env with UTF-8 encoding
    if updated:
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"✅ Added RELEASES_DATABASE_ID to .env")
        except Exception as e:
            print(f"⚠️  Could not update .env file: {e}")
            print(f"   Please manually add: RELEASES_DATABASE_ID={db_id}")
    else:
        print(f"⚠️  Could not automatically update .env")
        print(f"   Please manually add: RELEASES_DATABASE_ID={db_id}")

def main():
    print("="*60)
    print("🗼 WATCHTOWER RELEASE NOTES SETUP")
    print("="*60)
    print()
    
    # Create database
    db_id = create_releases_database()
    
    # Add sample releases
    add_initial_releases(db_id)
    
    # Update .env
    update_env_file(db_id)
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. View your Releases database in Notion")
    print("  2. Use add_release.py to add new releases:")
    print("     python add_release.py 1.3.0 \"New feature description\"")
    print()
    print(f"Database ID: {db_id}")
    print()

if __name__ == "__main__":
    main()
