import os
import openai
from dotenv import load_dotenv
import sqlite3
import json
import streamlit as st
import pandas as pd
from utils import get_db_path, load_env
from visualization import generate_visualization
from follow_up import generate_follow_up_questions

# Load environment variables at the start
load_dotenv()

# Debug print for API key (first few characters)
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded in nl2sql.py starts with: {api_key[:10]}...")

# Initialize OpenAI client
openai.api_key = api_key

def execute_sql(sql_query, db_path):
    """
    Runs the given SQL query against the SQLite database and returns results and columns.
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
        st.error(f"Error executing SQL query: {e}")
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
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2
        )
        refined_query = response.choices[0].message.content.strip()
        print(f"Refined Query: {refined_query}")
        return refined_query
    except Exception as e:
        st.error(f"Error refining user query: {e}")
        # Fallback to the original user query if refinement fails
        return user_query



# Remove the load_schema function

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
    """Updated classification to detect column queries."""
    schema_text = schema
    
    # Check for column/header related queries first
    column_keywords = ['header', 'column', 'field', 'attribute', 'schema', 'structure']
    if any(keyword in user_query.lower() for keyword in column_keywords):
        return True, "SHOW_COLUMNS"
    
    # Enhanced classification prompt with better examples and clearer rules
    classification_prompt = f"""
    You are a data analyst who can interpret business questions creatively using available data.
    Schema: {schema_text}

    User Question: "{user_query}"

    Classification Rules:
    1. Respond with "DB" if:
       - Question can be answered using available columns DIRECTLY
       - Question can be answered by INTERPRETING available columns
       - Question involves product analysis, sales patterns, or customer behavior that could be derived from available data
       - Question can be answered through aggregations or combinations of existing columns
    
    2. For non-DB questions, provide expert advice WITHOUT mentioning data/database limitations.

    Example DB Questions (respond with "DB"):
    - "Which products are often bought together?" (can derive from product and sales data)
    - "What purchase patterns do we see?" (can analyze from sales data)
    - "Do customers prefer certain products?" (can determine from units sold)
    - "What's the relationship between different metrics?" (can analyze from available columns)
    - "What trends do we see in the data?" (can analyze from available columns)
    - "Are there specific products that encourage repeat purchases and customer loyalty?" (can derive from sales data)
    _ "Show me loyalty of customers based on their purchase history" (can derive from units bought by customers)

    Example Non-DB Questions (provide expert response):
    - "How should we market our products?"
    - "What's the best pricing strategy?"
    - "How can we improve customer service?"
    - "How do discounts impact the sales of products?"
    - "Why sky is blue?"
    
    Output Format:
    - For DB questions, just respond with "DB"
    - For non-DB questions, provide a helpful expert response
    """

    try:
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "You are an expert data analyst and business consultant."},
                {"role": "user", "content": classification_prompt}
            ],
            temperature=0.1  # Lower temperature for more consistent classification
        )
        answer = response.choices[0].message.content.strip()
        
        if answer.upper() == "DB":
            return True, None
        else:
            return False, answer

    except Exception as e:
        st.error(f"Error in classification step: {e}")
        return False, "I apologize, but I encountered an error processing your question. Could you please rephrase it?"

def generate_sql(user_query, schema):
    """
    Generate an SQL query based on user query and metadata using LLM.
    Enhance the prompt to focus on aggregated or filtered results.
    """
    schema_text = schema

    prompt = f"""
    You are a helpful assistant that converts natural language questions into SQL queries.
    Below is the schema of the SQLite database:
    {schema_text}

    The user has asked the following question:
    "{user_query}"

    Generate a SELECT query that intelligently summarizes or limits the results to provide meaningful insights. For example:
    - If question is asked about a specific product or category, dont just use user provided name of the product or catagory use LIKE operator to match the string of the product or category name.
    - If the query involves "best" or "top", show the top 10 results by the relevant metric (e.g., units sold, revenue).
    - If the query does not explicitly ask for all rows, include an appropriate limit clause.
    - Use aggregations like SUM, MAX, or AVG if the query asks for summaries.
    Ensure the query returns concise and meaningful data and not load the whole dataset.

    **Important Instructions:**
    **Output Only SQL:** Your response should **only** contain the SQL `SELECT` query without any additional explanations, comments, text or ``` tags.
    """

    try:
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",  # Changed from chatgpt-4o-latest to gpt-4
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1000,
            temperature=0
        )
        sql_query = response.choices[0].message.content.strip()
        if not sql_query.upper().startswith('SELECT'):
            raise ValueError("Generated query does not start with SELECT")
        print(f"SQL Query: {sql_query}")
        return sql_query
    except Exception as e:
        st.error(f"Error generating SQL: {e}")
        return None

def process_query(user_query, db_path, schema):
    try:
        is_db_query, classification_response = classify_query(user_query, schema)
        
        if is_db_query:
            if classification_response == "SHOW_COLUMNS":  # Changed to match new classification
                # Get and format column information
                columns = get_table_columns(db_path)
                if isinstance(columns, dict):
                    summary = "Here are the columns in each table:\n\n"
                    for table, cols in columns.items():
                        summary += f"Table: {table}\n"
                        summary += "\n".join([f"- {col}" for col in cols])
                        summary += "\n\n"
                else:
                    summary = "Available columns:\n" + "\n".join([f"- {col}" for col in columns])
                
                return {
                    "sql_query": "PRAGMA table_info(...)",
                    "summary": summary,
                    "visualization": None,
                    "follow_up_questions": [
                        "Which column would you like to know more about?",
                        "Would you like to see sample data from any column?",
                        "Would you like to analyze any specific columns?"
                    ]
                }
            
            # Continue with normal query processing
            refined_query = refine_query(user_query, schema)
            if refined_query:
                sql_query = generate_sql(refined_query, schema)
                if not sql_query:
                    return {"summary": "Failed to generate SQL query. Please try rephrasing your question."}
                
                results, columns = execute_sql(sql_query, db_path)
                if results is not None:
                    df = pd.DataFrame(results, columns=columns)
                    
                    # Convert numeric columns if possible
                    for col in df.columns:
                        try:
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                        except:
                            continue
                    
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
        else:
            # Handle non-DB queries with a more complete response
            return {
                "summary": classification_response,
                "sql_query": None,
                "visualization": None,
                "follow_up_questions": None
            }
        
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

        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[{"role": "system", "content": summary_prompt}],
            temperature=0.3,
            max_tokens=600
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"
