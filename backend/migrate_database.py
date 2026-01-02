import os
import sys
from sqlalchemy import create_engine, text
from models.database import Base, engine

def migrate_database():
    """Migrate existing database to new schema"""
    
    print(" --- Starting database migration --- ")
    
    try:
        # Create new tables
        Base.metadata.create_all(bind=engine)
        print(" New tables created successfully")
        
        # Add new columns to existing tables
        with engine.connect() as conn:
            # Add message_id to conversations table if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE conversations 
                    ADD COLUMN IF NOT EXISTS message_id VARCHAR;
                """))
                print(" Added message_id column to conversations")
            except Exception as e:
                print(f"Note: message_id column might already exist: {e}")
            
            # Add error_details to agent_executions if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE agent_executions 
                    ADD COLUMN IF NOT EXISTS error_details TEXT;
                """))
                print(" Added error_details column to agent_executions")
            except Exception as e:
                print(f"Note: error_details column might already exist: {e}")
            
            # Update existing conversations with message_ids
            try:
                conn.execute(text("""
                    UPDATE conversations 
                    SET message_id = 'msg_' || id::text 
                    WHERE message_id IS NULL;
                """))
                print(" Updated existing conversations with message IDs")
            except Exception as e:
                print(f"Note: Error updating message IDs: {e}")
            
            conn.commit()
        
        print(" Database migration completed successfully!")
        
    except Exception as e:
        print(f" Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)