import hashlib
import json
from database_cache import store_in_db_cache, get_from_db_cache, init_cache_db, store_key_value, get_key_value


# Initialize cache database
init_cache_db()
def get_cache_key(query, schema):
    """Generate a unique cache key based on the query and schema."""
    combined = f"{query}|{schema}"
    return hashlib.md5(combined.encode()).hexdigest()

# cache key and value
def cache_key_value(key, value):
    store_key_value(key, value)

def get_from_db_cache(key):
    return get_key_value(key)


def cache_response(query, schema, sql_query, summary, visualization, follow_up, results, columns):
    """Cache the query response in database only."""
    try:
        cache_key = get_cache_key(query, schema)
        schema_hash = hashlib.sha256(schema.encode()).hexdigest()
        
        cached_data = {
            'query': query,
            'schema_hash': schema_hash,
            'sql_query': sql_query,
            'summary': summary,
            'visualization': visualization,
            'follow_up_questions': follow_up,
            'results': results,
            'columns': columns
        }
        
        # Store in database only
        store_in_db_cache(cache_key, cached_data)
        return True
    except Exception as e:
        print(f"Error caching response: {e}")
        return False
def get_cached_response(query, schema):
    """Retrieve cached response from database."""
    try:
        cache_key = get_cache_key(query, schema)
        response = get_from_db_cache(cache_key)
        if response and 'visualization' in response:
            # Ensure visualization data has required fields
            if 'data' not in response['visualization']:
                return None
        return response
    except Exception as e:
        print(f"Error retrieving from cache: {e}")
        return None
