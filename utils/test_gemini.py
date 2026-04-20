import os
from google import genai
from google.genai import types

def test():
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        print("No KEY in env, loading from .env")
        from dotenv import load_dotenv
        load_dotenv('.env')
        key = os.getenv('GEMINI_API_KEY')

    client = genai.Client(api_key=key)
    print("Files API available?", hasattr(client, "files"))

if __name__ == "__main__":
    test()
