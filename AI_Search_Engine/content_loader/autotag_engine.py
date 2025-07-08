#!/usr/bin/env python3
"""
Auto-Tagging Engine
Batch processor that loops through content_master table and generates auto-tags
using Dify auto-tagging agent, then saves results back to the database.
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import requests

# Database connection (self-contained)
DATABASE_PATH = Path(__file__).parent.parent / 'data' / 'database' / 'UD_database.db'

def get_connection():
    """Simple database connection function"""
    import sqlite3
    from contextlib import contextmanager
    
    @contextmanager
    def _get_connection():
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
    
    return _get_connection()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Auto-tagging agent configuration (self-contained)
AUTO_TAG_CONFIG = {
    "api_key": "app-yqldCBlThEvSpRQ5EW2B46UY",  # Auto Label Dify API key
    "base_url": "http://localhost",  # Auto Label Dify base URL
    "model": "gpt-4o",
    "required_inputs": {
        "content_piece": {"type": "string"},
        "tag_list": {"type": "string"}
    }
}

class DifyHelper:
    """Lightweight helper that reuses orchestrator's Dify communication without agent imports"""
    
    def __init__(self, api_key: str, base_url: str):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.base_url = base_url
        logger.info(f"Initialized DifyHelper with base_url: {self.base_url}")
    
    def send_to_dify(self, inputs: Dict, query: str, user: str = "batch_processor") -> Dict:
        """Send request to Dify and return response - reuses orchestrator's proven logic"""
        try:
            # Capture start timestamp
            start_time = time.time()
            
            # Prepare request data (same as orchestrator)
            request_data = {
                "inputs": inputs,
                "query": query,
                "response_mode": "streaming",
                "user": user
            }
            
            logger.info(f"Sending request to Dify: {json.dumps(request_data, indent=2)}")
            
            # Make request to Dify (same as orchestrator)
            response = requests.post(
                f"{self.base_url}/v1/chat-messages",
                headers=self.headers,
                json=request_data,
                stream=True
            )
            
            logger.info(f"Response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Response body: {response.text}")
                return {
                    'error': f"Dify API error: {response.status_code} - {response.text}",
                    'success': False
                }
            
            # Initialize response tracking variables (same as orchestrator)
            message_id = None
            conversation_id = None
            full_response = ""
            dify_metadata = {
                "message_files": [],
                "feedback": None,
                "retriever_resources": [],
                "agent_thoughts": []
            }
            usage_metrics = None
            first_event_received = False
            
            # Process streaming response (same as orchestrator)
            for line in response.iter_lines():
                if line:
                    try:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            event_type = data.get('event')
                            logger.debug(f"Received event type: {event_type}")
                            
                            # Capture first event timestamp for latency calculation
                            if not first_event_received:
                                end_time = time.time()
                                manual_latency = (end_time - start_time) * 1000  # Convert to milliseconds
                                dify_metadata['manual_latency'] = manual_latency
                                first_event_received = True
                                logger.debug(f"Calculated manual latency: {manual_latency}ms")
                            
                            if event_type == 'agent_message':
                                # Store message_id and conversation_id from any agent_message event
                                if not message_id and data.get('message_id'):
                                    message_id = data.get('message_id')
                                if not conversation_id and data.get('conversation_id'):
                                    conversation_id = data.get('conversation_id')
                            
                            elif event_type == 'agent_thought':
                                # This contains the complete response
                                full_response = data.get('thought', '')
                                # Update metadata
                                dify_metadata['agent_thoughts'].append({
                                    'thought': data.get('thought', ''),
                                    'observation': data.get('observation', ''),
                                    'tool': data.get('tool', ''),
                                    'tool_labels': data.get('tool_labels', {})
                                })
                            
                            elif event_type == 'message_end':
                                # Get usage metrics and override latency with manual calculation
                                usage_metrics = data.get('metadata', {}).get('usage', {})
                                if usage_metrics and first_event_received:
                                    usage_metrics['latency'] = manual_latency
                            
                            elif event_type == 'error':
                                logger.error(f"Received error event: {data.get('message')}")
                                raise Exception(f"Dify error: {data.get('message', 'Unknown error')}")
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error decoding JSON: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing line: {str(e)}")
                        continue
            
            logger.info(f"Final response data:")
            logger.info(f"message_id: {message_id}")
            logger.info(f"conversation_id: {conversation_id}")
            logger.info(f"full_response length: {len(full_response)}")
            
            # Return response in same format as orchestrator
            return {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'response': full_response,
                'dify_metadata': dify_metadata,
                'usage_metrics': usage_metrics,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in DifyHelper.send_to_dify: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }

class AutoTaggingAgent:
    """Auto-tagging agent that communicates with Dify using DifyHelper"""
    
    def __init__(self):
        self.config = AUTO_TAG_CONFIG
        self.dify_helper = DifyHelper(self.config['api_key'], self.config['base_url'])
        logger.info(f"Initialized AutoTaggingAgent with base_url: {self.config['base_url']}")
    
    def get_unique_tags_from_database(self) -> List[str]:
        """Get unique list of tags from both tags and auto_tags columns in content_master"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all tags from both columns
                cursor.execute('''
                    SELECT tags, auto_tags
                    FROM content_master 
                    WHERE tags IS NOT NULL OR auto_tags IS NOT NULL
                ''')
                
                all_tags = set()
                
                for row in cursor.fetchall():
                    # Parse tags column (JSON array)
                    if row['tags']:
                        try:
                            tags_list = json.loads(row['tags'])
                            if isinstance(tags_list, list):
                                # Filter out non-string values and clean tags
                                clean_tags = []
                                for tag in tags_list:
                                    if isinstance(tag, str) and tag.strip():
                                        clean_tag = tag.strip().strip('"\'')
                                        if clean_tag and len(clean_tag) > 1:  # Avoid single characters
                                            clean_tags.append(clean_tag)
                                all_tags.update(clean_tags)
                        except json.JSONDecodeError:
                            # If not JSON, try comma-separated
                            tags_text = row['tags'].strip()
                            if tags_text:
                                tags_list = [tag.strip().strip('"\'') for tag in tags_text.split(',') if tag.strip()]
                                # Filter out garbage text
                                clean_tags = [tag for tag in tags_list if self._is_valid_tag(tag)]
                                all_tags.update(clean_tags)
                    
                    # Parse auto_tags column (JSON array)
                    if row['auto_tags']:
                        try:
                            auto_tags_list = json.loads(row['auto_tags'])
                            if isinstance(auto_tags_list, list):
                                # Filter out non-string values and clean tags
                                clean_tags = []
                                for tag in auto_tags_list:
                                    if isinstance(tag, str) and tag.strip():
                                        clean_tag = tag.strip().strip('"\'')
                                        if clean_tag and len(clean_tag) > 1:  # Avoid single characters
                                            clean_tags.append(clean_tag)
                                all_tags.update(clean_tags)
                        except json.JSONDecodeError:
                            # If not JSON, try comma-separated
                            auto_tags_text = row['auto_tags'].strip()
                            if auto_tags_text:
                                auto_tags_list = [tag.strip().strip('"\'') for tag in auto_tags_text.split(',') if tag.strip()]
                                # Filter out garbage text
                                clean_tags = [tag for tag in auto_tags_list if self._is_valid_tag(tag)]
                                all_tags.update(clean_tags)
                
                # Convert to sorted list and apply final filtering
                unique_tags = sorted([tag for tag in all_tags if self._is_valid_tag(tag)])
                
                logger.info(f"Found {len(unique_tags)} unique clean tags in database")
                return unique_tags
                
        except Exception as e:
            logger.error(f"Error getting unique tags from database: {e}")
            return []
    
    def _is_valid_tag(self, tag: str) -> bool:
        """Check if a tag is valid (not garbage text)"""
        if not tag or not isinstance(tag, str):
            return False
        
        tag = tag.strip()
        
        # Must be at least 2 characters
        if len(tag) < 2:
            return False
        
        # Must not be just punctuation or symbols
        if tag in [':', '[', ']', '{', '}', '(', ')', ',', '.', '?', '!']:
            return False
        
        # Must not contain obvious garbage patterns
        garbage_patterns = [
            'you want me to',
            'for me to',
            'I will need',
            'in order to',
            'list for me',
            'list to',
            'related to this content',
            'you\'d like me to',
            'could you please',
            'please provide',
            'specific content',
            'existing tags',
            ': [',
            'list from which',
            'list so that',
            'perform an analysis'
        ]
        
        tag_lower = tag.lower()
        for pattern in garbage_patterns:
            if pattern in tag_lower:
                return False
        
        # Must not be just a single character or number
        if len(tag) == 1 and not tag.isalpha():
            return False
        
        return True
    
    def prepare_inputs(self, content_data: Dict) -> Dict:
        """Prepare inputs for Dify auto-tagging agent"""
        # Format content_piece as clean text string with ID, Title, and Summary on separate lines
        # Use actual line breaks that will be properly handled in JSON
        content_piece = f"""ID: {content_data.get('id', '')}
Title: {content_data.get('title', '')}
Summary: {content_data.get('summary', '')}"""
        
        # Get unique tags from database for context
        unique_tags = self.get_unique_tags_from_database()
        tag_list = "\n".join(unique_tags) if unique_tags else ""
        
        # DEBUG: Log what we're sending to Dify
        logger.info("=" * 60)
        logger.info("DEBUG: INPUTS BEING SENT TO DIFY")
        logger.info("=" * 60)
        logger.info(f"content_piece: {repr(content_piece)}")
        logger.info(f"tag_list: {repr(tag_list)}")
        logger.info("=" * 60)
        
        return {
            "content_piece": content_piece,
            "tag_list": tag_list
        }
    
    def get_dify_query(self, query: str) -> str:
        """Get the query text to send to Dify"""
        return "please return tags for this content"
    
    def parse_response(self, raw_response: Dict) -> Dict:
        """Parse the response from Dify and extract auto-tags"""
        try:
            response_text = raw_response.get('response', '')
            
            # DEBUG: Log the raw response to understand the format
            logger.info("=" * 60)
            logger.info("DEBUG: RAW DIFY RESPONSE")
            logger.info("=" * 60)
            logger.info(f"Response text: {repr(response_text)}")
            logger.info(f"Response length: {len(response_text)}")
            logger.info("=" * 60)
            
            # First, try to parse as JSON directly
            try:
                response_json = json.loads(response_text)
                logger.info(f"Successfully parsed as JSON: {response_json}")
                
                # Look for recommended_tags in the JSON response
                if isinstance(response_json, dict):
                    recommended_tags = response_json.get('recommended_tags', [])
                    if isinstance(recommended_tags, list):
                        # Filter and clean the tags
                        clean_tags = []
                        for tag in recommended_tags:
                            if isinstance(tag, str) and tag.strip():
                                clean_tag = tag.strip()
                                if self._is_valid_tag(clean_tag):
                                    clean_tags.append(clean_tag)
                        
                        logger.info(f"Extracted {len(clean_tags)} valid tags from JSON: {clean_tags}")
                        return {
                            'success': True,
                            'auto_tags': clean_tags,
                            'raw_response': response_text
                        }
            except json.JSONDecodeError:
                logger.info("Response is not valid JSON, trying regex patterns")
                pass
            
            # Fallback: try to extract tags from plain text using regex
            import re
            
            # Look for JSON array patterns in the text
            json_array_pattern = r'\[([^\]]*)\]'
            array_matches = re.findall(json_array_pattern, response_text)
            
            for match in array_matches:
                if match.strip():
                    # Try to parse the array content
                    try:
                        # Clean up the match and try to parse as JSON array
                        clean_match = match.strip()
                        if clean_match.startswith('"') or clean_match.startswith("'"):
                            # It's already a JSON array string
                            tags_array = json.loads(f"[{clean_match}]")
                        else:
                            # Split by comma and clean up
                            tags_text = clean_match
                            tags_list = [tag.strip().strip('"\'') for tag in tags_text.split(',') if tag.strip()]
                            tags_array = [tag for tag in tags_list if self._is_valid_tag(tag)]
                        
                        if tags_array:
                            logger.info(f"Extracted tags from array pattern: {tags_array}")
                            return {
                                'success': True,
                                'auto_tags': tags_array,
                                'raw_response': response_text
                            }
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            # Final fallback: look for comma-separated tags
            tag_patterns = [
                r'recommended_tags?[:\s]*\[([^\]]*)\]',  # "recommended_tags: [tag1, tag2]"
                r'tags?[:\s]*\[([^\]]*)\]',  # "tags: [tag1, tag2]"
                r'auto[-_]?tags?[:\s]*\[([^\]]*)\]',  # "auto-tags: [tag1, tag2]"
                r'recommended_tags?[:\s]*([^.\n]+)',  # "recommended_tags: tag1, tag2, tag3"
                r'tags?[:\s]*([^.\n]+)',  # "tags: tag1, tag2, tag3"
                r'auto[-_]?tags?[:\s]*([^.\n]+)',  # "auto-tags: tag1, tag2, tag3"
            ]
            
            for i, pattern in enumerate(tag_patterns):
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                logger.info(f"Pattern {i+1} matches: {matches}")
                if matches:
                    # Split by comma and clean up
                    tags_text = matches[0].strip()
                    auto_tags = [tag.strip().strip('"\'') for tag in tags_text.split(',') if tag.strip()]
                    # Filter out invalid tags
                    valid_tags = [tag for tag in auto_tags if self._is_valid_tag(tag)]
                    logger.info(f"Extracted tags from pattern {i+1}: {valid_tags}")
                    if valid_tags:
                        return {
                            'success': True,
                            'auto_tags': valid_tags,
                            'raw_response': response_text
                        }
            
            # If no tags found, return empty result
            logger.warning("No tags could be extracted from response")
            return {
                'success': True,  # Still success, just no tags
                'auto_tags': [],
                'raw_response': response_text
            }
            
        except Exception as e:
            logger.error(f"Error parsing auto-tagging response: {e}")
            return {
                'success': False,
                'auto_tags': [],
                'raw_response': raw_response.get('response', ''),
                'error': str(e)
            }

class AutoTaggingEngine:
    """Main auto-tagging batch processor"""
    
    def __init__(self):
        self.agent = AutoTaggingAgent()
        logger.info("Initialized AutoTaggingEngine")
    
    def get_content_to_process(self) -> List[Dict]:
        """Get all content from content_master table that needs auto-tagging"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                # Get content that either has no auto_tags or empty auto_tags
                cursor.execute('''
                    SELECT id, title, summary
                    FROM content_master 
                    WHERE auto_tags IS NULL OR auto_tags = '' OR auto_tags = '[]'
                    ORDER BY id
                ''')
                
                content = []
                for row in cursor.fetchall():
                    content.append({
                        'id': row['id'],
                        'title': row['title'],
                        'summary': row['summary']
                    })
                
                logger.info(f"Found {len(content)} content items to process")
                return content
                
        except Exception as e:
            logger.error(f"Error getting content to process: {e}")
            return []
    
    def update_content_auto_tags(self, content_id: str, auto_tags: List[str]) -> bool:
        """Update content_master table with new auto-tags"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert auto_tags list to JSON string
                auto_tags_json = json.dumps(auto_tags)
                
                cursor.execute('''
                    UPDATE content_master 
                    SET auto_tags = ?, last_edited = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (auto_tags_json, content_id))
                
                conn.commit()
                logger.info(f"Updated auto_tags for content {content_id}: {auto_tags}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating auto_tags for content {content_id}: {e}")
            return False
    
    def process_content_item(self, content: Dict) -> Dict:
        """Process a single content item and generate auto-tags"""
        try:
            logger.info(f"Processing content: {content['id']} - {content['title'][:50]}...")
            
            # Prepare content data for the agent
            content_data = {
                'id': content['id'],
                'title': content['title'],
                'summary': content['summary']
            }
            
            # Use DifyHelper to communicate with Dify (reuses orchestrator's proven logic)
            inputs = self.agent.prepare_inputs(content_data)
            query = self.agent.get_dify_query("Generate auto-tags for this content")
            
            # Send to Dify using the helper
            dify_response = self.agent.dify_helper.send_to_dify(inputs, query)
            
            if not dify_response.get('success', False):
                return {
                    'success': False,
                    'content_id': content['id'],
                    'error': dify_response.get('error', 'Unknown Dify error')
                }
            
            # Get the response data
            full_response = dify_response.get('response', '')
            
            # Parse the response using our agent's parse_response method
            parsed_result = self.agent.parse_response({
                'response': full_response
            })
            
            if parsed_result.get('success', False):
                auto_tags = parsed_result.get('auto_tags', [])
                
                # Update the database
                if self.update_content_auto_tags(content['id'], auto_tags):
                    return {
                        'success': True,
                        'content_id': content['id'],
                        'auto_tags': auto_tags,
                        'count': len(auto_tags)
                    }
                else:
                    return {
                        'success': False,
                        'content_id': content['id'],
                        'error': 'Failed to update database'
                    }
            else:
                return {
                    'success': False,
                    'content_id': content['id'],
                    'error': parsed_result.get('error', 'Failed to parse auto-tags')
                }
                
        except Exception as e:
            logger.error(f"Error processing content {content['id']}: {e}")
            return {
                'success': False,
                'content_id': content['id'],
                'error': str(e)
            }
    
    def run_batch_processing(self) -> Dict:
        """Run the complete auto-tagging batch process"""
        print("🚀 Starting Auto-Tagging Batch Processing...")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Get content to process
            content_list = self.get_content_to_process()
            
            if not content_list:
                print("✅ No content found that needs auto-tagging")
                return {
                    'success': True,
                    'processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_time': 0
                }
            
            # Process each content item
            successful = 0
            failed = 0
            results = []
            
            for i, content in enumerate(content_list, 1):
                print(f"\n📝 Processing {i}/{len(content_list)}: {content['title'][:60]}...")
                
                result = self.process_content_item(content)
                results.append(result)
                
                if result['success']:
                    successful += 1
                    print(f"✅ Success: Generated {result['count']} auto-tags")
                else:
                    failed += 1
                    print(f"❌ Failed: {result['error']}")
                
                # Small delay to avoid overwhelming the API
                time.sleep(1)
            
            total_time = time.time() - start_time
            
            # Print summary
            print("\n" + "=" * 60)
            print("🎉 AUTO-TAGGING BATCH PROCESSING COMPLETE!")
            print("=" * 60)
            print(f"📊 Total content processed: {len(content_list)}")
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"⏱️ Total time: {total_time:.2f} seconds")
            print(f"📈 Average time per item: {total_time/len(content_list):.2f} seconds")
            
            return {
                'success': True,
                'processed': len(content_list),
                'successful': successful,
                'failed': failed,
                'total_time': total_time,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            print(f"❌ Batch processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def main():
    """Main function to run the auto-tagging batch processor"""
    engine = AutoTaggingEngine()
    result = engine.run_batch_processing()
    
    if result['success']:
        print("\n✅ Auto-tagging batch processing completed successfully!")
    else:
        print(f"\n❌ Auto-tagging batch processing failed: {result['error']}")
    
    return result

if __name__ == "__main__":
    main()
