#!/usr/bin/env python3
"""
Add a new release note to the Watchtower Releases database
Usage: python add_release.py <version> "<description>" [changes...]
"""



from pathlib import Path
import argparse
from notion_client import Client
from datetime import datetime
import sys

# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import NOTION_TOKEN, RELEASES_DATABASE_ID
except ImportError:
    print("❌ ERROR: Missing configuration!")
    print("Please run setup_releases.py first to create the database.")
    exit(1)

notion = Client(auth=NOTION_TOKEN)

RELEASE_TYPES = [
    "✨ Feature",
    "🐛 Bug Fix", 
    "⚡ Performance",
    "💥 Breaking Change",
    "📚 Documentation",
    "🔧 Configuration"
]

def add_release(version, description, release_type, changes, status="✅ Released"):
    """Add a new release to the Releases database"""
    
    # Ensure version starts with 'v'
    if not version.startswith('v'):
        version = f'v{version}'
    
    # Create bullet list blocks for changes
    change_blocks = []
    if changes:
        for change in changes:
            change_blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": change}}]
                }
            })
    
    # Create the release page
    try:
        new_page = notion.pages.create(
            parent={"database_id": RELEASES_DATABASE_ID},
            properties={
                "Version": {
                    "title": [{"text": {"content": version}}]
                },
                "Date": {
                    "date": {"start": datetime.now().strftime("%Y-%m-%d")}
                },
                "Type": {
                    "select": {"name": release_type}
                },
                "Status": {
                    "select": {"name": status}
                },
                "Description": {
                    "rich_text": [{"text": {"content": description}}]
                }
            },
            children=change_blocks if change_blocks else []
        )
        
        print(f"✅ Release {version} added successfully!")
        print(f"   Type: {release_type}")
        print(f"   Description: {description}")
        if changes:
            print(f"   Changes: {len(changes)} item(s)")
        print(f"\n   View: https://notion.so/{new_page['id'].replace('-', '')}")
        
    except Exception as e:
        print(f"❌ Error creating release: {e}")
        sys.exit(1)

def interactive_mode():
    """Interactive mode for adding releases"""
    
    print("🗼 Watchtower Release Notes - Interactive Mode")
    print("="*50)
    
    # Get version
    version = input("\nVersion (e.g., 1.3.0): ").strip()
    if not version:
        print("❌ Version is required")
        return
    
    # Get description
    description = input("Description: ").strip()
    if not description:
        print("❌ Description is required")
        return
    
    # Get type
    print("\nRelease Type:")
    for i, rt in enumerate(RELEASE_TYPES, 1):
        print(f"  {i}. {rt}")
    
    type_choice = input(f"Choose type (1-{len(RELEASE_TYPES)}): ").strip()
    try:
        release_type = RELEASE_TYPES[int(type_choice) - 1]
    except (ValueError, IndexError):
        print("❌ Invalid choice, using '✨ Feature'")
        release_type = "✨ Feature"
    
    # Get status
    print("\nStatus:")
    print("  1. ✅ Released")
    print("  2. 🚧 In Progress")
    print("  3. 📋 Planned")
    
    status_choice = input("Choose status (1-3, default=1): ").strip() or "1"
    status_map = {
        "1": "✅ Released",
        "2": "🚧 In Progress",
        "3": "📋 Planned"
    }
    status = status_map.get(status_choice, "✅ Released")
    
    # Get changes
    print("\nChanges (enter one per line, empty line to finish):")
    changes = []
    while True:
        change = input("  - ").strip()
        if not change:
            break
        changes.append(change)
    
    # Confirm
    print("\n" + "="*50)
    print("Preview:")
    print(f"  Version: {version}")
    print(f"  Description: {description}")
    print(f"  Type: {release_type}")
    print(f"  Status: {status}")
    if changes:
        print(f"  Changes:")
        for change in changes:
            print(f"    - {change}")
    print("="*50)
    
    confirm = input("\nAdd this release? (y/n): ").lower()
    if confirm == 'y':
        add_release(version, description, release_type, changes, status)
    else:
        print("❌ Cancelled")

def main():
    parser = argparse.ArgumentParser(
        description="Add a new release to Watchtower Releases database",
        epilog="Example: python add_release.py 1.3.0 \"Added movie support\" \"Movie notifications\" \"Movie tracking\""
    )
    parser.add_argument("version", nargs="?", help="Version number (e.g., 1.3.0)")
    parser.add_argument("description", nargs="?", help="Brief description of release")
    parser.add_argument("changes", nargs="*", help="List of changes (optional)")
    parser.add_argument("-t", "--type", choices=range(1, len(RELEASE_TYPES)+1), type=int,
                       help=f"Release type (1-{len(RELEASE_TYPES)})", default=1)
    parser.add_argument("-s", "--status", choices=["released", "progress", "planned"],
                       default="released", help="Release status")
    parser.add_argument("-i", "--interactive", action="store_true",
                       help="Interactive mode (prompts for all fields)")
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive or (not args.version and not args.description):
        interactive_mode()
        return
    
    # Validate required args
    if not args.version:
        print("❌ Version is required")
        parser.print_help()
        sys.exit(1)
    
    if not args.description:
        print("❌ Description is required")
        parser.print_help()
        sys.exit(1)
    
    # Map status
    status_map = {
        "released": "✅ Released",
        "progress": "🚧 In Progress",
        "planned": "📋 Planned"
    }
    status = status_map[args.status]
    
    # Get release type
    release_type = RELEASE_TYPES[args.type - 1]
    
    # Add the release
    add_release(args.version, args.description, release_type, args.changes, status)

if __name__ == "__main__":
    main()
