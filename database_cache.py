import sqlite3
import json
import hashlib
from datetime import datetime

def init_cache_db():
    """Initialize the cache database with required tables."""
    conn = sqlite3.connect('query_cache.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS query_cache (
        cache_key TEXT PRIMARY KEY,
        query TEXT,
        schema_hash TEXT,
        sql_query TEXT,
        summary TEXT,
        visualization_data TEXT,
        follow_up_questions TEXT,
        results TEXT,
        columns TEXT,
        created_at TIMESTAMP,
        last_accessed TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def store_in_db_cache(cache_key, query_data):
    """Store query results in database cache."""
    conn = sqlite3.connect('query_cache.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO query_cache
        (cache_key, query, schema_hash, sql_query, summary, visualization_data, 
         follow_up_questions, results, columns, created_at, last_accessed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cache_key,
            query_data['query'],
            query_data['schema_hash'],
            query_data['sql_query'],
            query_data['summary'],
            json.dumps(query_data['visualization']),
            json.dumps(query_data['follow_up_questions']),
            json.dumps(query_data['results']),
            json.dumps(query_data['columns']),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
    finally:
        conn.close()

def get_from_db_cache(cache_key):
    """Retrieve query results from database cache."""
    conn = sqlite3.connect('query_cache.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT sql_query, summary, visualization_data, follow_up_questions, 
               results, columns, schema_hash
        FROM query_cache 
        WHERE cache_key = ?
        ''', (cache_key,))
        
        result = cursor.fetchone()
        if result:
            # Update last accessed time
            cursor.execute('''
            UPDATE query_cache 
            SET last_accessed = ? 
            WHERE cache_key = ?
            ''', (datetime.now().isoformat(), cache_key))
            conn.commit()
            
            return {
                'sql_query': result[0],
                'summary': result[1],
                'visualization': json.loads(result[2]),
                'follow_up_questions': json.loads(result[3]),
                'results': json.loads(result[4]),
                'columns': json.loads(result[5])
            }
        return None
    finally:
        conn.close()
