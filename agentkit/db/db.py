from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Optional
import uuid

from agentkit.db.models import Base, Chat, Message


class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Enable foreign keys and WAL mode
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.execute(text("PRAGMA journal_mode = WAL"))
            conn.commit()
        
        # Create tables
        Base.metadata.create_all(self.engine)

    def create_chat(self, title: Optional[str] = None) -> Chat:
        with self.SessionLocal() as session:
            chat = Chat(id=str(uuid.uuid4()), title=title)
            session.add(chat)
            session.commit()
            session.refresh(chat)
            return chat
    
    def save_message(self, chat_id: str, role: str, content: str) -> Message:
        with self.SessionLocal() as session:
            # Get next sequence number for this chat
            stmt = (
                select(func.coalesce(func.max(Message.sequence), 0) + 1)
                .where(Message.chat_id == chat_id)
            )
            next_sequence = session.execute(stmt).scalar()
            
            message = Message(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                sequence=next_sequence,
                role=role,
                content=content
            )
            session.add(message)
            
            # Update chat's updated_at
            chat = session.get(Chat, chat_id)
            if chat:
                chat.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(message)
            return message
    
    def get_chat_history(self, chat_id: str, limit: int = 50) -> List[Message]:
        with self.SessionLocal() as session:
            stmt = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.sequence)  # Order by sequence, not created_at
                .limit(limit)
            )
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def get_messages_from_sequence(self, chat_id: str, from_sequence: int) -> List[Message]:
        """Get messages starting from a specific sequence number"""
        with self.SessionLocal() as session:
            stmt = (
                select(Message)
                .where(Message.chat_id == chat_id, Message.sequence >= from_sequence)
                .order_by(Message.sequence)
            )
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def get_chat(self, chat_id: str) -> Optional[Chat]:
        with self.SessionLocal() as session:
            return session.get(Chat, chat_id)

    def list_chats(self, limit: int = 20) -> List[Chat]:
        with self.SessionLocal() as session:
            stmt = (
                select(Chat)
                .order_by(Chat.updated_at.desc())
                .limit(limit)
            )
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def delete_chat(self, chat_id: str):
        with self.SessionLocal() as session:
            chat = session.get(Chat, chat_id)
            if chat:
                session.delete(chat)
                session.commit()

    def close(self):
        """Close database connections and dispose of the engine"""
        self.engine.dispose()