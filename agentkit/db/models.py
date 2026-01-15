from sqlalchemy import Index, UniqueConstraint, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, UTC
from typing import Optional

class Base(DeclarativeBase):
    pass

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, default="Untitled Chat")

    # Configuration fields for storing chat settings
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_servers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as string
    model_params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON object as string

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # Order within chat
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    reasoning_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    
    __table_args__ = (
        # Ensure unique sequence per chat
        UniqueConstraint('chat_id', 'sequence', name='uq_chat_sequence'),
        # Index for efficient ordering
        Index('idx_chat_sequence', 'chat_id', 'sequence'),
    )

class FileAttachment(Base):
    __tablename__ = "file_attachments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)  # Path on disk
    content_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    
    __table_args__ = (
        Index('idx_message_attachments', 'message_id'),
    )
