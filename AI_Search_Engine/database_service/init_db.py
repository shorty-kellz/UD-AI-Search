#!/usr/bin/env python3
"""
Database Initialization Script
Run this once to set up the database schema and initial data
"""

import sys
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

# Add the database_service directory to the Python path
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir))

try:
    from table_registry import table_registry
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the AI_Search_Engine directory")
    sys.exit(1)

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

def ensure_database_directory():
    """Ensure the database directory exists"""
    db_dir = DATABASE_PATH.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Database directory ensured: {db_dir}")

def create_tables():
    """Create all necessary tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create all registered tables
        for table_name in table_registry.get_table_names():
            # Check if table already exists
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            ''', (table_name,))
            
            if cursor.fetchone() is None:
                # Table doesn't exist, create it
                schema = table_registry.get_table_schema(table_name)
                if schema:
                    cursor.execute(schema)
                    logger.info(f"Created table: {table_name}")
                
                # Create indexes for the table
                indexes = table_registry.get_table_indexes(table_name)
                for index_sql in indexes:
                    cursor.execute(index_sql)
                    logger.info(f"Created index for {table_name}")
            else:
                # Table already exists, just verify indexes
                logger.info(f"Table {table_name} already exists, verifying indexes")
                indexes = table_registry.get_table_indexes(table_name)
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.info(f"Created/verified index for {table_name}")
                    except Exception as e:
                        # Index might already exist, that's okay
                        logger.debug(f"Index creation skipped (may already exist): {e}")
        
        conn.commit()
        logger.info("All tables and indexes created/verified successfully")

def get_record_count(table_name: str = 'content_master') -> int:
    """Get the number of records in a table"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error getting record count: {e}")
        return 0

def init_database():
    """Initialize the database with all tables and initial data"""
    
    print("=" * 50)
    print("AI Search Engine - Database Initialization")
    print("=" * 50)
    
    try:
        # Ensure database directory exists
        ensure_database_directory()
        
        # Create tables
        create_tables()
        
        # Check if tables exist and get record counts
        tables = table_registry.get_table_names()
        for table_name in tables:
            record_count = get_record_count(table_name)
            print(f"✓ {table_name} table ready ({record_count} records)")
        
        # Test database connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            print(f"✓ SQLite version: {version}")
        
        print(f"✓ Database ready at: {DATABASE_PATH}")
        
        print("\n🎉 Database initialization complete!")
        print("\nNext steps:")
        print("1. Run your content ingestion pipeline to populate the database")
        print("2. Use DB Browser for SQLite to view the data")
        print("3. Start building your FastAPI backend")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
