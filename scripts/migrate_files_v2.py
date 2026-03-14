import sqlite3
import os
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def migrate(db_path: str):
    if not os.path.exists(db_path):
        logger.error(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Add file_ids to messages
        logger.info("Checking for file_ids column in messages table...")
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]

        if "file_ids" not in columns:
            logger.info("Adding file_ids column to messages table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN file_ids TEXT")
            logger.info("Column file_ids added.")
        else:
            logger.info("Column file_ids already exists in messages table.")

        # 2. Drop legacy file_attachments table
        logger.info("Checking for file_attachments table...")
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='file_attachments'"
        )
        if cursor.fetchone():
            logger.info("Dropping file_attachments table...")
            cursor.execute("DROP TABLE file_attachments")
            logger.info("Table file_attachments dropped.")
        else:
            logger.info("Table file_attachments does not exist.")

        conn.commit()
        logger.info("Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate AgentKit database to file attachments v2 schema."
    )
    parser.add_argument(
        "--db", default="agentkit.db", help="Path to the sqlite database file"
    )
    args = parser.parse_args()

    migrate(args.db)
