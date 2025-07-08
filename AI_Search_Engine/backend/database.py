"""
Database Connection Management
Provides core database connection functionality without complex CRUD operations
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_PATH = Path(__file__).parent.parent / 'data' / 'database' / 'UD_database.db'

def ensure_database_directory():
    """Ensure the database directory exists"""
    db_dir = DATABASE_PATH.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Database directory ensured: {db_dir}")

@contextmanager
def get_connection():
    """Context manager for database connections"""
    # Ensure database directory exists
    ensure_database_directory()
    
    conn = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
        timeout=30.0
    )
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def test_connection() -> bool:
    """Test database connection and return success status"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            logger.info(f"Database connection successful. SQLite version: {version}")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_database_info() -> dict:
    """Get basic database information"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get SQLite version
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            
            # Get database file size
            file_size = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0
            
            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            return {
                'version': version,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'table_count': table_count,
                'path': str(DATABASE_PATH)
            }
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            'error': str(e),
            'path': str(DATABASE_PATH)
        }


