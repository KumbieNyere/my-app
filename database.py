import os
import sqlite3

# Reads DB_PATH from Render's environment variables (e.g., /var/data/school_database.db)
# Falls back to local 'school_database.db' when testing in VS Code
DB_PATH = os.getenv("DB_PATH", "school_database.db")

# Automatically create parent directories if they don't exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


