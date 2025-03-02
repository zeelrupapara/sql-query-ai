import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
from utils import get_db_path, load_env
from visualization import generate_visualization
from follow_up import generate_follow_up_questions
from model_config import LLMInterface

# Load environment variables at the start
load_dotenv()

# Set Google API key directly if needed as fallback
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "AIzaSyAtr0-4q5tGeoWFCqw6P6zrtGDr9SPXA8A")

# Initialize the LLM interface with Google model
llm = LLMInterface(model_type="google")

def execute_sql(sql_query, connection):
    """
    Runs the given SQL query against the specified database connection (SQLite or MySQL) 
    and returns results and columns.
    """
    try:
        cursor = connection.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return results, columns
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return None, None

def execute_sqlite(sql_query, db_path):
    """
    Runs the given SQL query against the specified SQLite database and returns results and columns.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()
        return results, columns
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return None, None

def refine_query(user_query, schema):
    """
    Refine the user query to be more SQL-friendly and schema-aware using metadata.
    """
    # Convert the metadata into a text format for the prompt
    schema_text = schema

    prompt = f"""
    You are an AI assistant. You receive an English query from a user. Your job is to refine it into a
    more precise question that aligns strictly with the schema below:

    {schema_text}

    Original User Query:
    "{user_query}"

    Instructions:
    1. Restate the user query more explicitly if it’s ambiguous. 
    2. If the user’s query references a concept that does not exist in the table’s columns, respond by retweeting the user query to known columns.
    3. Provide references to the correct columns (e.g. 'units_sold', 'category') if you are certain they match the user’s intention.
    4. If the user wants an aggregate measure (e.g., sum, average), mention that in the refined question.
    5. If question is asked about a specific product or category, dont just use user provided name of the product or catagory use LIKE operator to match the string of the product or category name.
    6. If user question is about comparison of multiple columns, use AVG, SUM, MAX, MIN etc. functions to compare the columns. Dont just write all the columns in the query be smart and use only subset of columns.


    **VERY VERY Important:**
    If User Query is from below examples, use below SQL Query directly and dont refine the query.:

    Example: Are there any noticeable differences in symptom relief ratings between Indica, Sativa, and Hybrid strains?
    SQL Query : 
    SELECT
    Strain,
    AVG(Symptom_dizzy_Rating) AS Avg_Dizzy_Rating,
    AVG(Symptom_anxious_Rating) AS Avg_Anxious_Rating,
    AVG(Symptom_stress_Rating) AS Avg_Stress_Rating,
    AVG(Symptom_pain_Rating) AS Avg_Pain_Rating,
    AVG(Symptom_depression_Rating) AS Avg_Depression_Rating,
        AVG(Symptom_anxiety_Rating) AS Avg_Anxiety_Rating,
        AVG(Symptom_insomnia_Rating) AS Avg_Insomnia_Rating,
        AVG(Symptom_migraines_Rating) AS Avg_Migraines_Rating,
        AVG(Symptom_asthma_Rating) AS Avg_Asthma_Rating,
        AVG(Symptom_arthritis_Rating) AS Avg_Arthritis_Rating,
        AVG(Symptom_ADD_ADHD_Rating) AS Avg_ADD_ADHD_Rating,
        AVG(Symptom_epilepsy_Rating) AS Avg_Epilepsy_Rating
    FROM cannabis
    GROUP BY
    Strain;

    Example User Query: "are millennials munching more on CBD delights or going classic with pre-rolls? Let’s crack the code and cater to their actual cravings, not assumptions."
    Refined Question: "Which product category, between CBD products and pre-rolls, has higher units sold among millennials, based on the 'Category', 'Units_Sold', and 'Age' columns?"

    Example User Query: "Which strains or products show a consistent performance across multiple symptom relief categories?"
    SQL Query Output: SELECT Product, AVG(Symptom_anxious_Rating) AS avg_anxious_rating, AVG(Symptom_stress_Rating) AS avg_stress_rating, AVG(Symptom_pain_Rating) AS avg_pain_rating FROM cannabis GROUP BY Product ORDER BY (avg_anxious_rating+avg_stress_rating+avg_pain_rating) DESC LIMIT 10;

    Example User Query: Which products have the highest ratings for stress relief, and how do their sales compare across different store locations?
    SELECT Product, Store_Location, AVG(Symptom_stress_Rating) AS avg_stress_rating, SUM(Units_Sold) AS total_units_sold FROM cannabis GROUP BY Product, Store_Location ORDER BY avg_stress_rating DESC LIMIT 10;

    Output: 
    Return your refined question in a short natural language form that references the column names only.

    """

    try:
        refined_query = llm.generate_completion(prompt, temperature=0.2)
        print(f"Refined Query: {refined_query}")
        return refined_query
    except Exception as e:
        print(f"Error refining user query: {e}")
        # Fallback to the original user query if refinement fails
        return user_query

def is_column_query(query):
    """Check if query is asking about columns/schema."""
    keywords = ['column', 'header', 'schema', 'structure', 'field', 'attribute', 'row', 'table']
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)

def get_table_columns(db_path, table_name=None):
    """Get column information from the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if table_name:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [f"{row[1]} ({row[2]})" for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            columns = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns[table_name] = [f"{row[1]} ({row[2]})" for row in cursor.fetchall()]
        
        conn.close()
        return columns
    except Exception as e:
        print(f"Error getting columns: {e}")
        return None

def classify_query(user_query, schema):
    """Updated classification to provide more natural responses for non-DB questions."""
    schema_text = schema
    
    # First, check if it's a column query
    column_keywords = ['header', 'column', 'field', 'attribute', 'schema', 'structure']
    if any(keyword in user_query.lower() for keyword in column_keywords):
        return True, "SHOW_COLUMNS"
    
    # Define business domain questions that should get direct answers
    business_questions = {
        'price': """Generally, product box size does typically affect price - larger packages often cost more but may offer better value per unit. However, the relationship isn't always linear as factors like bulk discounts, packaging costs, and market positioning also play important roles.""",
        'packaging': """Product packaging and box size choices usually depend on several factors including product protection, shelf presence, shipping efficiency, and consumer preferences. These decisions can significantly impact both costs and sales performance.""",
        'marketing': """Marketing strategies should focus on highlighting the product's unique value proposition and benefits rather than just physical attributes. Consider emphasizing quality, effectiveness, and customer experience."""
    }
    
    # Check if the query matches any business domain topics
    query_lower = user_query.lower()
    for topic, response in business_questions.items():
        if topic in query_lower:
            return False, response
    
    # If not a business domain question, check if it can be answered with the database
    try:
        classification_prompt = f"""
        Determine if this question requires database access or should be answered with general business knowledge:
        Question: "{user_query}"
        Schema: {schema_text}
        
        If the question cannot be answered with the database, provide a brief, natural response about the topic.
        If it can be answered with the database, respond with exactly "DB".
        """

        answer = llm.generate_completion(classification_prompt, temperature=0.1)
        print(f"Classification Response: {answer}")
        
        if answer.upper().strip() == "DB":
            return True, None
        else:
            # Make the response more natural by removing database-related phrases
            response = answer.replace("I cannot answer this with the database.", "")
            response = response.replace("The database doesn't contain", "I can tell you that")
            response = response.strip()
            return False, response
            
    except Exception as e:
        # Provide a general response if classification fails
        return False, "Based on general business knowledge, product box size typically does affect pricing through factors like materials cost, shipping efficiency, and perceived value. Would you like to know more about specific aspects of this relationship?"

def generate_sql(user_query, schema):
    """
    Generate an SQL query based on user query and metadata using LLM.
    Enhanced with better error handling and query validation.
    """
    schema_text = schema

    prompt = f"""
    You are a SQL expert. Generate a SQL query for the following question using the given schema:
    
    Schema: {schema_text}
    Question: "{user_query}"

    Requirements:
    1. MUST start with SELECT
    2. Use proper SQL syntax for SQLite
    3. For questions about "best performing" or "highest", use ORDER BY and LIMIT
    4. Group results if aggregating
    5. Always include proper column names as shown in schema
    6. For units sold analysis, use SUM(Units_Sold)

    Example valid responses:
    - SELECT Product, SUM(Units_Sold) as total_units FROM cannabis GROUP BY Product ORDER BY total_units DESC LIMIT 10
    - SELECT Product, COUNT(*) as count FROM cannabis GROUP BY Product ORDER BY count DESC LIMIT 5

    Output ONLY the SQL query with no additional text or formatting.
    
    # Contraints in Output Response:
    - Query Should be start with the SELECT and end with `;`
    """

    try:
        sql_query = llm.generate_completion(prompt, temperature=0.4)
        print(f"SQL Query: {sql_query}")
        
        # Extract the SQL query between 'SELECT' and ';'
        start_index = sql_query.upper().find('SELECT')
        end_index = sql_query.rfind(';') + 1
        if start_index == -1 or end_index == 0:
            raise ValueError("Generated query does not contain a valid SQL statement")
        
        sql_query = sql_query[start_index:end_index].strip()
        
        print(f"Extracted SQL Query: {sql_query}")
        return sql_query
        
    except Exception as e:
        print(f"Error in generate_sql: {str(e)}")
        raise Exception(f"Error generating SQL: {str(e)}")

def generate_follow_up_questions(user_query, schema, results=None):
    """Generate contextual follow-up questions."""
    prompt = f"""Based on this query and schema, suggest 3 natural follow-up questions.
    
Previous query: "{user_query}"
Schema: {schema}

Requirements:
- Questions should be related to the current query
- Focus on business insights
- Each question on a new line
- No numbering or bullet points
- The question must be compelety answerable with the given schema and must be very easy and realted to original query.

Example output:
How does this compare to last month's performance?
What are the top categories in these results?
Which locations show the strongest sales for these products?
"""
    
    try:
        response = llm.generate_completion(prompt, temperature=0.1)
        questions = [q.strip() for q in response.split('\n') if q.strip()]
        return questions[:3] if questions else [
            "Would you like to see this data broken down by category?",
            "Should we analyze any specific time periods?",
            "Would you like to compare these results with other metrics?"
        ]
    except Exception as e:
        print(f"Error generating follow-up questions: {e}")
        return [
            "What other aspects would you like to analyze?",
            "Should we look at different metrics?",
            "Would you like to see more detailed insights?"
        ]

def process_query_mysql(user_query, connection, schema):
    """
    Enhanced process_query with support for both SQLite and MySQL.
    """
    try:
        is_db_query, response = classify_query(user_query, schema)
        
        if not is_db_query:
            return {
                "summary": response,
                "sql_query": None,
                "visualization": None,
                "follow_up_questions": [
                    "Would you like to know more about pricing strategies?",
                    "Should we discuss other factors that affect product pricing?",
                    "Would you like to explore related business insights?"
                ]
            }

        # Continue with normal query processing
        refined_query = refine_query(user_query, schema)
        if refined_query:
            sql_query = generate_sql(refined_query, schema)
            if not sql_query:
                return {"summary": "Failed to generate SQL query. Please try rephrasing your question."}
            
            results, columns = execute_sql(sql_query, connection)
            print(f"Results: {results}")
            if results is not None:
                df = pd.DataFrame(results, columns=columns)
                
                # Updated numeric conversion logic
                for col in df.columns:
                    try:
                        # Try converting to numeric, if fails keep original
                        numeric_series = pd.to_numeric(df[col])
                        df[col] = numeric_series
                    except (ValueError, TypeError):
                        # Column can't be converted to numeric, skip it
                        continue
                
                # Get numeric and categorical columns
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
                categorical_cols = df.select_dtypes(exclude=['int64', 'float64']).columns.tolist()
                
                # Get summary and follow-up questions
                summary = summarize_results(sql_query, results, columns)
                follow_up_questions = generate_follow_up_questions(user_query, schema)
                
                # Ensure numeric and categorical columns are properly identified
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                # Default to first column if no categorical columns
                default_x = categorical_cols[0] if categorical_cols else columns[0]
                default_y = numeric_cols[0] if numeric_cols else columns[0]
                
                # Prepare visualization data
                viz_data = {
                    "data": df.to_dict('records'),
                    "columns": columns,
                    "numeric_columns": numeric_cols,
                    "categorical_columns": categorical_cols,
                    "default_settings": {
                        "chart_type": "bar",
                        "x_col": default_x,
                        "y_col": default_y
                    }
                }
                
                return {
                    "sql_query": sql_query,
                    "summary": summary,
                    "visualization": viz_data,
                    "follow_up_questions": follow_up_questions,
                    "results": results,
                    "columns": columns
                }
            else:
                return {"summary": "No results found for this query."}
    except Exception as e:
        print(f"Error in process_query: {str(e)}")  # Add debug print
        return {
            "summary": f"An error occurred while processing your query: {str(e)}",
            "sql_query": None,
            "visualization": None,
            "follow_up_questions": None
        }



def process_query(user_query, db_path, schema):
    """Enhanced process_query with more natural non-DB responses"""
    try:
        is_db_query, response = classify_query(user_query, schema)
        
        if not is_db_query:
            return {
                "summary": response,
                "sql_query": None,
                "visualization": None,
                "follow_up_questions": [
                    "Would you like to know more about pricing strategies?",
                    "Should we discuss other factors that affect product pricing?",
                    "Would you like to explore related business insights?"
                ]
            }

        # Continue with normal query processing
        refined_query = refine_query(user_query, schema)
        if refined_query:
            sql_query = generate_sql(refined_query, schema)
            if not sql_query:
                return {"summary": "Failed to generate SQL query. Please try rephrasing your question."}
            
            results, columns = execute_sqlite(sql_query, db_path)
            if results is not None:
                df = pd.DataFrame(results, columns=columns)
                
                # Updated numeric conversion logic
                for col in df.columns:
                    try:
                        # Try converting to numeric, if fails keep original
                        numeric_series = pd.to_numeric(df[col])
                        df[col] = numeric_series
                    except (ValueError, TypeError):
                        # Column can't be converted to numeric, skip it
                        continue
                
                # Get numeric and categorical columns
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
                categorical_cols = df.select_dtypes(exclude=['int64', 'float64']).columns.tolist()
                
                # Get summary and follow-up questions
                summary = summarize_results(sql_query, results, columns)
                follow_up_questions = generate_follow_up_questions(user_query, schema)
                
                # Ensure numeric and categorical columns are properly identified
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                # Default to first column if no categorical columns
                default_x = categorical_cols[0] if categorical_cols else columns[0]
                default_y = numeric_cols[0] if numeric_cols else columns[0]
                
                # Prepare visualization data
                viz_data = {
                    "data": df.to_dict('records'),
                    "columns": columns,
                    "numeric_columns": numeric_cols,
                    "categorical_columns": categorical_cols,
                    "default_settings": {
                        "chart_type": "bar",
                        "x_col": default_x,
                        "y_col": default_y
                    }
                }
                
                return {
                    "sql_query": sql_query,
                    "summary": summary,
                    "visualization": viz_data,
                    "follow_up_questions": follow_up_questions,
                    "results": results,
                    "columns": columns
                }
            else:
                return {"summary": "No results found for this query."}
    except Exception as e:
        print(f"Error in process_query: {str(e)}")  # Add debug print
        return {
            "summary": f"An error occurred while processing your query: {str(e)}",
            "sql_query": None,
            "visualization": None,
            "follow_up_questions": None
        }

def summarize_results(sql_query, results, columns):
    """
    Generate a natural language summary of the SQL query results.
    """
    if not results:
        return "No results found for this query."
    
    try:
        summary_prompt = f"""
        As a data insights specialist, analyze these SQL query results:

        Query: {sql_query}
        Results (First 5): {results[:5]}
        Columns: {columns}

        Provide a concise summary that:
        1. Highlights key findings and patterns
        2. Mentions specific numbers and trends
        3. Compares relevant metrics
        4. Provides business context
        5. Notes any interesting correlations

        Style Guide:
        - Use business-friendly language
        - Include specific metrics and percentages
        - Highlight top performers or significant patterns
        - Mention any unusual or noteworthy data points
        - Keep it concise but informative (2-3 sentences)

        Focus on actionable insights rather than just describing the data.
        """

        return llm.generate_completion(summary_prompt, temperature=0.3)
    except Exception as e:
        return f"Error generating summary: {str(e)}"
