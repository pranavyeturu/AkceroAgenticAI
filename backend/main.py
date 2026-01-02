from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional, Any
import shutil
import mimetypes
from pathlib import Path
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os
from models.database import get_db, Conversation, AgentExecution
from agents.enhanced_orchestrator import EnhancedGeminiOrchestrator
from sqlalchemy.orm import Session
import psutil
import time
import uvicorn
from fastapi.staticfiles import StaticFiles

from models.database import get_db, Conversation, AgentExecution, ChatSession

from agents.brief_synthesizer.router import router as brief_router
from agents.ad_variation.router import router as ads_router
from agents.smart_invoice.router import router as invoice_router


# File upload configuration
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {
    'text': ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'],
    'documents': ['.pdf', '.doc', '.docx'],
    'data': ['.csv', '.json', '.xlsx', '.xls'],
    'images': ['.png', '.jpg', '.jpeg', '.gif']
}
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Multi-Agent Platform",
    description="Collaborative Multi-Agent System for Task Specialization",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000",
                   "http://localhost:5173", "http://frontend:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the orchestrator
orchestrator = EnhancedGeminiOrchestrator()

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(brief_router) 
app.include_router(ads_router)
app.include_router(invoice_router)

def get_file_type(filename: str) -> str:
    """Determine file type category"""
    ext = Path(filename).suffix.lower()
    for category, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return category
    return 'unknown'

def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    if file.size > MAX_FILE_SIZE:
        return False, f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
    
    ext = Path(file.filename).suffix.lower()
    all_allowed = []
    for extensions in ALLOWED_EXTENSIONS.values():
        all_allowed.extend(extensions)
    
    if ext not in all_allowed:
        return False, f"File type {ext} not supported"
    
    return True, "Valid"

async def process_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """Process uploaded file and extract content"""
    try:
        content = await file.read()
        file.file.seek(0)  # Reset file pointer
        
        try:
            text_content = content.decode('utf-8')
            return text_content[:5000], "text"  # Limit content for processing
        except UnicodeDecodeError:
            return f"Binary file: {file.filename} ({len(content)} bytes)", "binary"
    except Exception as e:
        return f"Error processing file: {str(e)}", "error"
    
# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    agent_used: str
    success: bool
    session_id: str
    message_id: str  # Add this line
    metadata: Dict[str, Any]
    timestamp: datetime  # Add this line

# ----- NEW MODELS -----
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    content_preview: str
    file_type: str

class ChatHistoryResponse(BaseModel):
    sessions: List[Dict[str, Any]]
    total_sessions: int

class SessionResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    message_count: int

@app.get("/api/health")
async def api_health():
    return {"status": "healthy", "database": "connected", "redis": "connected"}

@app.get("/")
async def root():
    return {"message": "Multi-Agent Platform API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "connected", "redis": "connected"}

@app.get("/agents")
async def list_agents():
    """Get list of available agents and their capabilities"""
    status = orchestrator.get_agent_status()
    return status

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agents(request: ChatRequest, db: Session = Depends(get_db)):
    """Main chat endpoint - processes user messages through the agent system"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process the request through the orchestrator
        result = orchestrator.process_request(request.message, session_id)
        
        # Determine which agent was used
        agents_used = result.get("metadata", {}).get("agents_consulted", ["orchestrator"])
        primary_agent = agents_used[0] if agents_used else "orchestrator"
        
        # Store conversation in database
        conversation = Conversation(
            session_id=session_id,
            user_message=request.message,
            agent_response=result.get("final_response", "No response generated"),
            agent_used=primary_agent,
            extra_data=result.get("metadata", {})
        )
        db.add(conversation)
        db.commit()
        
        # Store agent execution details
        for i, agent_name in enumerate(agents_used):
            execution = AgentExecution(
                conversation_id=conversation.id,
                agent_name=agent_name,
                input_data={"message": request.message},
                output_data=result.get("agent_responses", [{}])[i] if i < len(result.get("agent_responses", [])) else {},
                execution_time=0,  # Could be measured in production
                status="success" if result.get("success") else "error"
            )
            db.add(execution)
        
        db.commit()
        
        return ChatResponse(
            response=result.get("final_response", "I couldn't process your request."),
            agent_used=primary_agent,
            success=result.get("success", False),
            session_id=session_id,
            metadata=result.get("metadata", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/conversations/{session_id}")
async def get_conversation_history(session_id: str, db: Session = Depends(get_db)):
    """Get conversation history for a session"""
    conversations = db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).order_by(Conversation.created_at).all()
    
    return {
        "session_id": session_id,
        "conversations": [
            {
                "id": conv.id,
                "user_message": conv.user_message,
                "agent_response": conv.agent_response,
                "agent_used": conv.agent_used,
                "created_at": conv.created_at,
                "metadata": conv.extra_data
            }
            for conv in conversations
        ]
    }

@app.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get system analytics and usage statistics"""
    
    # Get agent usage statistics
    agent_usage = db.query(
        AgentExecution.agent_name,
        db.func.count(AgentExecution.id).label("usage_count")
    ).group_by(AgentExecution.agent_name).all()
    
    # Get total conversations
    total_conversations = db.query(Conversation).count()
    
    # Get success rate
    successful_executions = db.query(AgentExecution).filter(
        AgentExecution.status == "success"
    ).count()
    total_executions = db.query(AgentExecution).count()
    success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 100
    # success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
    
    return {
        "total_conversations": total_conversations,
        "total_executions": total_executions,
        "success_rate": round(success_rate, 2),
        "agent_usage": {usage.agent_name: usage.usage_count for usage in agent_usage},
        "system_status": "operational"
    }

@app.get("/system/status")
async def get_system_status():
    """Comprehensive system status for monitoring"""
    
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    return {
        "timestamp": time.time(),
        "system_health": {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "available_memory_gb": round(memory.available / (1024**3), 2)
        },
        "agents_status": orchestrator.get_agent_status(),
        "api_endpoints": {
            "health": " Active",
            "chat": " Active", 
            "agents": " Active",
            "analytics": " Active"
        },
        "features": {
            "multi_agent_routing": " Enabled",
            "database_logging": " Enabled",
            "real_time_processing": " Enabled",
            "fallback_responses": " Enabled"
        }
    }
@app.get("/demo/examples")
async def get_demo_examples():
    """Provide demo examples for different agent types"""
    return {
        "nlp_examples": [
            {
                "query": "Analyze the sentiment of this text: 'I absolutely love this new product! It exceeded all my expectations.'",
                "description": "Sentiment analysis with positive indicators"
            },
            {
                "query": "Summarize this text: 'Artificial intelligence has revolutionized many industries. From healthcare to finance, AI systems are improving efficiency and accuracy. Machine learning algorithms can process vast amounts of data and identify patterns that humans might miss.'",
                "description": "Text summarization example"
            },
            {
                "query": "What are the main themes in this feedback: 'The user interface is intuitive, but the loading times are frustratingly slow. Customer support was helpful though.'",
                "description": "Theme extraction from mixed feedback"
            }
        ],
        "code_examples": [
            {
                "query": "Write a Python function to calculate the factorial of a number",
                "description": "Algorithm implementation with documentation"
            },
            {
                "query": "Create a function to find the greatest common divisor of two numbers efficiently",
                "description": "Optimized algorithm with mathematical explanation"
            },
            {
                "query": "Help me write a Python script to read a CSV file and calculate basic statistics",
                "description": "Data processing with pandas"
            }
        ],
        "data_examples": [
            {
                "query": "How do I perform exploratory data analysis on a sales dataset?",
                "description": "Complete EDA workflow guidance"
            },
            {
                "query": "What's the best way to visualize the correlation between multiple variables?",
                "description": "Data visualization recommendations"
            },
            {
                "query": "Help me understand how to handle missing values in my dataset",
                "description": "Data cleaning strategies"
            }
        ]
    }

@app.post("/demo/quick-test")
async def quick_demo_test():
    """Quick demo showcasing all three agents"""
    demo_results = []
    
    # Test NLP Agent
    nlp_result = orchestrator.process_request(
        "Analyze sentiment: 'This AI platform is incredible!'", 
        "demo-session"
    )
    demo_results.append({
        "agent": "NLP Agent",
        "task": "Sentiment Analysis",
        "input": "This AI platform is incredible!",
        "output": nlp_result.get("final_response", "")[:200] + "..."
    })
    
    # Test Code Agent  
    code_result = orchestrator.process_request(
        "Write a Python function to add two numbers",
        "demo-session"
    )
    demo_results.append({
        "agent": "Code Agent", 
        "task": "Function Generation",
        "input": "Write a Python function to add two numbers",
        "output": "Generated complete Python function with documentation and examples"
    })
    
    # Test Data Agent
    data_result = orchestrator.process_request(
        "Help with data analysis workflow",
        "demo-session"
    )
    demo_results.append({
        "agent": "Data Agent",
        "task": "Analysis Guidance", 
        "input": "Help with data analysis workflow",
        "output": "Provided comprehensive data science workflow and code examples"
    })
    
    return {
        "demo_timestamp": "2024-12-26",
        "system_status": "All agents operational",
        "results": demo_results,
        "capabilities_demonstrated": [
            "Multi-agent routing", 
            "Natural language processing",
            "Code generation with documentation",
            "Data science guidance",
            "Intelligent fallback responses"
        ]
    }

# ----- NEW -----
@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload and process file for analysis"""
    
    # Validate file
    is_valid, message = validate_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process file content
        file.file.seek(0)
        content, content_type = await process_uploaded_file(file)
        
        # Get file info
        file_type = get_file_type(file.filename)
        file_size = file_path.stat().st_size
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size=file_size,
            content_preview=content[:500] + "..." if len(content) > 500 else content,
            file_type=file_type
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/api/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get chat session history"""
    
    # Get sessions with message counts
    sessions_query = db.query(ChatSession).order_by(ChatSession.updated_at.desc())
    total_sessions = sessions_query.count()
    sessions = sessions_query.offset(offset).limit(limit).all()
    
    session_data = []
    for session in sessions:
        message_count = db.query(Conversation).filter(
            Conversation.session_id == session.session_id
        ).count()
        
        last_message = db.query(Conversation).filter(
            Conversation.session_id == session.session_id
        ).order_by(Conversation.created_at.desc()).first()
        
        session_data.append({
            "session_id": session.session_id,
            "title": session.title,
            "message_count": message_count,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "last_message_preview": last_message.user_message[:100] + "..." if last_message and len(last_message.user_message) > 100 else last_message.user_message if last_message else None
        })
    
    return ChatHistoryResponse(
        sessions=session_data,
        total_sessions=total_sessions
    )

@app.get("/api/chat/session/{session_id}", response_model=SessionResponse)
async def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Get all messages for a specific session"""
    
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    conversations = db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).order_by(Conversation.created_at).all()
    
    messages = []
    for conv in conversations:
        messages.extend([
            {
                "id": f"{conv.id}_user",
                "type": "user",
                "content": conv.user_message,
                "timestamp": conv.created_at,
                "metadata": conv.extra_data
            },
            {
                "id": f"{conv.id}_agent",
                "type": "agent",
                "content": conv.agent_response,
                "agent_used": conv.agent_used,
                "timestamp": conv.created_at,
                "metadata": conv.extra_data
            }
        ])
    
    return SessionResponse(
        session_id=session_id,
        messages=messages,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(conversations)
    )

@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a chat session and all its messages"""
    
    # First, delete agent_executions that reference conversations in this session
    conversations = db.query(Conversation).filter(Conversation.session_id == session_id).all()
    conversation_ids = [conv.id for conv in conversations]
    
    if conversation_ids:
        db.query(AgentExecution).filter(AgentExecution.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
    
    # Then delete conversations
    db.query(Conversation).filter(Conversation.session_id == session_id).delete()
    
    # Finally delete session
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if session:
        db.delete(session)
    
    db.commit()
    
    return {"message": "Session deleted successfully"}

@app.get("/api/agents/status")
async def get_real_time_agent_status():
    """Get real-time agent processing status"""
    return orchestrator.get_agent_status()

# MODIFY YOUR EXISTING /chat ENDPOINT
# Find your existing @app.post("/chat", response_model=ChatResponse) function
# Replace it with this enhanced version:

@app.post("/api/chat", response_model=ChatResponse)  # Note: added /api prefix
async def chat_with_agents(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    file_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Enhanced chat endpoint with file support"""
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Generate message ID
        message_id = str(uuid.uuid4())
        
        # Handle file content if provided
        file_content = None
        file_name = None
        
        if file_id:
            # Find uploaded file
            for file_path in UPLOAD_DIR.glob(f"{file_id}_*"):
                file_name = file_path.name.split("_", 1)[1]
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                except UnicodeDecodeError:
                    file_content = f"Binary file: {file_name}"
                break
        
        # Process the request through the orchestrator
        result = orchestrator.process_request(
            user_input=message,
            session_id=session_id,
            file_content=file_content,
            file_name=file_name
        )
        
        # Determine which agent was used
        agents_used = result.get("metadata", {}).get("agents_consulted", ["orchestrator"])
        primary_agent = agents_used[0] if agents_used else "orchestrator"
        
        # Ensure session exists
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            session = ChatSession(
                session_id=session_id,
                title=message[:50] + "..." if len(message) > 50 else message,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(session)
            db.flush()
        else:
            session.updated_at = datetime.now()
        
        # Store conversation in database
        conversation = Conversation(
            session_id=session_id,
            message_id=message_id,
            user_message=message,
            agent_response=result.get("final_response", "No response generated"),
            agent_used=primary_agent,
            extra_data={
                **result.get("metadata", {}),
                "file_attached": file_content is not None,
                "file_name": file_name
            }
        )
        db.add(conversation)
        db.commit()
        
        # Store agent execution details
        for i, agent_name in enumerate(agents_used):
            execution = AgentExecution(
                conversation_id=conversation.id,
                agent_name=agent_name,
                input_data={"message": message, "file_attached": file_content is not None},
                output_data=result.get("agent_responses", [{}])[i] if i < len(result.get("agent_responses", [])) else {},
                execution_time=0,  # You can add timing later
                status="success" if result.get("success") else "error"
            )
            db.add(execution)
        
        db.commit()
        
        return ChatResponse(
            response=result.get("final_response", "I couldn't process your request."),
            agent_used=primary_agent,
            success=result.get("success", False),
            session_id=session_id,
            message_id=message_id,
            metadata=result.get("metadata", {}),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

