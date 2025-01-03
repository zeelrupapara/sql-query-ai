import sqlite3
import streamlit as st
import os
from utils import get_db_path

def handle_database_upload(uploaded_file):
    try:
        db_path = get_db_path(uploaded_file.name)
        with open(db_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return db_path
    except Exception as e:
        st.error(f"Error saving database file: {e}")
        return None

def get_database_schema(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schema = ""
        for table in tables:
            table_name = table[0]
            schema += f"Table: {table_name}\n"
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for column in columns:
                schema += f"  - {column[1]} ({column[2]})\n"
        conn.close()
        return schema
    except Exception as e:
        st.error(f"Error extracting database schema: {e}")
        return None
