import google.generativeai as genai
import os
from dotenv import load_dotenv
import sys

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"DEBUG: Key found? {'Yes' if api_key else 'No'}")

if not api_key:
    # Try to find it in .env manually if load_dotenv fails or just warn
    print("No API key found in env")
else:
    genai.configure(api_key=api_key)
    print("Listing available models:")
    try:
        found = False
        for m in genai.list_models():
            found = True
            # print(f"Model: {m.name} | Methods: {m.supported_generation_methods}")
            if 'generateContent' in m.supported_generation_methods:
                print(f"AVAILABLE: {m.name}")
        if not found:
            print("No models returned by list_models()")
    except Exception as e:
        print(f"Error listing models: {e}")
