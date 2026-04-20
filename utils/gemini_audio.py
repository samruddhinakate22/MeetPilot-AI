"""
Gemini API Audio Transcription Utility
Uploads audio to Gemini, prompts for transcription, and returns transcript text.
"""
import os
import time
from typing import Dict, Any
from flask import current_app
from google import genai
from google.genai import types

def get_api_key() -> str:
    """Retrieve Gemini API key from environment or config."""
    key = os.getenv('GEMINI_API_KEY')
    if not key and current_app:
        key = current_app.config.get('GEMINI_API_KEY')
    return key or ""

def is_configured() -> bool:
    """Check if Gemini API is configured."""
    return bool(get_api_key().strip())

def transcribe_audio_file(file_path: str) -> Dict[str, Any]:
    """
    Transcribe audio using Gemini.
    Returns dict with keys: transcript, highlights, duration_seconds, duration_minutes, word_count
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    
    print(f"📤 Uploading audio to Gemini: {os.path.basename(file_path)}")
    uploaded_file = client.files.upload(file=file_path)
    
    try:
        # Wait a moment for processing to complete if necessary
        time.sleep(2)
        
        prompt = (
            "Please fully transcribe this audio file. "
            "If there are multiple speakers, try to diarize by grouping their speech and prefixing with 'Speaker A:', 'Speaker B:', etc. "
            "Output ONLY the exact transcript text. Do not add markdown formatting, extra comments, or formatting around it."
        )

        print("🔄 Generating transcript with Gemini...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.2,
            )
        )
        
        transcript = response.text.strip() if response.text else ""
        
    finally:
        # Try to delete the uploaded file after processing
        try:
            client.files.delete(name=uploaded_file.name)
            print("🗑️ Cleaned up file from Gemini.")
        except Exception as e:
            print(f"⚠️ Failed to delete Gemini file {uploaded_file.name}: {e}")

    # Fallback duration calculation (Gemini doesn't provide precise duration easily, so we just use 0)
    duration = 0
    words = len(transcript.split())

    print(f"✅ Gemini Transcription complete! {words} words")

    return {
        "transcript": transcript,
        "highlights": [],
        "duration_seconds": duration,
        "duration_minutes": 0,
        "word_count": words,
    }
