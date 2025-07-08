"""
Agent Manager - Coordinates running multiple active agents
Core functionality:
1. Get list of active agents from config
2. Process user queries through all active agents
3. Return combined results from all agents
"""
import logging
from typing import Dict, List, Any
from dify_orchestrator import DifyOrchestrator
from config import AGENT_CONFIGS

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        """Initialize AgentManager"""
        self.orchestrator = DifyOrchestrator()
        logger.info("Initialized AgentManager")
    
    def get_active_agents(self) -> List[str]:
        """Get list of agents with active=True"""
        active_agents = []
        for agent_name, config in AGENT_CONFIGS.items():
            if config.get('active', False):
                active_agents.append(agent_name)
        
        logger.info(f"Found {len(active_agents)} active agents: {active_agents}")
        return active_agents
    
    def process_user_query(self, query: str, data: Dict, user: str = "default") -> Dict:
        """Process query through ALL active agents"""
        active_agents = self.get_active_agents()
        
        if not active_agents:
            logger.warning("No active agents found in configuration")
            return {
                'query': query,
                'active_agents': [],
                'results': {},
                'error': 'No active agents configured'
            }
        
        results = {}
        logger.info(f"Processing query through {len(active_agents)} active agents")
        
        for agent_type in active_agents:
            try:
                logger.info(f"Processing with {agent_type} agent...")
                
                # Create orchestrator for this specific agent
                orchestrator = DifyOrchestrator(agent_type)
                
                # Process with this agent
                result = orchestrator.process_message_with_agent(
                    agent_type, query, data, user
                )
                
                results[agent_type] = result
                logger.info(f"Completed {agent_type} agent processing")
                
            except Exception as e:
                logger.error(f"Error processing with {agent_type} agent: {str(e)}")
                results[agent_type] = {
                    'error': str(e), 
                    'success': False,
                    'agent_type': agent_type
                }
        
        return {
            'query': query,
            'active_agents': active_agents,
            'results': results,
            'total_agents': len(active_agents)
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents (active/inactive)"""
        status = {}
        for agent_name, config in AGENT_CONFIGS.items():
            status[agent_name] = {
                'active': config.get('active', False),
                'model': config.get('model', 'unknown'),
                'base_url': config.get('base_url', 'unknown')
            }
        return status 