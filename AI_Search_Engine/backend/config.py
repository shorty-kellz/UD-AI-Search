"""
Simplified configuration settings for the AI Search Engine
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
