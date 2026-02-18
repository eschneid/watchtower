#!/usr/bin/env python3
"""
Notion Database Schema Inspector
Dumps all properties, types, and configuration from a Notion database
"""

import argparse
import json
from notion_client import Client
import sys
from pathlib import Path

# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import NOTION_TOKEN, DATABASE_ID
except ImportError:
    print("❌ ERROR: config.py not found!")
    print("Please ensure .env file exists with NOTION_TOKEN")
    exit(1)

notion = Client(auth=NOTION_TOKEN)

def format_property_details(prop_name, prop_config):
    """Format property configuration details"""
    prop_type = prop_config.get("type")
    details = [f"  📋 {prop_name}"]
    details.append(f"     Type: {prop_type}")
    
    # Add type-specific details
    if prop_type == "select":
        options = prop_config.get("select", {}).get("options", [])
        if options:
            details.append(f"     Options: {len(options)} choices")
            for opt in options:
                details.append(f"       • {opt.get('name')} ({opt.get('color')})")
    
    elif prop_type == "multi_select":
        options = prop_config.get("multi_select", {}).get("options", [])
        if options:
            details.append(f"     Options: {len(options)} choices")
            for opt in options:
                details.append(f"       • {opt.get('name')} ({opt.get('color')})")
    
    elif prop_type == "relation":
        rel_config = prop_config.get("relation", {})
        details.append(f"     Related DB: {rel_config.get('database_id', 'N/A')}")
        details.append(f"     Type: {rel_config.get('type', 'N/A')}")
    
    elif prop_type == "formula":
        formula = prop_config.get("formula", {}).get("expression", "N/A")
        details.append(f"     Expression: {formula}")
    
    elif prop_type == "rollup":
        rollup = prop_config.get("rollup", {})
        details.append(f"     Relation: {rollup.get('relation_property_name', 'N/A')}")
        details.append(f"     Property: {rollup.get('rollup_property_name', 'N/A')}")
        details.append(f"     Function: {rollup.get('function', 'N/A')}")
    
    return "\n".join(details)

def inspect_database(db_id, show_json=False):
    """Inspect a Notion database and display its schema"""
    
    print(f"🔍 Inspecting database: {db_id}")
    print("="*70)
    
    try:
        # Retrieve database metadata
        db = notion.databases.retrieve(database_id=db_id)
        
        # Basic info
        title = db.get("title", [])
        db_title = title[0].get("plain_text", "Untitled") if title else "Untitled"
        
        print(f"\n📚 Database: {db_title}")
        print(f"   ID: {db_id}")
        print(f"   URL: https://notion.so/{db_id.replace('-', '')}")
        
        # Icon & Cover
        icon = db.get("icon")
        if icon:
            if icon.get("type") == "emoji":
                print(f"   Icon: {icon.get('emoji')}")
            elif icon.get("type") == "external":
                print(f"   Icon: {icon.get('external', {}).get('url', 'N/A')}")
        
        # Parent info
        parent = db.get("parent", {})
        parent_type = parent.get("type")
        print(f"   Parent: {parent_type}")
        
        # Properties
        properties = db.get("properties", {})
        print(f"\n📊 Properties: {len(properties)} total")
        print("-"*70)
        
        # Group by type
        type_groups = {}
        for prop_name, prop_config in properties.items():
            prop_type = prop_config.get("type")
            if prop_type not in type_groups:
                type_groups[prop_type] = []
            type_groups[prop_type].append((prop_name, prop_config))
        
        # Display grouped by type
        for prop_type in sorted(type_groups.keys()):
            print(f"\n🏷️  {prop_type.upper()} ({len(type_groups[prop_type])})")
            for prop_name, prop_config in type_groups[prop_type]:
                print(format_property_details(prop_name, prop_config))
        
        # Summary
        print("\n" + "="*70)
        print("📈 SUMMARY")
        print("="*70)
        for prop_type, props in sorted(type_groups.items()):
            print(f"  {prop_type:20s} : {len(props):3d} properties")
        
        # Full JSON output if requested
        if show_json:
            print("\n" + "="*70)
            print("📄 FULL JSON SCHEMA")
            print("="*70)
            print(json.dumps(db, indent=2))
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        return False
    
    return True

def list_all_databases():
    """List all databases the integration has access to"""
    
    print("🗂️  Searching for accessible databases...")
    print("="*70)
    
    try:
        # Search for all databases
        results = notion.search(filter={"property": "object", "value": "database"})
        
        databases = results.get("results", [])
        
        if not databases:
            print("⚠️  No databases found")
            print("   Make sure your integration has access to your databases")
            return
        
        print(f"\n✅ Found {len(databases)} database(s):\n")
        
        for i, db in enumerate(databases, 1):
            title = db.get("title", [])
            db_title = title[0].get("plain_text", "Untitled") if title else "Untitled"
            db_id = db.get("id")
            
            icon = db.get("icon")
            icon_str = ""
            if icon and icon.get("type") == "emoji":
                icon_str = icon.get("emoji", "") + " "
            
            print(f"{i}. {icon_str}{db_title}")
            print(f"   ID: {db_id}")
            print(f"   URL: https://notion.so/{db_id.replace('-', '')}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing databases: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Inspect Notion database schema and properties"
    )
    parser.add_argument(
        "database_id",
        nargs="?",
        help="Database ID to inspect (optional, uses DATABASE_ID from config if not provided)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all accessible databases"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Show full JSON schema"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Inspect all accessible databases"
    )
    
    args = parser.parse_args()
    
    # List mode
    if args.list:
        list_all_databases()
        return
    
    # Inspect all mode
    if args.all:
        results = notion.search(filter={"property": "object", "value": "database"})
        databases = results.get("results", [])
        
        for i, db in enumerate(databases, 1):
            title = db.get("title", [])
            db_title = title[0].get("plain_text", "Untitled") if title else "Untitled"
            db_id = db.get("id")
            
            print(f"\n{'='*70}")
            print(f"DATABASE {i}/{len(databases)}: {db_title}")
            print(f"{'='*70}")
            
            inspect_database(db_id, args.json)
            
            if i < len(databases):
                input("\nPress Enter to continue to next database...")
        return
    
    # Inspect specific database
    db_id = args.database_id or DATABASE_ID
    
    if not db_id:
        print("❌ No database ID provided")
        print("\nUsage:")
        print("  python inspect_notion.py                    # Use DATABASE_ID from config")
        print("  python inspect_notion.py <database-id>      # Inspect specific database")
        print("  python inspect_notion.py --list             # List all databases")
        print("  python inspect_notion.py --all              # Inspect all databases")
        return
    
    inspect_database(db_id, args.json)

if __name__ == "__main__":
    main()
