from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent_user:agent_password@postgres:5432/agent_platform")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), index=True)  # Only keep this one
    message_id = Column(String, unique=True, index=True)
    user_message = Column(Text)
    agent_response = Column(Text)
    agent_used = Column(String)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="conversations")

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))  # Keep only this one
    agent_name = Column(String)
    input_data = Column(JSON)
    output_data = Column(JSON)
    execution_time = Column(Integer)  # milliseconds
    status = Column(String)  # success, error, timeout
    error_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Add this relationship
    conversation = relationship("Conversation")
    
# New models
class ChatSession(Base):
    """Model for chat sessions - enables chat history management"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False)
    
    # Relationship to conversations
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")

class FileUpload(Base):
    """Track uploaded files"""
    __tablename__ = "file_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, unique=True, index=True)
    original_filename = Column(String)
    stored_filename = Column(String)
    file_size = Column(Integer)
    file_type = Column(String)
    mime_type = Column(String)
    upload_path = Column(String)
    content_preview = Column(Text)
    processed_by_agent = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

# Create tables
Base.metadata.create_all(bind=engine)

# --- New Methods ---
def get_or_create_session(db, session_id: str, title: str = "New Chat"):
    """Get existing session or create new one"""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        session = ChatSession(
            session_id=session_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    return session

def get_session_stats(db, session_id: str) -> dict:
    """Get statistics for a session"""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        return {}
    
    conversations_count = db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).count()
    
    return {
        "session_id": session_id,
        "total_messages": conversations_count,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "is_archived": session.is_archived
    }

def get_db(): # Old method
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

