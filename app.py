from flask import Flask, request, jsonify, render_template
import os
from other import (
    add_message_to_history, create_static_visualization, create_visualization,
    show_visualization_options, handle_cached_response, handle_response,
    handle_csv_or_excel_upload, handle_sql_upload
)
from database import (
    handle_database_upload, get_database_schema, create_mysql_connection,
    get_mysql_schema
)
from nl2sql import process_query, process_query_mysql
from utils import load_env, init_chat_history_table
from cache import get_cached_response, cache_response, cache_key_value, get_from_db_cache
from follow_up import generate_follow_up_questions

app = Flask(__name__)

# Initialize the app environment
load_env()
init_chat_history_table()

@app.route('/')
def index():
    """
    Render the chat UI.
    """
    return render_template('apex_chat_ui.html')

@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle file uploads and return the database schema.
    """
    file = request.files.get('file')
    db_type = request.form.get('db_type', 'sqlite')
    
    if not file:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

    try:
        if db_type == "mysql":
            host = request.form.get('host')
            user = request.form.get('user')
            password = request.form.get('password')
            database = request.form.get('database')
            connection = create_mysql_connection(host, user, password, database)
            schema = get_mysql_schema(connection)
            db_path = None

        else:  # Handling SQLite, CSV, or Excel
            if file.filename.endswith(".csv"):
                db_path = handle_csv_or_excel_upload(file)
            else:
                db_path = handle_database_upload(file)
            schema = get_database_schema(db_path)

        # Store in cache
        cache_key_value('db_path', db_path)
        cache_key_value('schema', schema)

        response = {'status': 'success', 'schema': schema, 'db_path': db_path}
        return jsonify(response), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """
    Process user queries and return responses.
    """
    data = request.json
    user_query = data.get('query')
    db_type = data.get('db_type', 'sqlite')

    if not user_query:
        return jsonify({'status': 'error', 'message': 'Query is required'}), 400

    try:
        db_path = get_from_db_cache('db_path')
        schema = get_from_db_cache('schema')

        if db_path is None or schema is None:
            return jsonify({'status': 'error', 'message': 'No database uploaded. Please upload a file first.'}), 400

        if db_type == 'mysql':
            connection_info = data.get('connection')
            response = process_query_mysql(user_query, connection_info, schema)
        else:
            response = process_query(user_query, db_path, schema)

        if response and 'sql_query' in response:
            return jsonify({
                'status': 'success',
                'summary': response.get('summary', 'No summary available.'),
                'visualization': response.get('visualization', {}),
                'follow_up_questions': response.get('follow_up_questions', []),
                'results': response.get('results', []),
                'columns': response.get('columns', [])
            }), 200
        else:
            return jsonify({'status': 'error', 'message': "Query could not be processed"}), 500

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
