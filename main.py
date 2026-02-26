from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator
from dotenv import load_dotenv
from typing import Literal, Optional
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from groq import Groq
import bcrypt
import re
from jose import jwt, JWTError

# Load environment variables
load_dotenv()

app = FastAPI()
security = HTTPBearer()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# ── Database ──────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    email      TEXT UNIQUE NOT NULL,
                    password   TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Generations table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS generations (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER REFERENCES users(id),
                    platform   TEXT        NOT NULL,
                    input_text TEXT        NOT NULL,
                    output_text TEXT       NOT NULL,
                    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    finally:
        conn.close()


# ── Password Utilities ────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def check_password_strength(password: str) -> dict:
    """Check password strength and return details."""
    checks = {
        "length": len(password) >= 8,
        "uppercase": bool(re.search(r"[A-Z]", password)),
        "lowercase": bool(re.search(r"[a-z]", password)),
        "digit": bool(re.search(r"\d", password)),
        "special": bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)),
    }
    score = sum(checks.values())
    strength = "weak" if score <= 2 else "medium" if score <= 4 else "strong"
    return {"checks": checks, "score": score, "strength": strength}


# ── JWT Utilities ─────────────────────────────────────────────
def create_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        return {"id": user_id, "email": email}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def save_generation(user_id: int, platform: str, input_text: str, output_text: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO generations (user_id, platform, input_text, output_text) VALUES (%s, %s, %s, %s)",
                (user_id, platform, input_text, output_text)
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


# ── Auth Models ──────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str
    password: str

    @validator("email")
    def validate_email(cls, v):
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class PasswordCheck(BaseModel):
    password: str


# ── Auth Endpoints ───────────────────────────────────────────
@app.post("/register")
def register(user: UserRegister):
    strength = check_password_strength(user.password)
    if strength["strength"] == "weak":
        raise HTTPException(status_code=400, detail="Password is too weak")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            # Create user
            hashed = hash_password(user.password)
            cur.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id",
                (user.email, hashed)
            )
            user_id = cur.fetchone()[0]
        conn.commit()
        token = create_token(user_id, user.email)
        return {"token": token, "email": user.email}
    finally:
        conn.close()


@app.post("/login")
def login(user: UserLogin):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password FROM users WHERE email = %s",
                (user.email.lower(),)
            )
            row = cur.fetchone()

            if not row or not verify_password(user.password, row[2]):
                raise HTTPException(status_code=401, detail="Invalid email or password")

            token = create_token(row[0], row[1])

            return {
                "token": token,
                "email": row[1]
            }
    finally:
        conn.close()


@app.post("/check-password")
def check_password(data: PasswordCheck):
    return check_password_strength(data.password)


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
def repurpose_endpoint(request: ArticleRequest, user: dict = Depends(get_current_user)):
    result = repurpose_content(request.article, request.platform)
    save_generation(user["id"], request.platform, request.article, result)
    return {
        "platform": request.platform,
        "repurposed_content": result
    }


@app.get("/history")
def get_history(limit: int = 20, user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, platform, input_text, output_text, created_at
                   FROM generations
                   WHERE user_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (user["id"], limit,)
            )
            rows = cur.fetchall()
        return {"history": [dict(r) for r in rows]}
    finally:
        conn.close()