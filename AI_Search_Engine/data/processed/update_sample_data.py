#!/usr/bin/env python3
"""
Sample Data Update Script
Reads SampleData.json and updates content_master table with taxonomy data
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to the Python path (go up 2 levels from data/processed to reach backend)
backend_dir = Path(__file__).parent.parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

try:
    from database import get_connection
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def load_sample_data() -> List[Dict[str, Any]]:
    """Load sample data from JSON file"""
    json_path = Path(__file__).parent / 'SampleData.json'
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} entries from SampleData.json")
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {json_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return []

def update_content_master(sample_data: List[Dict[str, Any]]) -> bool:
    """Update content_master table with taxonomy data from sample data"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            updated_count = 0
            not_found_count = 0
            
            for entry in sample_data:
                # Extract data from JSON entry
                content_id = entry.get('id')
                category = entry.get('category')
                sub_category = entry.get('sub category')  # Note the space in the key
                tags = entry.get('tags', [])
                
                if not content_id:
                    print(f"⚠️ Skipping entry with no ID: {entry.get('title', 'Unknown')}")
                    continue
                
                # Convert tags list to JSON string for storage
                tags_json = json.dumps(tags) if tags else None
                
                # Update the content_master table
                update_query = """
                UPDATE content_master 
                SET category = ?, sub_category = ?, tags = ?, labels_approved = TRUE
                WHERE id = ?
                """
                
                cursor.execute(update_query, (category, sub_category, tags_json, content_id))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    print(f"✅ Updated content ID {content_id}: {entry.get('title', 'Unknown')[:50]}...")
                else:
                    not_found_count += 1
                    print(f"⚠️ Content ID {content_id} not found in database")
            
            # Commit the changes
            conn.commit()
            
            print(f"\n📊 Update Summary:")
            print(f"   ✅ Successfully updated: {updated_count} entries")
            print(f"   ⚠️ Not found in database: {not_found_count} entries")
            print(f"   📝 Total processed: {len(sample_data)} entries")
            
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Main function to run the update process"""
    print("🔄 Starting Sample Data Update Process...")
    print("=" * 50)
    
    # Load sample data
    sample_data = load_sample_data()
    if not sample_data:
        print("❌ No sample data loaded. Exiting.")
        return
    
    # Update database
    print("\n🔄 Updating content_master table...")
    success = update_content_master(sample_data)
    
    if success:
        print("\n✅ Sample data update completed successfully!")
    else:
        print("\n❌ Sample data update failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 