import streamlit as st
import sqlite3
import bcrypt
import os
from utils import get_db_path

DATABASE_FILE = get_db_path("users.db")

def create_users_table():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

create_users_table()

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(username, password):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def authenticate_user(username, password):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        hashed_password = result[0]
        if verify_password(password, hashed_password):
            login_user(username)  # Set the login state
            return True
    return False

def is_user_logged_in():
    return 'logged_in' in st.session_state and st.session_state['logged_in']

def login_user(username):
    st.session_state['logged_in'] = True
    st.session_state['username'] = username

def logout_user():
    """Clear user-specific session data on logout"""
    if 'current_user' in st.session_state:
        del st.session_state['current_user']
    if 'user_chat_histories' in st.session_state:
        del st.session_state['user_chat_histories']
    st.session_state['logged_in'] = False
    if 'username' in st.session_state:
        del st.session_state['username']
