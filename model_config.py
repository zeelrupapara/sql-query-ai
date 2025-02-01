from dotenv import load_dotenv
import os
import openai
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

class LLMInterface:
    def __init__(self, model_type="google"):
        self.model_type = model_type
        if model_type == "openai":
            openai.api_key = os.getenv("OPENAI_API_KEY")
        elif model_type == "google":
            print("Google gemini model initialized")
            api_key = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            self.generation_config = {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1000,
            }
            self.model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",  # Changed model name
                generation_config=self.generation_config,
            )
            self.safety_settings = [
                {
                    "category": "HARM_CATEGORY_DANGEROUS",
                    "threshold": "BLOCK_NONE",
                },
            ]

    def generate_completion(self, prompt, temperature=0.2):
        try:
            if self.model_type == "openai":
                response = openai.ChatCompletion.create(
                    model="chatgpt-4o-latest",
                    messages=[{"role": "system", "content": prompt}],
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            elif self.model_type == "google":
                print("Google gemini model used")
                try:
                    formatted_prompt = f"""Instructions: {prompt}
                    
Remember:
- Output must be a single complete statement
- No comments or explanations
- No multiple statements
- No semicolons at the end"""
                    
                    response = self.model.generate_content(
                        formatted_prompt,
                        generation_config={"temperature": temperature},
                        safety_settings=self.safety_settings
                    )
                    
                    response_text = response.text.strip()
                    
                    # For SQL queries, ensure proper format and clean semicolons
                    if "Write ONLY the SQL query" in prompt:
                        # Clean up the response
                        if ';' in response_text:
                            response_text = response_text.split(';')[0].strip()
                        
                        if not response_text.upper().startswith('SELECT'):
                            print("Invalid SQL generated, using fallback")
                            return """SELECT Product, COUNT(*) as frequency 
                                     FROM cannabis 
                                     GROUP BY Product 
                                     ORDER BY frequency DESC 
                                     LIMIT 5"""
                        
                        return response_text
                    
                    return response_text
                    
                except Exception as e:
                    print(f"Gemini Error: {str(e)}")
                    raise e
                    
        except Exception as e:
            raise Exception(f"Error generating completion: {str(e)}")
