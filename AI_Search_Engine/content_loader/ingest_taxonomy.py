#!/usr/bin/env python3
"""
Taxonomy Ingestion Script
Loads taxonomy structure data into the taxonomy_master table
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

try:
    from database import get_connection
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_taxonomy_table():
    """Clear existing taxonomy data"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM taxonomy_master")
            conn.commit()
            logger.info("Cleared existing taxonomy data")
            return True
    except Exception as e:
        logger.error(f"Error clearing taxonomy table: {e}")
        return False

def insert_taxonomy_entry(domain: str, category: str, sub_category: str) -> bool:
    """Insert a single taxonomy entry"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO taxonomy_master (domain, category, sub_category, last_edited)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (domain, category, sub_category))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error inserting taxonomy entry: {e}")
        return False

def ingest_taxonomy_data(taxonomy_data: List[Dict[str, Any]]) -> bool:
    """Ingest taxonomy data from the provided structure"""
    try:
        # Clear existing data
        if not clear_taxonomy_table():
            return False
        
        success_count = 0
        total_count = 0
        
        for entry in taxonomy_data:
            domain = entry.get('domain', '').strip()
            category = entry.get('category', '').strip()
            sub_category = entry.get('sub_category')
            
            # Handle None sub_category (for C1. items)
            if sub_category is not None:
                sub_category = sub_category.strip()
            
            if domain and category:
                if insert_taxonomy_entry(domain, category, sub_category):
                    success_count += 1
                total_count += 1
            else:
                logger.warning(f"Skipping incomplete entry: {entry}")
        
        logger.info(f"Successfully ingested {success_count}/{total_count} taxonomy entries")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error ingesting taxonomy data: {e}")
        return False

def load_taxonomy_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load taxonomy data from a JSON or Markdown file"""
    try:
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.json':
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return data
            else:
                logger.error("JSON file should contain a list of entries")
                return []
                
        elif file_path.suffix.lower() == '.md':
            # Load Markdown file
            return parse_markdown_taxonomy(file_path)
        else:
            logger.error("Unsupported file format. Please use .json or .md files")
            return []
            
    except Exception as e:
        logger.error(f"Error loading taxonomy file: {e}")
        return []

def parse_markdown_taxonomy(file_path: Path) -> List[Dict[str, Any]]:
    """Parse taxonomy data from markdown format"""
    taxonomy_data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        current_domain = ""
        current_category = ""
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Parse domain (starts with **Domain:)
            if line.startswith('**Domain:'):
                # This is a domain
                current_domain = line.replace('**Domain:', '').replace('**', '').strip()
                current_category = ""  # Reset category when new domain
                logger.debug(f"Found domain: {current_domain}")
                
            # Parse category (starts with C1.)
            elif line.startswith('C1.'):
                # This is a category - store it as a row with empty sub_category
                # Remove the C1. prefix from the category name
                current_category = line.replace('C1.', '').strip()
                logger.debug(f"Found category: {current_category}")
                
                # Store the C1. item as a row (sub_category is empty)
                if current_domain and current_category:
                    taxonomy_data.append({
                        "domain": current_domain,
                        "category": current_category,
                        "sub_category": None  # Empty for C1. items
                    })
                    logger.debug(f"Added C1. entry: {current_domain} -> {current_category} -> None")
                    
            # Parse sub-category (starts with C2.)
            elif line.startswith('C2.'):
                # This is a sub-category - store it as a row with the current C1. as category
                # Remove the C2. prefix from the sub_category name
                sub_category = line.replace('C2.', '').strip()
                
                # Add the complete taxonomy entry with C1. as category and C2. as sub-category
                if current_domain and current_category and sub_category:
                    taxonomy_data.append({
                        "domain": current_domain,
                        "category": current_category,
                        "sub_category": sub_category
                    })
                    logger.debug(f"Added C2. entry: {current_domain} -> {current_category} -> {sub_category}")
                elif current_domain and sub_category:
                    # If no C1. category is specified, use the sub-category as category and empty sub_category
                    taxonomy_data.append({
                        "domain": current_domain,
                        "category": sub_category,
                        "sub_category": None
                    })
                    logger.debug(f"Added C2. entry (no C1.): {current_domain} -> {sub_category} -> None")
                    
        logger.info(f"Parsed {len(taxonomy_data)} taxonomy entries from markdown")
        return taxonomy_data
        
    except Exception as e:
        logger.error(f"Error parsing markdown taxonomy: {e}")
        return []

def create_sample_taxonomy_data() -> List[Dict[str, Any]]:
    """Create sample taxonomy data structure for testing"""
    return [
        {
            "domain": "Clinical Care",
            "category": "Pain Management",
            "sub_category": "Opioid Management"
        },
        {
            "domain": "Clinical Care", 
            "category": "Pain Management",
            "sub_category": "Non-Opioid Management"
        },
        {
            "domain": "Clinical Care",
            "category": "Symptom Management", 
            "sub_category": "Nausea and Vomiting"
        },
        {
            "domain": "Psychosocial",
            "category": "Communication",
            "sub_category": "Family Meetings"
        },
        {
            "domain": "Psychosocial",
            "category": "Communication", 
            "sub_category": "Goals of Care"
        }
    ]

def main():
    """Main function to run taxonomy ingestion"""
    print("=== Taxonomy Ingestion Tool ===")
    print()
    
    # Check if taxonomy table exists
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taxonomy_master'")
            if not cursor.fetchone():
                print("❌ Error: taxonomy_master table does not exist. Please run database initialization first.")
                return
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return
    
    # Automatically load from taxonomy.md in the data folder
    data_folder = Path(__file__).parent.parent / "data"
    taxonomy_file = data_folder / "taxonomy.md"
    
    if not taxonomy_file.exists():
        print(f"❌ Error: taxonomy.md file not found at {taxonomy_file}")
        print("Please make sure taxonomy.md exists in the data folder")
        return
    
    print(f"📁 Loading taxonomy from: {taxonomy_file}")
    
    # Load taxonomy data from markdown file
    taxonomy_data = load_taxonomy_from_file(str(taxonomy_file))
    if not taxonomy_data:
        print("❌ Failed to load taxonomy data from file")
        return
    
    print(f"📊 Loaded {len(taxonomy_data)} taxonomy entries")
    
    # Confirm before ingesting
    confirm = input("Proceed with ingestion? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Ingestion cancelled")
        return
    
    print("\n🔄 Ingesting taxonomy data...")
    
    if ingest_taxonomy_data(taxonomy_data):
        print("✅ Taxonomy ingestion completed successfully!")
        
        # Show summary
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM taxonomy_master")
                count = cursor.fetchone()[0]
                print(f"📈 Total taxonomy entries in database: {count}")
                
                cursor.execute("SELECT DISTINCT domain FROM taxonomy_master")
                domains = [row[0] for row in cursor.fetchall()]
                print(f"🏷️ Domains: {', '.join(domains)}")
                
        except Exception as e:
            print(f"⚠️ Could not retrieve summary: {e}")
    else:
        print("❌ Taxonomy ingestion failed")

if __name__ == "__main__":
    main() 