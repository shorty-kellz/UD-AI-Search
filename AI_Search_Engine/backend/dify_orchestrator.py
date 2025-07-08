"""
Dify Orchestrator Service
Core functionality:
1. Send messages to Dify
2. Handle streaming responses
3. Save basic chat interactions
4. Return essential response data
"""
import os
import json
import requests
from sseclient import SSEClient
from typing import Dict, AsyncGenerator, Optional, Any, List
from datetime import datetime
import time
import logging
from database import get_connection
from config import AGENT_CONFIGS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DifyOrchestrator:
    def __init__(self, agent_type: str = "fast_fact"):
        """Initialize DifyOrchestrator with configuration and headers"""
        self.conversation_id = None
        self.agent_type = agent_type
        self.config = AGENT_CONFIGS[agent_type]
        self.headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        logger.info(f"Initialized DifyOrchestrator for {agent_type} with base_url: {self.config['base_url']}")

    def get_conversation_id(self) -> Optional[str]:
        """Get current conversation ID"""
        return self.conversation_id

    def set_conversation_id(self, conversation_id: str) -> None:
        """Set conversation ID"""
        self.conversation_id = conversation_id
        logger.info(f"Set conversation_id to: {conversation_id}")

    def process_message_with_agent(
        self,
        agent_type: str,
        query: str,
        data: Dict,
        user: str = "default",
        conversation_id: Optional[str] = None
    ) -> Dict:
        """Process a message through a specific Dify agent"""
        try:
            # Import agent dynamically
            # Handle special case for fast_fact -> FastFactAgent
            if agent_type == "fast_fact":
                class_name = "FastFactAgent"
            else:
                class_name = f'{agent_type.capitalize()}Agent'
            
            agent_module = __import__(f'dify_agents.{agent_type}_agent', fromlist=[class_name])
            agent_class = getattr(agent_module, class_name)
            agent = agent_class()
            
            # Prepare inputs using agent-specific logic
            inputs = agent.prepare_inputs(data)
            
            logger.info(f"Processing message with {agent_type} agent...")
            logger.debug(f"Inputs prepared: {json.dumps(inputs, indent=2)}")

            # Capture start timestamp
            start_time = time.time()

            # Prepare request data
            # Get the query text that should be sent to Dify from the agent
            dify_query = agent.get_dify_query(query)
            request_data = {
                "inputs": inputs,
                "query": dify_query,
                "response_mode": "streaming",
                "user": user,
                "conversation_id": conversation_id
            }

            logger.info(f"Sending request to Dify: {json.dumps(request_data, indent=2)}")
            logger.info(f"FF_articles length: {len(inputs.get('FF_articles', ''))} characters")
            logger.info(f"FF_articles preview: {inputs.get('FF_articles', '')[:500]}...")

            # Make request to Dify
            response = requests.post(
                f"{self.config['base_url']}/v1/chat-messages",
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

            # Initialize response tracking variables
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

            # Process streaming response
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
                                if conversation_id:
                                    self.set_conversation_id(conversation_id)
                            
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

            # Parse response using agent-specific logic
            raw_response = {
                'message_id': message_id,
                'conversation_id': conversation_id,
                'response': full_response,
                'dify_metadata': dify_metadata,
                'usage_metrics': usage_metrics
            }
            
            parsed_response = agent.parse_response(raw_response)
            return parsed_response

        except Exception as e:
            logger.error(f"Error processing message with {agent_type} agent: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }

    def get_agent_types(self) -> List[str]:
        """Get list of available agent types"""
        return ['fast_fact', 'ud', 'literature']

    def validate_agent_type(self, agent_type: str) -> bool:
        """Validate if agent type exists"""
        return agent_type in self.get_agent_types()

    def save_interaction(self, agent_type: str, query: str, response: Dict, user: str = "default") -> bool:
        """Save interaction to database for analytics"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO dify_interactions 
                    (agent_type, query, response, user, timestamp, success, latency)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_type,
                    query,
                    json.dumps(response),
                    user,
                    datetime.now(),
                    response.get('success', True),
                    response.get('usage_metrics', {}).get('latency', 0)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error saving interaction: {str(e)}")
            return False

    def get_interaction_history(self, user: str = "default", limit: int = 50) -> List[Dict]:
        """Get interaction history for a user"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT agent_type, query, response, timestamp, success, latency
                    FROM dify_interactions 
                    WHERE user = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user, limit))
                
                rows = cursor.fetchall()
                history = []
                
                for row in rows:
                    history.append({
                        'agent_type': row[0],
                        'query': row[1],
                        'response': json.loads(row[2]) if row[2] else {},
                        'timestamp': row[3],
                        'success': row[4],
                        'latency': row[5]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting interaction history: {str(e)}")
            return []
