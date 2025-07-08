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
from agent_manager import AgentManager

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
agent_manager = AgentManager()

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
    try:
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/content")
async def create_content(content: ContentCreate):
    """Create a new content record"""
    try:
        result = content_service.create_content(content)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    except Exception as e:
        logger.error(f"Create content error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content/{content_id}")
async def get_content(content_id: str):
    """Get content by ID"""
    try:
        result = content_service.get_content_by_id(content_id)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result['data']
    except Exception as e:
        logger.error(f"Get content error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/content")
async def list_content(
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(100, description="Maximum number of records to return")
):
    """List content with optional filtering"""
    try:
        result = content_service.list_content(source=source, limit=limit)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return {
            "data": result['data'],
            "count": result['count']
        }
    except Exception as e:
        logger.error(f"List content error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def process_query(query: str, user: str = "default"):
    """Process a query through all active agents"""
    try:
        logger.info(f"Processing query: {query}")
        
        # Process through all active agents
        result = agent_manager.process_user_query(query, {"question": query}, user)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/status")
async def get_agent_status():
    """Get status of all agents (active/inactive)"""
    try:
        logger.info("Getting agent status...")
        status = agent_manager.get_agent_status()
        logger.info(f"Agent status: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-questions")
async def get_test_questions():
    """Get all test questions from the database"""
    try:
        from database import get_connection
        
        logger.info("Attempting to retrieve test questions from database...")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # First check if the table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_questions'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                logger.warning("test_questions table does not exist in database")
                return []
            
            logger.info("test_questions table found, querying for questions...")
            cursor.execute("SELECT question_id, question_text FROM test_questions ORDER BY question_id")
            questions = cursor.fetchall()
            
            logger.info(f"Found {len(questions)} test questions in database")
            
            return [
                {
                    'question_id': row['question_id'],
                    'question_text': row['question_text']
                }
                for row in questions
            ]
            
    except Exception as e:
        logger.error(f"Error retrieving test questions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-results")
async def save_results(data: dict):
    """Save search results with SME feedback to the database"""
    try:
        from database import get_connection
        
        logger.info("Saving results to database...")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if results table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='results'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                logger.error("results table does not exist in database")
                raise HTTPException(status_code=500, detail="Results table not found")
            
            results_data = data.get('results', [])
            saved_count = 0
            
            for result in results_data:
                cursor.execute('''
                    INSERT INTO results (
                        result_id, question_id, question_text, rank, title, explanation, 
                        tags_matched, url, relevance_score_model, agent_version, 
                        is_relevant_sme, relevance_score_sme, ideal_rank_sme, sme_user_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.get('result_id', ''),
                    result.get('question_id'),
                    result.get('question_text', ''),
                    result.get('rank', 0),
                    result.get('title', ''),
                    result.get('explanation', ''),
                    result.get('tags_matched', ''),
                    result.get('url', ''),
                    result.get('relevance_score_model', 0.0),
                    result.get('agent_version', '1.0'),
                    result.get('is_relevant_sme'),
                    result.get('relevance_score_sme', 0),
                    result.get('ideal_rank_sme', 0),
                    result.get('sme_user_type', 'Nurse')
                ))
                saved_count += 1
            
            conn.commit()
            logger.info(f"Successfully saved {saved_count} results to database")
            
            return {"success": True, "saved_count": saved_count}
            
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    print("Make sure your database and Dify service are running!")
    
    try:
        print("Initializing services...")
        # Test that services initialize properly
        print(f"Content service: {content_service}")
        print(f"Agent manager: {agent_manager}")
        print("Services initialized successfully!")
        
        print("Starting uvicorn server...")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
