# Docker Development Environment

This directory contains the Docker setup for the AI Search Engine development environment with SQLite.

## Quick Start

### 1. Start the development container
```bash
cd AI_Search_Engine/deploy
docker-compose up -d
```

### 2. Access the container shell
```bash
docker-compose exec sqlite-dev bash
```

### 3. Verify the setup
```bash
# Check if SQLite is working
sqlite3 /app/data/database/UD_database.db ".tables"

# Check if Python packages are installed
python -c "import sqlite3, bs4, html2text; print('All packages installed!')"
```

## Development Workflow

1. **Start the container**: `docker-compose up -d`
2. **Access shell**: `docker-compose exec sqlite-dev bash`
3. **Run your code**: `python backend/main.py` (or other scripts as needed)
4. **Stop container**: `docker-compose down`

## Volume Mounts

The following directories are mounted for development:
- `./data` → `/app/data` (persistent data storage)
- `./backend` → `/app/backend` (backend code)
- `./frontend` → `/app/frontend` (frontend code)
- `./deploy` → `/app/deploy` (deploy scripts)

## Environment Variables

- `DATABASE_PATH`: Path to SQLite database file
- `PYTHONPATH`: Python path for imports

## Database Location

The SQLite database is automatically created at:
`/app/data/database/UD_database.db`

## Database Schema

The `content_master` table is created with the following structure:
- `id` (INTEGER PRIMARY KEY)
- `title` (TEXT)
- `summary` (TEXT)
- `tags` (TEXT)
- `url` (TEXT)
- `content_type` (TEXT)
- `source_file` (TEXT)
- `created_at` (TIMESTAMP)

## Troubleshooting

If you encounter issues:

1. **Rebuild container**: `docker-compose down && docker-compose up -d`
2. **Check logs**: `docker-compose logs sqlite-dev`
3. **Reset everything**: `docker-compose down -v && docker-compose up -d` 