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

def initialize_session_state():
    """Initialize session state variables"""
    if 'user_chat_histories' not in st.session_state:
        st.session_state['user_chat_histories'] = {}
    
    # Initialize current user's chat history
    current_user = st.session_state.get('current_user')
    if current_user and current_user not in st.session_state['user_chat_histories']:
        st.session_state['user_chat_histories'][current_user] = []

def get_current_chat_history():
    """Get chat history for current user"""
    current_user = st.session_state.get('current_user')
    return st.session_state['user_chat_histories'].get(current_user, [])

def display_chat_history():
    """Display chat history with static visualizations."""
    chat_history = get_current_chat_history()
    for message in chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("visualization"):
                viz_chart = create_static_visualization(message["visualization"])
                if viz_chart:
                    st.altair_chart(viz_chart, use_container_width=True)

def add_message_to_history(role, content, visualization=None):
    """Add message to chat history with visualization data and settings."""
    current_user = st.session_state.get('current_user')
    if current_user:
        # If visualization exists, store the current chart settings
        if visualization:
            viz_settings = {
                'chart_type': st.session_state.get('current_chart_type', 'bar'),
                'x_col': st.session_state.get('current_x_col'),
                'y_col': st.session_state.get('current_y_col'),
                'data': visualization  # Store the complete visualization data
            }
        else:
            viz_settings = None

        message = {
            "role": role,
            "content": content,
            "visualization": viz_settings,
            "timestamp": datetime.now().isoformat()
        }
        
        # Initialize list if it doesn't exist
        if current_user not in st.session_state['user_chat_histories']:
            st.session_state['user_chat_histories'][current_user] = []
            
        st.session_state['user_chat_histories'][current_user].append(message)

def create_static_visualization(viz_settings):
    """Create a visualization without interactive elements."""
    if not viz_settings or not viz_settings.get('data'):
        return None

    try:
        # Get data and settings
        data = viz_settings['data'].get('data', [])
        if not data:
            return None
            
        chart_type = viz_settings.get('chart_type', 'bar')
        x_col = viz_settings.get('x_col')
        y_col = viz_settings.get('y_col')
        
        # If columns not specified, try to get from default settings
        if not x_col or not y_col:
            default_settings = viz_settings['data'].get('default_settings', {})
            x_col = default_settings.get('x_col')
            y_col = default_settings.get('y_col')
            
        if not x_col or not y_col:
            return None

        # Convert data to DataFrame and ensure column types
        df = pd.DataFrame(data)
        
        # Apply the same styling as create_visualization
        return create_visualization(df, chart_type, x_col, y_col)
        
    except Exception as e:
        st.error(f"Error creating static visualization: {e}")
        return None

def create_visualization(data, chart_type, x_col, y_col):
    """Create an Altair visualization based on the selected parameters."""
    try:
        # Convert data to DataFrame
        df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame(data)

        # Color scheme
        color_scheme = 'tableau10'  # Professional color palette
        
        # Basic chart configuration with improved styling
        base_config = {
            "width": 600,
            "height": 400,
        }

        # Common encoding configurations
        tooltip_config = [
            alt.Tooltip(x_col, title=x_col.replace('_', ' ').title()),
            alt.Tooltip(y_col, title=y_col.replace('_', ' ').title(), format=',.0f')
        ]

        if chart_type == "bar":
            chart = alt.Chart(df, **base_config).mark_bar(
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
                opacity=0.8,
                width=20  # Adjust bar width
            ).encode(
                x=alt.X(x_col, 
                       sort='-y',
                       axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
                y=alt.Y(y_col,
                       scale=alt.Scale(zero=True),
                       axis=alt.Axis(grid=True, gridOpacity=0.3)),
                color=alt.Color(y_col, scale=alt.Scale(scheme=color_scheme)),
                tooltip=tooltip_config
            ).properties(
                title=alt.TitleParams(
                    f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )
            
        elif chart_type == "line":
            chart = alt.Chart(df, **base_config).mark_line(
                point=True,
                strokeWidth=3,
                opacity=0.8
            ).encode(
                x=alt.X(x_col, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(y_col, 
                       scale=alt.Scale(zero=False),
                       axis=alt.Axis(grid=True, gridOpacity=0.3)),
                color=alt.value('#1f77b4'),  # Professional blue color
                tooltip=tooltip_config
            ).properties(
                title=alt.TitleParams(
                    f"Trend of {y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )
            
        elif chart_type == "scatter":
            chart = alt.Chart(df, **base_config).mark_circle(
                size=100,
                opacity=0.6
            ).encode(
                x=alt.X(x_col, scale=alt.Scale(zero=False)),
                y=alt.Y(y_col, scale=alt.Scale(zero=False)),
                color=alt.Color(y_col, scale=alt.Scale(scheme=color_scheme)),
                size=alt.value(100),
                tooltip=tooltip_config
            ).properties(
                title=alt.TitleParams(
                    f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )
            
        elif chart_type == "heatmap":
            chart = alt.Chart(df, **base_config).mark_rect().encode(
                x=alt.X(x_col, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y(y_col),
                color=alt.Color('count()',
                              scale=alt.Scale(scheme='viridis'),
                              legend=alt.Legend(title='Count')),
                tooltip=[
                    alt.Tooltip(x_col),
                    alt.Tooltip(y_col),
                    alt.Tooltip('count()', title='Count')
                ]
            ).properties(
                title=alt.TitleParams(
                    f"Heatmap of {y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}",
                    fontSize=16,
                    anchor='middle'
                )
            )

        # Add a configuration to make the chart more professional
        chart = chart.configure_axis(
            gridColor='#f0f0f0',
            domainColor='#cccccc',
            tickColor='#cccccc',
            labelFontSize=12,
            titleFontSize=14
        ).configure_title(
            fontSize=16,
            font='Arial',
            anchor='middle',
            color='#333333'
        ).configure_view(
            strokeWidth=0
        )

        return chart
    except Exception as e:
        st.error(f"Error creating visualization: {e}")
        return None

def show_visualization_options(response, key_prefix):
    """Handle visualization options and display for new messages only."""
    if not response.get('visualization'):
        return

    viz_data = response['visualization']
    
    try:
        df = pd.DataFrame(viz_data['data'])
        
        # Ensure numeric and categorical columns are properly identified
        numeric_types = ['int64', 'float64']
        object_types = ['object', 'string']
        
        numeric_cols = df.select_dtypes(numeric_types).columns.tolist()
        categorical_cols = df.select_dtypes(object_types).columns.tolist()
        
        # Update visualization data
        viz_data.update({
            'numeric_columns': numeric_cols,
            'categorical_columns': categorical_cols
        })
        
        # Create visualization
        if numeric_cols and (categorical_cols or numeric_cols):
            chart = create_visualization(
                viz_data['data'],
                st.session_state.get('current_chart_type', 'bar'),
                categorical_cols[0] if categorical_cols else numeric_cols[0],
                numeric_cols[0]
            )
            if chart:
                st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("No Visualization Needed")
            
    except Exception as e:
        st.error(f"Error in visualization options: {e}")

def handle_cached_response(cached_response):
    """Handle cached response with proper visualization."""
    if cached_response and 'visualization' in cached_response:
        try:
            # Convert cached data back to proper format
            df = pd.DataFrame(cached_response['visualization']['data'])
            
            # Update visualization data with proper column types
            numeric_types = ['int64', 'float64']
            object_types = ['object', 'string']
            
            numeric_cols = df.select_dtypes(['int64', 'float64']).columns.tolist()
            categorical_cols = df.select_dtypes(['object', 'string']).columns.tolist()
            
            cached_response['visualization'].update({
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols
            })
            
            # Add to chat history and display
            handle_response(cached_response)
            return True
        except Exception as e:
            st.error(f"Error processing cached response: {e}")
            return False
    return False

def handle_response(response):
    """Handle the response and visualization creation."""
    sql_query = response.get('sql_query')
    summary = response.get('summary', 'No summary available.')
    visualization = response.get('visualization')
    follow_up_questions = response.get('follow_up_questions')
    
    # Format the content based on what's available
    content = ""
    if sql_query:
        content += f"SQL Query: {sql_query}\n\n"
    content += f"Summary: {summary}"
    
    # Add to chat history with visualization
    add_message_to_history("assistant", content, visualization)
    
    with st.chat_message("assistant"):
        if sql_query and sql_query.startswith("PRAGMA"):
            st.markdown(summary)
        else:
            st.markdown(summary)
            if visualization:
                show_visualization_options(response, f"viz_{datetime.now().isoformat()}")
        if follow_up_questions:
            st.markdown("Follow-up questions:")
            for question in follow_up_questions:
                st.markdown(f"- {question}")

def handle_csv_or_excel_upload(uploaded_file):
    import tempfile
    import sqlite3
    import pandas as pd
    
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    # Read CSV or Excel into a DataFrame
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Write DataFrame to temporary SQLite DB
    conn = sqlite3.connect(temp_db_path)
    df.to_sql("uploaded_data", conn, if_exists="replace", index=False)
    conn.close()

    return temp_db_path

def handle_sql_upload(uploaded_file):
    import tempfile
    import sqlite3
    
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    
    try:
        # Read SQL file content
        sql_content = uploaded_file.getvalue().decode('utf-8')
        
        # Connect to the temporary database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Split and execute SQL statements
        # This handles both single and multiple statements
        sql_commands = sql_content.split(';')
        
        for command in sql_commands:
            command = command.strip()
            if command:  # Skip empty statements
                try:
                    cursor.execute(command)
                except sqlite3.Error as e:
                    st.warning(f"Skipping invalid SQL statement: {e}")
                    continue
        
        conn.commit()
        conn.close()
        return temp_db_path
        
    except Exception as e:
        st.error(f"Error processing SQL file: {e}")
        os.unlink(temp_db_path)  # Clean up the temporary file
        return None

def main():
    init_chat_history_table()

    # Start the WebSocket server in a separate thread
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.daemon = True  # Thread exits when the main program exits
    websocket_thread.start()

    # Streamlit UI
    st.title("NL2SQL Chatbot")

    if not is_user_logged_in():
        auth_tab, register_tab = st.tabs(["Login", "Register"])
        
        with auth_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit_button = st.form_submit_button("Login")
                
                if submit_button:
                    if authenticate_user(username, password):
                        st.session_state['current_user'] = username
                        initialize_session_state()
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
        
        with register_tab:
            with st.form("register_form"):
                new_username = st.text_input("New Username")
                new_password = st.text_input("New Password", type="password")
                register_button = st.form_submit_button("Register")
                
                if register_button:
                    if register_user(new_username, new_password):
                        st.success("Registered successfully! Please log in.")
                    else:
                        st.error("Username already exists.")
        return

    if st.button("Logout"):
        st.session_state['current_user'] = None
        logout_user()
        st.rerun()

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

        display_chat_history()
    
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

