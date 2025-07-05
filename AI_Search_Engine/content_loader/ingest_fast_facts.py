"""
Simplified FastFact Ingestion - Loads FastFact files into the database
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Simple import approach
import sys
import os

# Add the backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, '..', 'backend')
sys.path.insert(0, backend_dir)

from services import ContentService
from models import ContentCreate
from database import get_connection

from fast_fact_parser import FastFactParser
from content_mapper import ContentMapper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FastFactIngestion:
    """Simplified FastFact ingestion into the database"""
    
    def __init__(self):
        self.parser = FastFactParser()
        self.mapper = ContentMapper()
        self.content_service = ContentService()
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'errors_list': []
        }
    
    def process_folder(self, input_folder: str) -> Dict[str, Any]:
        """Process all FastFact files in a folder with batch database operations"""
        print(f"Starting FastFact ingestion from: {input_folder}")
        print("=" * 60)
        
        # Reset stats
        self.stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'errors_list': []
        }
        
        # Parse all files first
        parsed_data_list = self.parser.process_all_files(input_folder)
        
        if not parsed_data_list:
            print("No files to process!")
            return self.stats
        
        # Process files in batch with single database connection
        self.process_files_batch(parsed_data_list)
        
        # Print summary
        self.print_summary()
        
        return self.stats
    
    def process_files_batch(self, parsed_data_list: List[Dict[str, Any]]):
        """Process multiple files using batch database operations"""
        print(f"\nProcessing {len(parsed_data_list)} files with batch database operations...")
        
        # Process files in smaller batches to avoid long transactions
        batch_size = 10
        for i in range(0, len(parsed_data_list), batch_size):
            batch = parsed_data_list[i:i+batch_size]
            self.process_batch(batch)
            
            # Small delay to allow database to release locks
            import time
            time.sleep(0.1)
    
    def process_batch(self, parsed_data_batch: List[Dict[str, Any]]):
        """Process a small batch of files with proper connection management"""
        try:
            # Use fresh connection for each batch
            with get_connection() as conn:
                cursor = conn.cursor()
                
                for parsed_data in parsed_data_batch:
                    try:
                        # Map parsed data to content format
                        content_data = self.mapper.map_fast_fact_to_content(parsed_data)
                        
                        # Validate the content data
                        is_valid, validation_message = self.mapper.validate_content_data(content_data)
                        if not is_valid:
                            error_msg = f"Validation failed for {content_data.get('id', 'unknown')}: {validation_message}"
                            self.stats['errors'] += 1
                            self.stats['errors_list'].append(error_msg)
                            print(f"  ✗ {error_msg}")
                            print(f"     File: {parsed_data.get('file_path', 'unknown')}")
                            print(f"     Data: {content_data}")
                            continue
                        
                        content_id = content_data['id']
                        
                        # Check if content already exists (using same connection)
                        cursor.execute('SELECT id FROM content_master WHERE id = ?', (content_id,))
                        if cursor.fetchone():
                            self.stats['skipped'] += 1
                            print(f"  ⏭ Skipped (exists): {content_id} - {content_data['title']}")
                            continue
                        
                        # Insert using same connection
                        success = self.insert_content_batch(cursor, content_data)
                        
                        if success:
                            self.stats['processed'] += 1
                            print(f"  ✓ Created: {content_id} - {content_data['title']}")
                        else:
                            error_msg = f"Failed to save {content_id} to database"
                            self.stats['errors'] += 1
                            self.stats['errors_list'].append(error_msg)
                            print(f"  ✗ {error_msg}")
                            
                    except Exception as e:
                        error_msg = f"Error processing file: {str(e)}"
                        self.stats['errors'] += 1
                        self.stats['errors_list'].append(error_msg)
                        print(f"  ✗ {error_msg}")
                
                # Commit this batch
                conn.commit()
                
        except Exception as e:
            error_msg = f"Database connection error: {str(e)}"
            self.stats['errors'] += len(parsed_data_batch)
            self.stats['errors_list'].append(error_msg)
            print(f"  ✗ {error_msg}")
    
    def insert_content_batch(self, cursor, content_data: Dict[str, Any]) -> bool:
        """Insert content using provided cursor (for batch operations)"""
        try:
            # Convert Pydantic model to dict if needed
            if hasattr(content_data, 'model_dump'):
                data = content_data.model_dump()
            else:
                data = content_data.copy()
            
            # Handle date conversion
            if data.get('last_edited') and hasattr(data['last_edited'], 'isoformat'):
                data['last_edited'] = data['last_edited'].isoformat()
            
            # Convert tags list to JSON string for storage
            import json
            if isinstance(data.get('tags'), list):
                data['tags'] = json.dumps(data['tags'])
            elif data.get('tags') is None:
                data['tags'] = None
            
            # Convert FF_tags list to JSON string for storage
            if isinstance(data.get('FF_tags'), list):
                data['FF_tags'] = json.dumps(data['FF_tags'])
            elif data.get('FF_tags') is None:
                data['FF_tags'] = None
            
            # Convert auto_tags list to JSON string for storage
            if isinstance(data.get('auto_tags'), list):
                data['auto_tags'] = json.dumps(data['auto_tags'])
            elif data.get('auto_tags') is None:
                data['auto_tags'] = None
            
            # Ensure all string fields are actually strings
            string_fields = ['title', 'summary', 'source', 'category', 'sub_category', 'auto_category', 'auto_sub_category', 'url', 'status', 'version']
            for field in string_fields:
                if data.get(field) is not None and data.get(field) != '':
                    data[field] = str(data[field])
                else:
                    data[field] = None
            
            # Insert using cursor
            cursor.execute('''
                INSERT INTO content_master 
                (id, title, summary, source, category, sub_category, tags, FF_tags, auto_category, auto_sub_category, auto_tags, labels_approved, url, last_edited, status, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('id'),
                data.get('title'),
                data.get('summary'),
                data.get('source'),
                data.get('category'),
                data.get('sub_category'),
                data.get('tags'),
                data.get('FF_tags'),
                data.get('auto_category', ''),
                data.get('auto_sub_category', ''),
                data.get('auto_tags', []),
                data.get('labels_approved', False),
                data.get('url'),
                data.get('last_edited'),
                data.get('status', 'active'),
                data.get('version', '1.0')
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error inserting content: {e}")
            return False
    
    def process_single_file(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single parsed FastFact file (legacy method for compatibility)"""
        try:
            # Map parsed data to content format
            content_data = self.mapper.map_fast_fact_to_content(parsed_data)
            
            # Validate the content data
            is_valid, validation_message = self.mapper.validate_content_data(content_data)
            if not is_valid:
                error_msg = f"Validation failed for {content_data.get('id', 'unknown')}: {validation_message}"
                self.stats['errors'] += 1
                self.stats['errors_list'].append(error_msg)
                print(f"  ✗ {error_msg}")
                print(f"     File: {parsed_data.get('file_path', 'unknown')}")
                print(f"     Data: {content_data}")
                return {'success': False, 'error': error_msg}
            
            # Check if content already exists
            content_id = content_data['id']
            if self.check_exists(content_id):
                self.stats['skipped'] += 1
                print(f"  ⏭ Skipped (exists): {content_id} - {content_data['title']}")
                return {'success': True, 'skipped': True, 'content_id': content_id}
            
            # Save to database
            success = self.save_to_database(content_data)
            
            if success:
                self.stats['processed'] += 1
                print(f"  ✓ Created: {content_id} - {content_data['title']}")
                return {'success': True, 'content_id': content_id}
            else:
                error_msg = f"Failed to save {content_id} to database"
                self.stats['errors'] += 1
                self.stats['errors_list'].append(error_msg)
                print(f"  ✗ {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            self.stats['errors'] += 1
            self.stats['errors_list'].append(error_msg)
            print(f"  ✗ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def check_exists(self, content_id: str) -> bool:
        """Check if content already exists in database"""
        try:
            result = self.content_service.get_content_by_id(content_id)
            return result['success']
        except Exception as e:
            logger.error(f"Error checking if content exists: {e}")
            return False
    
    def save_to_database(self, content_data: Dict[str, Any]) -> bool:
        """Save content data to database"""
        try:
            # Create ContentCreate model
            content_create = ContentCreate(**content_data)
            
            # Save using content service
            result = self.content_service.create_content(content_create)
            
            return result['success']
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return False
    
    def print_summary(self):
        """Print ingestion summary"""
        print("\n" + "=" * 60)
        print("INGESTION SUMMARY")
        print("=" * 60)
        print(f"Processed: {self.stats['processed']}")
        print(f"Skipped (existing): {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['errors'] > 0:
            print("\nErrors:")
            for error in self.stats['errors_list']:
                print(f"  - {error}")
        
        total = self.stats['processed'] + self.stats['skipped'] + self.stats['errors']
        print(f"\nTotal files: {total}")
        
        if self.stats['processed'] > 0:
            print(f"Success rate: {(self.stats['processed'] / total) * 100:.1f}%")

def main():
    """Main function to run FastFact ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest FastFact files into the database")
    parser.add_argument('input_folder', help='Path to folder containing MHTML files')
    
    args = parser.parse_args()
    
    # Initialize ingestion
    ingestion = FastFactIngestion()
    
    # Process the folder
    stats = ingestion.process_folder(args.input_folder)
    
    # Exit with error code if there were errors
    if stats['errors'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
