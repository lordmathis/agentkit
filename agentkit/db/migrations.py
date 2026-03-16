import logging
from sqlalchemy import text, inspect

logger = logging.getLogger(__name__)


def run_migrations(engine):
    with engine.connect() as conn:
        _migrate_file_ids_column(conn)
        _migrate_drop_file_attachments_table(conn)
        _migrate_tool_call_id_column(conn)
        conn.commit()


def _migrate_file_ids_column(conn):
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("messages")]

    if "file_ids" not in columns:
        logger.info("Adding file_ids column to messages table...")
        conn.execute(text("ALTER TABLE messages ADD COLUMN file_ids TEXT"))
        logger.info("Column file_ids added to messages table.")
    else:
        logger.debug("Column file_ids already exists in messages table.")


def _migrate_drop_file_attachments_table(conn):
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "file_attachments" in tables:
        logger.info("Dropping file_attachments table...")
        conn.execute(text("DROP TABLE file_attachments"))
        logger.info("Table file_attachments dropped.")
    else:
        logger.debug("Table file_attachments does not exist.")


def _migrate_tool_call_id_column(conn):
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("messages")]

    if "tool_call_id" not in columns:
        logger.info("Adding tool_call_id column to messages table...")
        conn.execute(text("ALTER TABLE messages ADD COLUMN tool_call_id TEXT"))
        logger.info("Column tool_call_id added to messages table.")
    else:
        logger.debug("Column tool_call_id already exists in messages table.")
