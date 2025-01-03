import os
import openai
from dotenv import load_dotenv

def test_api_connection():
    # Load environment variables
    load_dotenv()
    
    # Get and print the API key (first few characters)
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API Key starts with: {api_key[:10]}...")
    
    # Set the API key
    openai.api_key = api_key
    
    try:
        # Test the API with a simple completion
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Say 'API is working!'"}
            ]
        )
        print("API Response:", response.choices[0].message.content)
        print("API connection successful!")
        return True
    except Exception as e:
        print("API Error:", str(e))
        return False

if __name__ == "__main__":
    test_api_connection()
