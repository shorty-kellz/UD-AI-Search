"""
FastFact Agent for Dify Integration
Handles FastFact-specific queries and responses
"""

import json
import logging
from typing import Dict, List, Any, Optional
from database import get_connection
from config import AGENT_CONFIGS

logger = logging.getLogger(__name__)

class FastFactAgent:
    def __init__(self):
        """Initialize FastFact agent"""
        self.config = AGENT_CONFIGS.get('fast_fact', {})
        
    def get_fast_facts_from_database(self) -> List[Dict[str, Any]]:
        """Query database for all Fast Fact articles and structure them for the prompt"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                # Query all Fast Fact articles
                cursor.execute("""
                    SELECT id, title, summary, url, category, sub_category, tags, FF_tags
                    FROM content_master 
                    WHERE source = 'Fast Fact' AND status = 'active'
                    ORDER BY id
                """)
                
                rows = cursor.fetchall()
                fast_facts = []
                
                for row in rows:
                    # Parse tags and FF_tags from JSON strings
                    tags = []
                    if row['tags']:
                        try:
                            tags = json.loads(row['tags'])
                        except json.JSONDecodeError:
                            tags = []
                    
                    ff_tags = []
                    if row['FF_tags']:
                        try:
                            ff_tags = json.loads(row['FF_tags'])
                        except json.JSONDecodeError:
                            ff_tags = []
                    
                    # Use tags field (not FF_tags)
                    combined_tags = tags
                    
                    fast_fact = {
                        "title": row['title'],
                        "summary": row['summary'] or "",
                        "url": row['url'] or "",
                        "category": row['category'] or "",
                        "sub_category": row['sub_category'] or "",
                        "tags": combined_tags
                    }
                    fast_facts.append(fast_fact)
                
                logger.info(f"Retrieved {len(fast_facts)} Fast Fact articles from database")
                return fast_facts
                
        except Exception as e:
            logger.error(f"Error retrieving Fast Facts from database: {e}")
            return []
    
    def prepare_inputs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare inputs for Dify API - include Fast Facts data in inputs"""
        try:
            # Extract the question from the data
            question = data.get('question', '')
            if not question:
                raise ValueError("Question is required for FastFact queries")
            
            # Get Fast Facts from database
            fast_facts = self.get_fast_facts_from_database()
            
            if not fast_facts:
                raise Exception("No Fast Fact articles found in database")
            
            # Convert fast_facts to readable markdown format
            fast_facts_markdown = self.convert_fast_facts_to_markdown(fast_facts)
            
            # Return the inputs in the format expected by Dify
            # Send as readable markdown instead of JSON string
            return {
                'question': question,
                'FF_articles': fast_facts_markdown
            }
            
        except Exception as e:
            logger.error(f"Error preparing inputs for FastFact agent: {e}")
            raise
    
    def convert_fast_facts_to_markdown(self, fast_facts: List[Dict[str, Any]]) -> str:
        """Convert fast_facts to readable markdown format"""
        markdown_lines = ["Fast Fact Articles:"]
        
        for i, fact in enumerate(fast_facts, 1):
            # Format tags as comma-separated string
            tags_str = ", ".join(fact.get('tags', [])) if fact.get('tags') else "none"
            
            article_text = f"""---
Article {i}:
- title: {fact.get('title', 'N/A')}
- summary: {fact.get('summary', 'N/A')}
- url: {fact.get('url', 'N/A')}
- category: {fact.get('category', 'N/A')}
- sub_category: {fact.get('sub_category', 'N/A')}
- tags: {tags_str}"""
            
            markdown_lines.append(article_text)
        
        # Join all articles with proper spacing
        full_markdown = "\n\n".join(markdown_lines)
        
        logger.info(f"Converted {len(fast_facts)} fast facts to markdown format")
        
        return full_markdown
    
    def get_dify_query(self, original_query: str) -> str:
        """Return the query text that should be sent to Dify"""
        return "Please return results for this question"
    
    def parse_response(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the response from Dify and return structured data"""
        try:
            # Extract the response text
            response_text = raw_response.get('response', '')
            
            # For FastFact agent, the response is the recommendations text
            # We can enhance this later to parse structured data if needed
            
            return {
                'success': True,
                'recommendations': response_text,
                'message_id': raw_response.get('message_id'),
                'conversation_id': raw_response.get('conversation_id'),
                'usage_metrics': raw_response.get('usage_metrics', {}),
                'agent_type': 'fast_fact'
            }
            
        except Exception as e:
            logger.error(f"Error parsing FastFact response: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommendations': '',
                'agent_type': 'fast_fact'
            }
    
    def process_query(self, query: str, data: dict = None) -> dict:
        """Legacy method - now delegates to prepare_inputs for compatibility"""
        try:
            # Use the new interface
            inputs = self.prepare_inputs({'question': query})
            
            return {
                'success': True,
                'inputs': inputs,
                'query': query,
                'agent_type': 'fast_fact'
            }
            
        except Exception as e:
            logger.error(f"Error processing FastFact query: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommendations': []
            } 