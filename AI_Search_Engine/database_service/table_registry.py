"""
Table Registry - Manages table schemas and provides selective table operations
"""

from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TableRegistry:
    """Registry for managing table schemas and operations"""
    
    def __init__(self):
        self.tables = {
            'content_master': {
                'description': 'Main content storage table',
                'schema': '''
                    CREATE TABLE content_master (
                        id TEXT PRIMARY KEY,                   -- e.g., "FF365"
                        title TEXT NOT NULL,                   -- Full title of the article
                        summary TEXT,                          -- Rich summary or description
                        source TEXT,                           -- "Fast Fact", "UD Content", etc.
                        category TEXT,                         -- High-level grouping
                        sub_category TEXT,                     -- Sub-grouping under category
                        tags TEXT,                             -- Stored as JSON array (e.g., '["code status", "goals of care"]')
                        FF_tags TEXT,                          -- FastFact parsed tags from PDF articles
                        auto_category TEXT,                    -- Auto-generated category
                        auto_sub_category TEXT,                -- Auto-generated sub-category
                        auto_tags TEXT,                        -- Auto-generated tags (JSON array)
                        labels_approved BOOLEAN DEFAULT FALSE, -- Whether labels have been approved
                        url TEXT,                              -- Link to external source (if applicable)
                        last_edited DATE,                      -- Timestamp of most recent content edit
                        status TEXT DEFAULT 'active',          -- e.g., "active", "archived"
                        version TEXT DEFAULT '1.0'             -- Manual or programmatic versioning
                    )
                ''',
                'indexes': [
                    'CREATE INDEX IF NOT EXISTS idx_content_master_source ON content_master(source)',
                    'CREATE INDEX IF NOT EXISTS idx_content_master_category ON content_master(category)',
                    'CREATE INDEX IF NOT EXISTS idx_content_master_status ON content_master(status)',
                    'CREATE INDEX IF NOT EXISTS idx_content_master_last_edited ON content_master(last_edited)'
                ]
            },
            'taxonomy_master': {
                'description': 'Taxonomy structure storage table',
                'schema': '''
                    CREATE TABLE taxonomy_master (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        domain TEXT NOT NULL,                  -- Level 1: Domain name
                        category TEXT NOT NULL,                -- Level 2: Category (C1. labels, prefix removed)
                        sub_category TEXT,                     -- Level 3: Sub-category (C2. labels, prefix removed) - can be NULL for C1. items
                        last_edited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active'           -- 'active', 'inactive', 'archived'
                    )
                ''',
                'indexes': [
                    'CREATE INDEX IF NOT EXISTS idx_taxonomy_domain ON taxonomy_master(domain)',
                    'CREATE INDEX IF NOT EXISTS idx_taxonomy_category ON taxonomy_master(category)',
                    'CREATE INDEX IF NOT EXISTS idx_taxonomy_sub_category ON taxonomy_master(sub_category)',
                    'CREATE INDEX IF NOT EXISTS idx_taxonomy_status ON taxonomy_master(status)',
                    'CREATE UNIQUE INDEX IF NOT EXISTS idx_taxonomy_unique ON taxonomy_master(domain, category, sub_category)'
                ]
            },
            # Add more tables here as needed
            # 'users': { ... },
            # 'analytics': { ... },
        }
    
    def get_table_names(self) -> List[str]:
        """Get list of all registered table names"""
        return list(self.tables.keys())
    
    def get_table_schema(self, table_name: str) -> Optional[str]:
        """Get the CREATE TABLE statement for a specific table"""
        if table_name in self.tables:
            return self.tables[table_name]['schema']
        return None
    
    def get_table_indexes(self, table_name: str) -> List[str]:
        """Get the index creation statements for a specific table"""
        if table_name in self.tables:
            return self.tables[table_name]['indexes']
        return []
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table is registered"""
        return table_name in self.tables
    
    def add_table(self, table_name: str, schema: str, indexes: List[str] = None, description: str = ""):
        """Add a new table to the registry"""
        self.tables[table_name] = {
            'description': description,
            'schema': schema,
            'indexes': indexes or []
        }
        logger.info(f"Added table '{table_name}' to registry")
    
    def remove_table(self, table_name: str):
        """Remove a table from the registry"""
        if table_name in self.tables:
            del self.tables[table_name]
            logger.info(f"Removed table '{table_name}' from registry")
    
    def list_tables(self) -> Dict[str, str]:
        """List all tables with their descriptions"""
        return {name: info['description'] for name, info in self.tables.items()}

# Global table registry instance
table_registry = TableRegistry()
