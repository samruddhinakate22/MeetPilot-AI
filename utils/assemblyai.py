"""
AssemblyAI Audio Transcription Utility
Uploads audio, polls for completion, returns transcript text.
Docs: https://www.assemblyai.com/docs
"""
import requests
import time
import os
from flask import current_app

ASSEMBLYAI_BASE = "https://api.assemblyai.com/v2"


def _headers():
    api_key = current_app.config.get('ASSEMBLYAI_API_KEY', '')
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY not set in .env file")
    return {"authorization": api_key, "content-type": "application/json"}


def upload_audio(file_path: str) -> str:
    """Upload a local audio file to AssemblyAI and return its hosted URL."""
    api_key = current_app.config.get('ASSEMBLYAI_API_KEY', '')
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY not set in .env file")

    headers = {"authorization": api_key}
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{ASSEMBLYAI_BASE}/upload",
            headers=headers,
            data=f,
            timeout=120
        )
    response.raise_for_status()
    return response.json()["upload_url"]


def submit_transcription(audio_url: str, speaker_labels: bool = True) -> str:
    """Submit a transcription job and return the transcript ID."""
    payload = {
        "audio_url": audio_url,
        "speaker_labels": speaker_labels,      # detect who is speaking
        "auto_highlights": True,               # extract key phrases
        "punctuate": True,
        "format_text": True,
    }
    response = requests.post(
        f"{ASSEMBLYAI_BASE}/transcript",
        json=payload,
        headers=_headers(),
        timeout=30
    )
    response.raise_for_status()
    return response.json()["id"]


def poll_transcription(transcript_id: str, max_wait: int = 300) -> dict:
    """
    Poll until transcription is complete.
    Returns the full result dict.
    Raises TimeoutError if it takes longer than max_wait seconds.
    """
    url = f"{ASSEMBLYAI_BASE}/transcript/{transcript_id}"
    waited = 0
    interval = 5

    while waited < max_wait:
        response = requests.get(url, headers=_headers(), timeout=30)
        response.raise_for_status()
        result = response.json()

        status = result.get("status")
        if status == "completed":
            return result
        elif status == "error":
            raise RuntimeError(f"AssemblyAI transcription error: {result.get('error')}")

        time.sleep(interval)
        waited += interval

    raise TimeoutError(f"Transcription timed out after {max_wait}s")


def format_transcript_with_speakers(result: dict) -> str:
    """
    Convert AssemblyAI result into a readable Speaker: text format.
    Falls back to plain text if no speaker data available.
    """
    utterances = result.get("utterances")
    if utterances:
        lines = []
        for utt in utterances:
            speaker = f"Speaker {utt['speaker']}"
            text    = utt["text"].strip()
            lines.append(f"{speaker}: {text}")
        return "\n\n".join(lines)

    # Fallback — plain transcript text
    return result.get("text", "")


def get_auto_highlights(result: dict) -> list:
    """Extract automatically highlighted key phrases from the result."""
    highlights = result.get("auto_highlights_result") or {}
    results    = highlights.get("results", [])
    return [h["text"] for h in sorted(results, key=lambda x: x.get("rank", 0), reverse=True)[:15]]


def transcribe_audio_file(file_path: str) -> dict:
    """
    Full pipeline: upload → submit → poll → format.
    Returns dict with keys: transcript, highlights, duration_seconds
    """
    print(f"📤 Uploading audio: {os.path.basename(file_path)}")
    audio_url = upload_audio(file_path)

    print("🔄 Submitting transcription job...")
    transcript_id = submit_transcription(audio_url)

    print(f"⏳ Waiting for transcription (ID: {transcript_id})...")
    result = poll_transcription(transcript_id)

    transcript = format_transcript_with_speakers(result)
    highlights = get_auto_highlights(result)
    duration   = result.get("audio_duration", 0)

    print(f"✅ Transcription complete! {len(transcript.split())} words, {duration}s audio")

    return {
        "transcript":        transcript,
        "highlights":        highlights,
        "duration_seconds":  duration,
        "duration_minutes":  round(duration / 60, 1) if duration else 0,
        "word_count":        len(transcript.split()),
    }


def is_configured() -> bool:
    """Check if AssemblyAI API key is set."""
    return bool(current_app.config.get('ASSEMBLYAI_API_KEY', '').strip())
