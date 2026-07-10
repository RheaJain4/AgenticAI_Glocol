import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Create Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate_text(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return ""

def generate_json(prompt: str, schema: dict) -> str:
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"Gemini Error (JSON Mode): {e}")
        return ""