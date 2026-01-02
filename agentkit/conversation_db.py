import uuid
from sqlite3 import Connection

_connection = None

def get_connection(db_path: str) -> Connection:
    """Get a database connection."""
    global _connection
    if _connection is None:
        _connection = Connection(db_path)
        _init_db(_connection)
    return _connection

def _init_db(conn: Connection):
    """Initialize the conversation database."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

def create_conversation(conn: Connection, title: str):
    """Create a new conversation in the database."""
    conversation_id = str(uuid.uuid4())
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (conversation_id, title))
    conn.commit()
    return cursor.lastrowid

def update_conversation_title(conn: Connection, conversation_id: str, new_title: str):
    """Update the title of an existing conversation."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (new_title, conversation_id))
    conn.commit()

def save_conversation_messages(conn: Connection, conversation_id: str, title: str, messages: list):
    """Save a conversation to the database."""
    cursor = conn.cursor()
    # Create new conversation or update "title ot"
    conn.execute("""
        SELECT id FROM conversations WHERE id = ?
    """, (conversation_id,))

    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (conversation_id, title))
    else:
        cursor.execute("""
            UPDATE conversations SET updated_at = CURRENT_TIMESTAMP, title = ? WHERE id = ?
        """, (title, conversation_id))

    for msg in messages:
        cursor.execute("""
            INSERT INTO messages (id, conversation_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (msg['id'], conversation_id, msg['role'], msg['content']))
    conn.commit()
    conn.close()

def get_conversation(conn: Connection, conversation_id: str):
    """Retrieve all conversations from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, created_at, updated_at FROM conversation WHERE id = ?
    """, (conversation_id,))
    return cursor.fetchone()
    
def list_conversations(conn: Connection):
    """Retrieve all conversations from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC
    """)
    return cursor.fetchall()

def get_conversation_messages(conn: Connection, conversation_id: str):
    """Retrieve messages for a specific conversation."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
    """, (conversation_id,))
    return cursor.fetchall()

def delete_conversation(conn: Connection, conversation_id: str):
    """Delete a conversation and its messages from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM conversations WHERE id = ?
    """, (conversation_id,))
    conn.commit()