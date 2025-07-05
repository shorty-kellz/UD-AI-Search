"""
Simplified service layer for core content operations
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import date

from database import get_connection
from models import ContentCreate, Content

logger = logging.getLogger(__name__)

class ContentService:
    """Simplified service for content management operations"""
    
    def create_content(self, content_data: ContentCreate) -> Dict[str, Any]:
        """Create a new content record"""
        try:
            # Convert Pydantic model to dict
            data = content_data.model_dump()
            
            # Handle date conversion
            if data.get('last_edited') and isinstance(data['last_edited'], date):
                data['last_edited'] = data['last_edited'].isoformat()
            
            # Convert tags list to JSON string for storage
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
                    data[field] = None  # Use None instead of empty string
            

            
            with get_connection() as conn:
                cursor = conn.cursor()
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
                conn.commit()
            
            return {
                'success': True,
                'message': f"Content '{data['id']}' created successfully",
                'content_id': data['id']
            }
            
        except Exception as e:
            logger.error(f"Error creating content: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_content_by_id(self, content_id: str) -> Dict[str, Any]:
        """Get content by ID"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM content_master WHERE id = ?
                ''', (content_id,))
                row = cursor.fetchone()
                
                if not row:
                    return {
                        'success': False,
                        'error': f"Content with ID '{content_id}' not found"
                    }
                
                # Convert row to dict and handle JSON tags
                content_dict = dict(row)
                if content_dict.get('tags'):
                    try:
                        content_dict['tags'] = json.loads(content_dict['tags'])
                    except:
                        content_dict['tags'] = []
                
                if content_dict.get('FF_tags'):
                    try:
                        content_dict['FF_tags'] = json.loads(content_dict['FF_tags'])
                    except:
                        content_dict['FF_tags'] = []
                
                if content_dict.get('auto_tags'):
                    try:
                        content_dict['auto_tags'] = json.loads(content_dict['auto_tags'])
                    except:
                        content_dict['auto_tags'] = []
                
                return {
                    'success': True,
                    'data': content_dict
                }
                
        except Exception as e:
            logger.error(f"Error getting content: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_content(self, source: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """List content with optional filtering"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                if source:
                    cursor.execute('''
                        SELECT * FROM content_master WHERE source = ? LIMIT ?
                    ''', (source, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM content_master LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                
                # Convert rows to dicts and handle JSON tags
                content_list = []
                for row in rows:
                    content_dict = dict(row)
                    if content_dict.get('tags'):
                        try:
                            content_dict['tags'] = json.loads(content_dict['tags'])
                        except:
                            content_dict['tags'] = []
                    
                    if content_dict.get('FF_tags'):
                        try:
                            content_dict['FF_tags'] = json.loads(content_dict['FF_tags'])
                        except:
                            content_dict['FF_tags'] = []
                    
                    if content_dict.get('auto_tags'):
                        try:
                            content_dict['auto_tags'] = json.loads(content_dict['auto_tags'])
                        except:
                            content_dict['auto_tags'] = []
                    
                    content_list.append(content_dict)
                
                return {
                    'success': True,
                    'data': content_list,
                    'count': len(content_list)
                }
                
        except Exception as e:
            logger.error(f"Error listing content: {e}")
            return {
                'success': False,
                'error': str(e)
            }
