from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Literal
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from groq import Groq

# Load environment variables
load_dotenv()

app = FastAPI()


# ── Database ──────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def init_db():
    """Create the generations table if it doesn't exist."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS generations (
                    id         SERIAL PRIMARY KEY,
                    platform   TEXT        NOT NULL,
                    input_text TEXT        NOT NULL,
                    output_text TEXT       NOT NULL,
                    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    finally:
        conn.close()


def save_generation(platform: str, input_text: str, output_text: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO generations (platform, input_text, output_text) VALUES (%s, %s, %s)",
                (platform, input_text, output_text)
            )
        conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def startup():
    init_db()
  

#allows the HTML file to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get Groq API key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env file")

# Create Groq client
client = Groq(api_key=api_key)


# ── Platform Prompts ─────────────────────────────────────────
PLATFORM_PROMPTS = {
    "twitter": """
You are a viral Twitter/X content expert.
Convert the article into a punchy 5-tweet thread.
- Start with a hook tweet that grabs attention immediately
- Each tweet must be under 280 characters
- Label each tweet: Tweet 1:, Tweet 2:, etc.
- End with a call-to-action tweet
- Add relevant hashtags
""",
    "linkedin": """
You are a professional LinkedIn content strategist.
Convert the article into a LinkedIn post.
- Start with a bold first line that stops the scroll
- Use short paragraphs (2-3 lines max)
- Add 3-5 key takeaways using bullet points
- End with a thought-provoking question
- Keep it between 150-300 words
""",
    "instagram": """
You are an Instagram caption expert.
Convert the article into an engaging Instagram caption.
- Hook in the first line
- Storytelling style, personal and relatable
- Add a clear call-to-action at the end
- Suggest 10 relevant hashtags at the bottom
- Keep caption under 200 words
""",
    "newsletter": """
You are an email newsletter writer.
Convert the article into a short newsletter section.
- Write a catchy subject line first (label it: Subject:)
- Conversational, friendly tone
- Summarize the core idea in 3 short paragraphs
- Add one actionable tip the reader can use today
- End with a 1-sentence teaser for next week
""",
    "medium": """
You are a Medium blog writer.
Convert the article into a well-structured Medium post.
- Write a compelling title (label it: Title:)
- Start with a strong opening paragraph that draws the reader in
- Use clear subheadings to break up sections
- Write in a thoughtful, conversational tone
- Include real examples or analogies to explain key points
- End with a powerful conclusion and a question for readers
- Aim for 400-600 words
"""
}


# ── Request Model ─────────────────────────────────────────────
class ArticleRequest(BaseModel):
    article: str
    platform: Literal["twitter", "linkedin", "instagram", "newsletter", "medium"] = "twitter"


@app.get("/")
def root():
    return {"message": "API running 🚀"}


def repurpose_content(article: str, platform: str):

    # Pick the right prompt based on platform
    instructions = PLATFORM_PROMPTS[platform]

    prompt = instructions + "\n\nARTICLE:\n" + article

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repurpose")
def repurpose_endpoint(request: ArticleRequest):
    result = repurpose_content(request.article, request.platform)
    save_generation(request.platform, request.article, result)
    return {
        "platform": request.platform,
        "repurposed_content": result
    }


@app.get("/history")
def get_history(limit: int = 20):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, platform, input_text, output_text, created_at
                   FROM generations
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (limit,)
            )
            rows = cur.fetchall()
        return {"history": [dict(r) for r in rows]}
    finally:
        conn.close()