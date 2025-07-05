"""
Minimal FastAPI application for AI Search Engine backend
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging

from services import ContentService
from models import ContentCreate, Content
from config import APP_NAME, APP_VERSION

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    description="Minimal API for AI Search Engine content management",
    version=APP_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
content_service = ContentService()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": APP_NAME,
        "version": APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/content")
async def create_content(content: ContentCreate):
    """Create a new content record"""
    result = content_service.create_content(content)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result

@app.get("/content/{content_id}")
async def get_content(content_id: str):
    """Get content by ID"""
    result = content_service.get_content_by_id(content_id)
    
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result['data']

@app.get("/content")
async def list_content(
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(100, description="Maximum number of records to return")
):
    """List content with optional filtering"""
    result = content_service.list_content(source=source, limit=limit)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return {
        "data": result['data'],
        "count": result['count']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
