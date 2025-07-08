"""
Configuration settings for the AI Search Engine application.
"""
import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).parent.parent

# Database configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'data' / 'database' / 'UD_database.db'))

# Data directories
DATA_DIR = BASE_DIR / 'data'
FAST_FACTS_RAW_DIR = DATA_DIR / 'fast_facts_raw'
UD_CONTENT_RAW_DIR = DATA_DIR / 'ud_content_raw'
PROCESSED_DIR = DATA_DIR / 'processed'

# Application settings
APP_NAME = "AI Search Engine"
APP_VERSION = "1.0.0"

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Agent configurations
AGENT_CONFIGS = {
    "fast_fact": {
        "api_key": "app-jcc5LOnWH0cIf4TIHFq4IU5l",  # FastFact Dify API key
        "base_url": "http://localhost",  # FastFact Dify base URL
        "model": "gpt-4o",
        "active": True,  # Toggle this on/off
        "required_inputs": {
            "question": {"type": "string"},
            "FF_articles": {"type": "string"}
        }
    },
    "ud": {
        "api_key": "app-5UVXvE1G6wiZBZ3v0MACCfbj",  # UD Dify API key
        "base_url": "http://localhost:5001",  # UD Dify base URL
        "model": "claude-3-5-sonnet-20241022",
        "active": False,  # Toggle this on/off
        "required_inputs": {
            "content_title": {"type": "string"},
            "content_summary": {"type": "string"},
            "content_type": {"type": "string"}
        }
    },
    "literature": {
        "api_key": "app-N1mfbmN31JwFFOfEhOnvGjg3",  # Literature Dify API key
        "base_url": "http://localhost:5001",  # Literature Dify base URL
        "model": "gpt-4o",
        "active": False,  # Toggle this on/off
        "required_inputs": {
            "query": {"type": "string"},
            "context": {"type": "string"}
        }
    },

}

# API configuration
API_CONFIG = {
    "title": "AI Search Engine API",
    "description": "API for AI Search Engine application",
    "version": "1.0.0",
    "debug": True
}
