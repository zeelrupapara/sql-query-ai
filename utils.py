import os
from dotenv import load_dotenv
import sqlite3

def load_env():
    load_dotenv()

def get_db_path(filename):
    return os.path.join(os.getcwd(), filename)


def init_chat_history_table():
    """Initialize the chat history table if it doesn't exist."""
    DATABASE_FILE = get_db_path("user_chats.db")  # Database for chat history

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_chat_history(user_id):
    """Retrieve chat history for the specified user ID."""
    DATABASE_FILE = get_db_path("user_chats.db")  # Database for chat history

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT role, content, timestamp FROM chat_history WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    
    chat_histories = [{'role': row[0], 'content': row[1], 'timestamp': row[2]} for row in rows]
    conn.close()
    
    return chat_histories