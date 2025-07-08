#!/usr/bin/env python3
"""
Debug script to test Dify auto-tagging response format
"""

import sys
import json
import logging
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from autotag_engine import AutoTaggingAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dify_response():
    """Test what Dify returns for auto-tagging"""
    
    # Create agent
    agent = AutoTaggingAgent()
    
    # Test content
    test_content = {
        'id': 'test-001',
        'title': 'Test Content Title',
        'summary': 'This is a test summary for debugging the Dify response format.'
    }
    
    print("🚀 Testing Dify Auto-Tagging Response Format")
    print("=" * 60)
    
    try:
        # Prepare inputs
        inputs = agent.prepare_inputs(test_content)
        query = agent.get_dify_query("Generate auto-tags for this content")
        
        print(f"Inputs being sent to Dify:")
        print(json.dumps(inputs, indent=2))
        print(f"Query: {query}")
        print("=" * 60)
        
        # Send to Dify
        dify_response = agent.dify_helper.send_to_dify(inputs, query)
        
        print(f"Dify response success: {dify_response.get('success')}")
        print(f"Raw response from Dify:")
        print("=" * 60)
        print(repr(dify_response.get('response', '')))
        print("=" * 60)
        print(f"Response length: {len(dify_response.get('response', ''))}")
        
        # Try parsing
        parsed_result = agent.parse_response(dify_response)
        
        print(f"Parsed result: {parsed_result}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dify_response() 