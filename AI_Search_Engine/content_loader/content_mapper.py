"""
Content Mapper - Maps parsed FastFact data to database schema
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

class ContentMapper:
    """Maps parsed FastFact data to content_master table schema"""
    
    def __init__(self):
        pass
    
    def map_fast_fact_to_content(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map parsed FastFact data to content_master table format"""
        
        # Extract Fast Fact number and generate content ID
        fast_fact_number = parsed_data.get('fast_fact_number')
        content_id = self.generate_content_id(fast_fact_number, parsed_data.get('title', ''))
        
        # Set category and sub_category to empty
        category = ''
        sub_category = ''
        
        # Set last_edited to current date only (no time)
        last_edited = datetime.now().date()
        
        # Keep parsed tags as Python list for FF_tags field
        FF_tags = parsed_data.get('tags', [])
        
        # Map to content_master schema
        content_data = {
            'id': content_id,
            'title': parsed_data.get('title', 'Unknown Title'),
            'summary': parsed_data.get('summary', ''),
            'source': 'Fast Fact',
            'category': category,
            'sub_category': sub_category,
            'tags': [],  # Leave empty for now as requested
            'FF_tags': FF_tags,  # Store parsed tags here
            'auto_category': '',  # Initialize as empty
            'auto_sub_category': '',  # Initialize as empty
            'auto_tags': [],  # Initialize as empty list
            'labels_approved': False,  # Initialize as False
            'url': parsed_data.get('url', ''),
            'last_edited': last_edited,
            'status': 'active',
            'version': '1.0'
        }
        
        return content_data
    
    def generate_content_id(self, fast_fact_number: Optional[str], title: str) -> str:
        """Generate content ID from Fast Fact number or title"""
        import re
        
        # First priority: Use extracted fast_fact_number
        if fast_fact_number:
            return fast_fact_number  # Direct mapping - just use the number
        
        # Second priority: Extract from title (look for "FF #XXX" pattern)
        ff_match = re.search(r'FF #(\d+)', title)
        if ff_match:
            return ff_match.group(1)  # Just the number
        
        # Third priority: Look for any number pattern that might be the FF number
        # This is a fallback for cases where the title format is different
        number_match = re.search(r'(\d{1,4})', title)
        if number_match:
            return number_match.group(1)
        
        # Last resort: generate from title hash (but this should rarely happen)
        import hashlib
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        print(f"WARNING: Could not extract FF number for title: '{title}'. Using hash: {title_hash}")
        return title_hash
    
    def validate_content_data(self, content_data: Dict[str, Any]) -> (bool, str):
        """Validate content data before saving to database"""
        required_fields = ['id', 'title', 'source']
        
        for field in required_fields:
            if not content_data.get(field):
                return False, f"Missing required field: {field}"
        
        # Validate ID format (just check it's not empty)
        if not content_data['id']:
            return False, f"Invalid ID: {content_data['id']}"
        
        # Validate FF_tags is a list
        if not isinstance(content_data.get('FF_tags'), list):
            return False, "FF_tags must be a list"
        
        return True, "Valid"
    
    def enrich_content_data(self, content_data: Dict[str, Any], parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add additional metadata to content data"""
        # Add file path for reference
        if parsed_data.get('file_path'):
            content_data['source_file'] = parsed_data['file_path']
        return content_data
