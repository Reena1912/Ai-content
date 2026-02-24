# RepurposeAI 🚀

An AI-powered content repurposing tool that transforms long-form articles into platform-ready content for Twitter, LinkedIn, Instagram, Newsletter, and Medium — in seconds.

---

## What It Does

Paste any article or blog post, pick a platform, and the AI generates perfectly formatted content tailored to that platform's style, tone, and format. Every generation is saved permanently to a PostgreSQL database.

# Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL installed and running
- Groq API key → [console.groq.com](https://console.groq.com)

---

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/repurposeai.git
cd repurposeai
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn groq psycopg2-binary python-dotenv
```

### 4. Set up PostgreSQL

Create a database:
```sql
CREATE DATABASE repurposeai;
```

### 5. Configure environment variables

Create a `.env` file in the root folder:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://postgres:yourpassword@localhost/repurposeai
```

### 6. Run the backend

```bash
uvicorn main:app --reload
```

You should see:
```
✅ Database table ready.
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 7. Open the frontend

Open `index.html` in your browser directly, or use the VS Code **Live Server** extension.
