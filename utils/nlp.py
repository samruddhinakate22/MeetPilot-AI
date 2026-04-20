"""
NLP Utilities for Meeting Analysis
Uses rule-based NLP (no heavy ML models required) for fast, reliable processing.
Falls back gracefully if optional libraries are unavailable.
"""
import re
import string
import os
from collections import Counter
from pydantic import BaseModel, Field
from typing import List, Optional
from flask import current_app

class TaskExtract(BaseModel):
    description: str = Field(description="Accurate and complete description of the task based on the conversation.")
    assigned_name: Optional[str] = Field(description="The name of the user this task is assigned to.")
    assigned_email: Optional[str] = Field(description="The email of the user assigned directly matching the users list.")
    deadline_hint: Optional[str] = Field(description="Any time hint for the deadline, e.g., 'next Friday', 'tomorrow'.")

class MeetingExtract(BaseModel):
    summary: str = Field(description="A concise summary of what was discussed in the meeting.")
    key_points: str = Field(description="Bullet points of the main ideas and topics discussed, using '-' prefixes. Ensure it is formatted as markdown bullets.")
    decisions: str = Field(description="Numbered list of decisions made during the meeting. E.g. '1. We decided to...\\n2. We agreed to...'")
    keywords: List[str] = Field(description="A list of 5-10 keywords summarizing the meeting's topics.")
    tasks: List[TaskExtract] = Field(description="List of actionable tasks and their assignees based on the speakers' roles and context.")



# ─── Simple sentence tokenizer (no NLTK dependency required) ──────────────────
def sent_tokenize(text):
    text = text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


# ─── Stop words ───────────────────────────────────────────────────────────────
STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can',
    'need', 'dare', 'ought', 'used', 'i', 'we', 'you', 'he', 'she', 'it',
    'they', 'me', 'us', 'him', 'her', 'them', 'my', 'our', 'your', 'his',
    'their', 'this', 'that', 'these', 'those', 'what', 'which', 'who',
    'whom', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'just', 'don',
    'about', 'also', 'well', 'get', 'let', 'good', 'think', 'know', 'go',
    'make', 'see', 'come', 'take', 'want', 'look', 'use', 'find', 'give',
    'tell', 'keep', 'work', 'call', 'try', 'ask', 'seem', 'feel', 'leave',
    'put', 'mean', 'become', 'show', 'start', 'time', 'now', 'then'
}

# ─── Task keywords ─────────────────────────────────────────────────────────────
TASK_INDICATORS = [
    r'\b(will|shall|going to|need to|must|should|have to|supposed to)\s+([\w\s]+)',
    r'\b(please|make sure|ensure|confirm|verify)\b',
    r'\baction item[s]?\b',
    r'\b(by|before|until|due)\s+\w+\s+\d+',
    r'\b(complete|finish|send|prepare|create|build|develop|review|update|schedule|arrange|coordinate|handle|resolve|fix|address|deliver|submit|present|write|design|test|deploy|launch|implement|investigate|analyze|check|contact|follow\s*up)\b',
]

TASK_PATTERN = re.compile(
    r'(?i)(' +
    r'(?:will|shall|going to|need to|must|should|have to)\s+\w[\w\s,]+|' +
    r'(?:please|make sure|ensure)\s+\w[\w\s,]+|' +
    r'(?:i\'ll|he\'ll|she\'ll|they\'ll|we\'ll)\s+\w[\w\s,]+|' +
    r'action item[s]?[:\s]+\w[\w\s,]+'
    r')'
)

# ─── Public API ────────────────────────────────────────────────────────────────

def analyze_meeting(transcript: str, users: list = None) -> dict:
    """Full meeting analysis pipeline, using Gemini LLM if available."""
    if not transcript or not transcript.strip():
        return _empty_result()

    clean = _clean_text(transcript)
    sentences = sent_tokenize(clean)
    speakers, speaker_map = _extract_speakers(transcript)
    
    # Try using Gemini API if configured
    gemini_key = os.getenv('GEMINI_API_KEY') or (current_app and current_app.config.get('GEMINI_API_KEY'))
    if gemini_key:
        try:
            return _analyze_with_gemini(transcript, users, gemini_key, sentences, clean)
        except Exception as e:
            print(f"⚠️ Gemini analysis failed, falling back to basic NLP: {e}")

    keywords = extract_keywords(clean, top_n=15)
    summary = generate_summary(sentences, keywords, max_sentences=5)
    key_points = extract_key_points(sentences, speakers)
    decisions = extract_decisions(sentences)
    tasks = extract_tasks(transcript, speakers)

    return {
        'summary': summary,
        'key_points': key_points,
        'decisions': decisions,
        'keywords': ', '.join(keywords[:10]),
        'tasks': tasks,
        'speakers': speakers,
        'word_count': len(clean.split()),
        'sentence_count': len(sentences),
    }


def _analyze_with_gemini(transcript: str, users: list, api_key: str, sentences: list, clean: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    
    users_context = "Available Users in the system (use this to figure out who 'Speaker A' might be based on role and tasks):\n"
    if users:
        for u in users:
            users_context += f"- Name: {u.name}, Email: {u.email}, Role: {u.role}\n"
    else:
        users_context += "No predefined users provided.\n"

    prompt = f"""
You are an intelligent assistant that analyzes meeting transcripts to generate concise summaries, decisions, and tasks.
Carefully review the transcript. Try to deduce which 'Speaker' corresponds to which user from the "Available Users" based on their roles, discussion, and names mentioned contextually. 
If someone says "Alice, can you check the server", clearly the person responding is likely Alice, and the task belongs to her.

{users_context}

Meeting Transcript:
{transcript}
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MeetingExtract,
            temperature=0.2,
        ),
    )
    
    import json
    data = json.loads(response.text)
    
    return {
        'summary': data.get('summary', ''),
        'key_points': data.get('key_points', ''),
        'decisions': data.get('decisions', ''),
        'keywords': ', '.join(data.get('keywords', [])),
        'tasks': data.get('tasks', []),
        'speakers': list(_extract_speakers(transcript)[0]),
        'word_count': len(clean.split()),
        'sentence_count': len(sentences),
    }


def generate_summary(sentences: list, keywords: list = None, max_sentences: int = 5) -> str:
    """Extractive summarization using TF-IDF-like scoring."""
    if not sentences:
        return ''
    if len(sentences) <= max_sentences:
        return ' '.join(sentences)

    keyword_set = set(keywords or [])
    scores = {}

    for i, sent in enumerate(sentences):
        words = _tokenize_words(sent.lower())
        if not words:
            continue

        # TF score
        tf = sum(1 for w in words if w in keyword_set) / max(len(words), 1)
        # Position score (first and last sentences matter more)
        pos = 1.0 if i == 0 else (0.8 if i == len(sentences) - 1 else 0.5)
        # Length penalty (prefer medium-length sentences)
        length_score = min(len(words) / 20, 1.0)

        scores[i] = tf * 0.5 + pos * 0.3 + length_score * 0.2

    top_indices = sorted(scores, key=scores.get, reverse=True)[:max_sentences]
    top_indices.sort()  # maintain original order
    selected = [sentences[i] for i in top_indices]
    return ' '.join(selected)


def extract_keywords(text: str, top_n: int = 10) -> list:
    """Extract keywords using frequency + position scoring."""
    words = _tokenize_words(text.lower())
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 3]

    freq = Counter(filtered)

    # Boost words appearing in first 20% of text
    total = len(words)
    early_text = ' '.join(words[:total // 5])
    early_words = set(_tokenize_words(early_text))

    scored = {w: freq[w] * (1.5 if w in early_words else 1.0) for w in freq}
    top = sorted(scored, key=scored.get, reverse=True)[:top_n]
    return top


def extract_key_points(sentences: list, speakers: list = None) -> str:
    """Extract important discussion points."""
    indicators = [
        r'\b(important|critical|key|main|major|significant|essential|crucial|priority|focus)\b',
        r'\b(decided|agreed|confirmed|noted|highlighted|mentioned|discussed|raised)\b',
        r'\b(issue|problem|concern|challenge|opportunity|goal|objective|target)\b',
        r'\b(increase|decrease|improve|reduce|achieve|deliver|complete|launch)\b',
        r'\b\d+\s*%|\$\s*\d+|\d+\s*(million|billion|thousand|k)\b',
    ]
    pattern = re.compile('|'.join(indicators), re.IGNORECASE)

    scored = []
    for sent in sentences:
        if len(sent.split()) < 5:
            continue
        matches = len(pattern.findall(sent))
        if matches > 0:
            scored.append((matches, sent))

    scored.sort(reverse=True)
    top = [s for _, s in scored[:8]]

    # Format as bullet points
    points = []
    for s in top:
        s = re.sub(r'^[^:]+:\s*', '', s)  # remove "Speaker: " prefix
        if s:
            points.append(f'- {s.strip()}')

    return '\n'.join(points) if points else '- Meeting discussion recorded'


def extract_decisions(sentences: list) -> str:
    """Extract decisions made during the meeting."""
    decision_patterns = re.compile(
        r'(?i)\b('
        r'decided|agreed|confirmed|concluded|resolved|approved|'
        r'will\s+\w+\s+by|deadline|due\s+(?:by|date)|'
        r'scheduled for|set for|target is|goal is|plan is'
        r')\b'
    )

    decisions = []
    for sent in sentences:
        if decision_patterns.search(sent):
            clean = re.sub(r'^[^:]+:\s*', '', sent)
            if clean and len(clean.split()) >= 5:
                decisions.append(clean.strip())

    if not decisions:
        return '1. No explicit decisions recorded'

    return '\n'.join(f'{i+1}. {d}' for i, d in enumerate(decisions[:6]))


def extract_tasks(transcript: str, speakers: list = None) -> list:
    """Extract actionable tasks with assignees."""
    lines = transcript.split('\n')
    tasks = []
    seen = set()

    action_verbs = re.compile(
        r'(?i)\b('
        r'will\s+(?:send|create|prepare|build|develop|design|write|review|'
        r'update|schedule|fix|resolve|complete|finish|handle|coordinate|'
        r'submit|present|test|deploy|launch|investigate|analyze|check|contact|'
        r'follow\s*up|provide|ensure|confirm|make|deliver|implement|set\s*up)'
        r'|(?:please|make sure|ensure|need to|must|should)\s+\w+'
        r'|(?:i\'ll|he\'ll|she\'ll|they\'ll|we\'ll)\s+\w+'
        r')\b'
    )

    deadline_pat = re.compile(
        r'(?i)by\s+(?:end of\s+)?(?:(?:next\s+)?(?:week|month|monday|tuesday|wednesday|thursday|friday)|'
        r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}|'
        r'\d{1,2}(?:st|nd|rd|th)?(?:\s+of\s+\w+)?)',
        re.IGNORECASE
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract speaker
        speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$', line)
        speaker_name = speaker_match.group(1).strip() if speaker_match else None
        content = speaker_match.group(2).strip() if speaker_match else line

        if not action_verbs.search(content):
            continue

        # Clean up task description
        task_desc = re.sub(r'^(i\'ll|i will|i must|i should|i need to)\s+', '', content, flags=re.IGNORECASE)
        task_desc = task_desc.strip().rstrip('.')

        # De-duplicate
        key = task_desc.lower()[:60]
        if key in seen or len(task_desc.split()) < 4:
            continue
        seen.add(key)

        # Extract deadline hint
        deadline_hint = None
        dm = deadline_pat.search(content)
        if dm:
            deadline_hint = dm.group(0)

        tasks.append({
            'description': task_desc[:200],
            'assigned_name': speaker_name,
            'deadline_hint': deadline_hint,
        })

    return tasks[:15]  # cap at 15 tasks


def extract_names_from_text(text: str) -> list:
    """Simple name extraction using capitalization patterns."""
    name_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
    candidates = name_pattern.findall(text)

    # Filter common false positives
    non_names = {'January', 'February', 'March', 'April', 'Monday', 'Tuesday',
                 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                 'New York', 'United States', 'North America', 'South America'}

    names = [n for n in set(candidates) if n not in non_names]
    return names


# ─── Internal helpers ──────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r'^[A-Za-z][A-Za-z\s]+:\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _tokenize_words(text: str) -> list:
    return re.findall(r'\b[a-z][a-z\-]*[a-z]\b', text.lower())


def _extract_speakers(transcript: str):
    lines = transcript.split('\n')
    speakers = []
    speaker_map = {}
    for line in lines:
        m = re.match(r'^([A-Za-z][A-Za-z\s]{1,30}):\s*', line)
        if m:
            name = m.group(1).strip()
            if name not in speaker_map:
                speaker_map[name] = []
                speakers.append(name)
    return speakers, speaker_map


def _empty_result() -> dict:
    return {
        'summary': '',
        'key_points': '',
        'decisions': '',
        'keywords': '',
        'tasks': [],
        'speakers': [],
        'word_count': 0,
        'sentence_count': 0,
    }
