import openai
import os
import streamlit as st
from utils import load_env

load_env()

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_follow_up_questions(user_query, schema):
    """Generate relevant follow-up questions based on the current query."""
    try:
        prompt = f"""
        Based on this user query and database schema, suggest 3 relevant follow-up questions.
        
        User Query: {user_query}
        Schema: {schema}
        
        Rules:
        1. Questions should be related to the data available in the schema
        2. Questions should build upon the current query
        3. Keep questions concise and business-focused
        4. Avoid technical SQL terms
        
        Format: Return only the questions, one per line.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        # Split the response into individual questions
        questions = response.choices[0].message.content.strip().split('\n')
        # Remove any empty questions and limit to 3
        questions = [q.strip() for q in questions if q.strip()][:3]
        
        return questions
    except Exception as e:
        print(f"Error generating follow-up questions: {e}")
        return []
