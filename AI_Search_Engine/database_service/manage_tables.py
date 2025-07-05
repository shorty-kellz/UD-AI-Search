#!/usr/bin/env python3
"""
Table Management CLI Tool
Provides simple commands to manage database tables during development
"""

import sys
import argparse
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

# Add the database_service directory to the Python path
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir))

from table_registry import table_registry

# Database configuration
DATABASE_PATH = Path(__file__).parent.parent / 'data' / 'database' / 'UD_database.db'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            ''', (table_name,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking table existence: {e}")
        return False

def create_table(table_name: str) -> bool:
    """Create a specific table"""
    if not table_registry.table_exists(table_name):
        print(f"❌ Table '{table_name}' not found in registry")
        return False
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table already exists
            if table_exists(table_name):
                print(f"⚠️  Table '{table_name}' already exists")
                return True
            
            # Create the table
            schema = table_registry.get_table_schema(table_name)
            cursor.execute(schema)
            
            # Create indexes
            indexes = table_registry.get_table_indexes(table_name)
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            print(f"✅ Created table: {table_name}")
            return True
            
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        print(f"❌ Failed to create table: {table_name}")
        return False

def drop_table(table_name: str) -> bool:
    """Drop a specific table (WARNING: This will delete all data)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table exists before dropping
            if table_exists(table_name):
                cursor.execute(f"DROP TABLE {table_name}")
                conn.commit()
                print(f"✅ Dropped table: {table_name}")
                return True
            else:
                print(f"⚠️  Table {table_name} does not exist, nothing to drop")
                return True
                
    except Exception as e:
        logger.error(f"Error dropping table: {e}")
        print(f"❌ Failed to drop table: {table_name}")
        return False

def recreate_table(table_name: str) -> bool:
    """Drop and recreate a specific table (WARNING: This will delete all data)"""
    if not table_registry.table_exists(table_name):
        print(f"❌ Table '{table_name}' not found in registry")
        return False
    
    print(f"⚠️  Recreating table '{table_name}' - this will delete all data!")
    
    # Step 1: Drop the table
    if not drop_table(table_name):
        return False
    
    # Step 2: Verify table is dropped
    if table_exists(table_name):
        print(f"❌ Failed to drop table '{table_name}'")
        return False
    
    # Step 3: Create the new table
    success = create_table(table_name)
    if success:
        print(f"✅ Successfully recreated table '{table_name}'")
    else:
        print(f"❌ Failed to create table '{table_name}'")
    
    return success

def list_tables():
    """List all registered tables"""
    print("=" * 50)
    print("Registered Tables")
    print("=" * 50)
    
    tables = table_registry.list_tables()
    if not tables:
        print("No tables registered")
        return
    
    for table_name, description in tables.items():
        exists_in_db = table_exists(table_name)
        status = "✅" if exists_in_db else "❌"
        print(f"{status} {table_name}: {description}")

def show_table_info(table_name: str):
    """Show detailed information about a specific table"""
    if not table_registry.table_exists(table_name):
        print(f"❌ Table '{table_name}' not found in registry")
        return
    
    print(f"=" * 50)
    print(f"Table: {table_name}")
    print("=" * 50)
    
    # Get table info
    table_info = table_registry.tables[table_name]
    print(f"Description: {table_info['description']}")
    
    # Check if table exists in database
    exists_in_db = table_exists(table_name)
    print(f"Exists in database: {'✅ Yes' if exists_in_db else '❌ No'}")
    
    if exists_in_db:
        # Get record count
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"Record count: {count}")
        except Exception as e:
            print(f"Error getting record count: {e}")
    
    print("\nSchema:")
    print(table_info['schema'].strip())
    
    if table_info['indexes']:
        print("\nIndexes:")
        for index in table_info['indexes']:
            print(f"  {index}")

def init_all_tables():
    """Initialize all registered tables"""
    print("=" * 50)
    print("Initializing All Tables")
    print("=" * 50)
    
    tables = table_registry.get_table_names()
    
    for table_name in tables:
        print(f"Creating table: {table_name}")
        create_table(table_name)
    
    print("✅ All tables initialized")

def main():
    parser = argparse.ArgumentParser(description="Manage database tables")
    parser.add_argument('command', choices=['list', 'info', 'create', 'drop', 'recreate', 'init'], 
                       help='Command to execute')
    parser.add_argument('table_name', nargs='?', help='Table name (required for most commands)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'list':
            list_tables()
        elif args.command == 'info':
            if not args.table_name:
                print("❌ Table name required for 'info' command")
                sys.exit(1)
            show_table_info(args.table_name)
        elif args.command == 'create':
            if not args.table_name:
                print("❌ Table name required for 'create' command")
                sys.exit(1)
            create_table(args.table_name)
        elif args.command == 'drop':
            if not args.table_name:
                print("❌ Table name required for 'drop' command")
                sys.exit(1)
            if not args.force:
                print(f"⚠️  WARNING: This will delete ALL data in table '{args.table_name}'")
                response = input("Are you sure? Type 'yes' to continue: ")
                if response.lower() != 'yes':
                    print("Operation cancelled")
                    return
            drop_table(args.table_name)
        elif args.command == 'recreate':
            if not args.table_name:
                print("❌ Table name required for 'recreate' command")
                sys.exit(1)
            if not args.force:
                print(f"⚠️  WARNING: This will delete ALL data in table '{args.table_name}' and recreate it")
                response = input("Are you sure? Type 'yes' to continue: ")
                if response.lower() != 'yes':
                    print("Operation cancelled")
                    return
            recreate_table(args.table_name)
        elif args.command == 'init':
            init_all_tables()
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
