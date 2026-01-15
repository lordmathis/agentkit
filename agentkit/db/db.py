from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC
from typing import Dict, List, Optional
import json
import uuid
import os
import shutil

from agentkit.db.models import Base, Chat, Message, FileAttachment


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
    
    def save_message(self, chat_id: str, role: str, content: str, reasoning_content: Optional[str] = None) -> Message:
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
                content=content,
                reasoning_content=reasoning_content
            )
            session.add(message)
            
            # Update chat's updated_at
            chat = session.get(Chat, chat_id)
            if chat:
                chat.updated_at = datetime.now(UTC)
            
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

    def update_chat(self, chat_id: str, **kwargs) -> Optional[Chat]:
        """Update chat metadata and configuration"""
        with self.SessionLocal() as session:
            chat = session.get(Chat, chat_id)
            if not chat:
                return None

            for key, value in kwargs.items():
                if hasattr(chat, key):
                    setattr(chat, key, value)

            chat.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(chat)
            return chat

    def save_chat_config(
        self,
        chat_id: str,
        model: str,
        system_prompt: Optional[str] = None,
        tool_servers: Optional[List[str]] = None,
        model_params: Optional[Dict] = None,
    ) -> Optional[Chat]:
        """Save chat configuration for restoration"""
        with self.SessionLocal() as session:
            chat = session.get(Chat, chat_id)
            if not chat:
                return None

            chat.model = model
            chat.system_prompt = system_prompt
            chat.tool_servers = json.dumps(tool_servers) if tool_servers else None
            chat.model_params = json.dumps(model_params) if model_params else None
            chat.updated_at = datetime.now()

            session.commit()
            session.refresh(chat)
            return chat

    def get_chat_config(self, chat_id: str) -> Optional[Dict]:
        """Get chat configuration"""
        with self.SessionLocal() as session:
            chat = session.get(Chat, chat_id)
            if not chat:
                return None

            return {
                "model": chat.model,
                "system_prompt": chat.system_prompt,
                "tool_servers": json.loads(chat.tool_servers) if chat.tool_servers else None,
                "model_params": json.loads(chat.model_params) if chat.model_params else None,
            }

    def close(self):
        """Close database connections and dispose of the engine"""
        self.engine.dispose()

    def save_file_attachment(
        self,
        message_id: str,
        filename: str,
        file_path: str,
        content_type: str
    ) -> FileAttachment:
        """Save a file attachment linked to a message"""
        with self.SessionLocal() as session:
            attachment = FileAttachment(
                id=str(uuid.uuid4()),
                message_id=message_id,
                filename=filename,
                file_path=file_path,
                content_type=content_type
            )
            session.add(attachment)
            session.commit()
            session.refresh(attachment)
            return attachment

    def get_message_attachments(self, message_id: str) -> List[FileAttachment]:
        """Get all file attachments for a message"""
        with self.SessionLocal() as session:
            stmt = (
                select(FileAttachment)
                .where(FileAttachment.message_id == message_id)
                .order_by(FileAttachment.created_at)
            )
            result = session.execute(stmt)
            return list(result.scalars().all())

    def branch_chat(self, source_chat_id: str, up_to_message_id: str, new_title: Optional[str] = None) -> Optional[Chat]:

        with self.SessionLocal() as session:
            # Get source chat
            source_chat = session.get(Chat, source_chat_id)
            if not source_chat:
                return None
            
            # Get the target message to find its sequence number
            target_message = session.get(Message, up_to_message_id)
            if not target_message or target_message.chat_id != source_chat_id:
                return None
            
            target_sequence = target_message.sequence
            
            # Create new chat with same config
            new_chat = Chat(
                id=str(uuid.uuid4()),
                title=new_title or "Untitled Chat",
                model=source_chat.model,
                system_prompt=source_chat.system_prompt,
                tool_servers=source_chat.tool_servers,
                model_params=source_chat.model_params
            )
            session.add(new_chat)
            session.flush()  # Get the new chat ID
            
            # Get messages up to and including target sequence
            stmt = (
                select(Message)
                .where(Message.chat_id == source_chat_id, Message.sequence <= target_sequence)
                .order_by(Message.sequence)
            )
            messages_to_copy = session.execute(stmt).scalars().all()
            
            # Copy messages and their attachments
            for old_message in messages_to_copy:
                # Create new message
                new_message = Message(
                    id=str(uuid.uuid4()),
                    chat_id=new_chat.id,
                    sequence=old_message.sequence,
                    role=old_message.role,
                    content=old_message.content,
                    reasoning_content=old_message.reasoning_content
                )
                session.add(new_message)
                session.flush()  # Get the new message ID
                
                # Get and copy attachments
                stmt_attachments = (
                    select(FileAttachment)
                    .where(FileAttachment.message_id == old_message.id)
                )
                attachments_to_copy = session.execute(stmt_attachments).scalars().all()
                
                for old_attachment in attachments_to_copy:
                    old_path = old_attachment.file_path
                    
                    # All files are stored in uploads/<chat_id>/ directory
                    # Replace the old chat_id with the new one
                    new_path = old_path.replace(
                        f"uploads/{source_chat_id}/", 
                        f"uploads/{new_chat.id}/"
                    )
                    
                    # Copy the physical file if it exists
                    if os.path.exists(old_path):
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        shutil.copy2(old_path, new_path)
                    
                    # Create new attachment record
                    new_attachment = FileAttachment(
                        id=str(uuid.uuid4()),
                        message_id=new_message.id,
                        filename=old_attachment.filename,
                        file_path=new_path,
                        content_type=old_attachment.content_type
                    )
                    session.add(new_attachment)
            
            session.commit()
            session.refresh(new_chat)
            return new_chat