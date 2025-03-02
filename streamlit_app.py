import streamlit as st
import os
import threading
from socket_server import start_websocket_server
from auth import authenticate_user, register_user, logout_user, is_user_logged_in
from database import handle_database_upload, get_database_schema, create_mysql_connection, get_mysql_schema
from nl2sql import process_query, process_query_mysql
from visualization import generate_visualization
from utils import load_env, init_chat_history_table
from cache import get_cached_response, cache_response
from follow_up import generate_follow_up_questions
import altair as alt
import pandas as pd
from datetime import datetime

load_env()

st.set_page_config(page_title="NL2SQL Chatbot", page_icon="🤖")



def main():
    init_chat_history_table()

    # Streamlit UI
    st.title("NL2SQL Chatbot")



    st.sidebar.header("Database Management")
    database_option = st.sidebar.selectbox("Select Database Type", ["Sqlite/CSV/Excel", "MySQL"], key="database_type")
    
    if database_option == "MySQL":
        st.sidebar.subheader("MySQL Connection")
        host = st.sidebar.text_input("Host")
        user = st.sidebar.text_input("User")
        password = st.sidebar.text_input("Password", type="password")
        database = st.sidebar.text_input("Database Name")

        if st.sidebar.button("Connect to MySQL", key="connect_mysql"):
            connection = create_mysql_connection(host, user, password, database)
            if connection:
                st.sidebar.success("Connected to MySQL successfully!")
                schema = get_mysql_schema(connection)
                st.session_state['connection'] = connection
                st.session_state['db_type'] = "mysql"
                st.session_state['schema'] = schema  # Store schema in session state
                st.sidebar.subheader("MySQL Schema")
                st.sidebar.code(schema, language="sql")
            
    
    else: # SQLite handling
        uploaded_file = st.sidebar.file_uploader("Upload Database or CSV/Excel", type=["db", "csv", "xlsx", "sql"], key="upload_file")
        if uploaded_file:
            if uploaded_file.name.endswith(".csv") or uploaded_file.name.endswith(".xlsx"):
                db_path = handle_csv_or_excel_upload(uploaded_file)
            elif uploaded_file.name.endswith(".sql"):
                db_path = handle_sql_upload(uploaded_file)
            else:
                db_path = handle_database_upload(uploaded_file)

            if db_path:
                schema = get_database_schema(db_path)
                st.sidebar.subheader("Database Schema")
                st.sidebar.code(schema, language="sql")
                st.session_state['db_path'] = db_path
                st.session_state['schema'] = schema
            else:
                st.error("Error processing the database file.")
                return
        else:
            st.info("Please upload a SQLite database to start.")
            return

    
    # Proceed with query processing
    user_query = st.chat_input("Ask me anything about your database", key="user_query")
    if user_query:
        add_message_to_history("user", user_query)
        with st.chat_message("user"):
            st.markdown(user_query)
        if 'connection' in st.session_state and st.session_state['db_type'] == "mysql":
            # Logic for MySQL query processing would go here (similar to SQLite)
            connection = st.session_state['connection']
            schema = st.session_state.get('schema')  # Safely access schema
            with st.spinner("Processing your query..."):
                try:
                    response = process_query_mysql(user_query, connection, schema)
                    print(f"Response: {response}")
                    if response and 'sql_query' in response:
                        handle_response(response)
                        cache_response(user_query, schema, response['sql_query'], 
                                     response.get('summary', 'No summary available.'), 
                                     response['visualization'], 
                                     response['follow_up_questions'], response.get('results', []), 
                                     response.get('columns', []))
                    else:
                        add_message_to_history("assistant", "I'm sorry, I couldn't understand your query.")
                        with st.chat_message("assistant"):
                            st.markdown("I'm sorry, I couldn't understand your query.")
                except Exception as e:
                    add_message_to_history("assistant", f"An error occurred: {e}")
                    with st.chat_message("assistant"):
                        st.error(f"An error occurred: {e}")

        elif 'db_path' in st.session_state:
            # SQLite query processing
            with st.spinner("Processing your query..."):
                try:
                    response = process_query(user_query, st.session_state['db_path'], st.session_state['schema'])
                    if response and 'sql_query' in response:
                        handle_response(response)
                        cache_response(user_query, st.session_state['schema'], response['sql_query'], 
                                     response['summary'], response['visualization'], 
                                     response['follow_up_questions'], response.get('results', []), 
                                     response.get('columns', []))
                    else:
                        add_message_to_history("assistant", "I'm sorry, I couldn't understand your query.")
                        with st.chat_message("assistant"):
                            st.markdown("I'm sorry, I couldn't understand your query.")
                except Exception as e:
                    add_message_to_history("assistant", f"An error occurred: {e}")
                    with st.chat_message("assistant"):
                        st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

