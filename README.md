# RepurposeAI 🚀

An AI-powered content repurposing tool that transforms long-form articles into platform-ready content for Twitter, LinkedIn, Instagram, Newsletter, and Medium — in seconds.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-purple)

---

## Features

- **Multi-Platform Support** — Generate content optimized for Twitter, LinkedIn, Instagram, Newsletter, and Medium
- **AI-Powered** — Uses Groq's LLaMA 3.3 70B for fast, high-quality content generation
- **History Tracking** — All generations saved to PostgreSQL database
- **Minimal UI** — Clean, dark-themed frontend with copy-to-clipboard functionality
- **Slide-out History** — View and reload past generations

---

## Tech Stack

| Layer    | Technology               |
| -------- | ------------------------ |
| Frontend | Vanilla HTML/CSS/JS      |
| Backend  | FastAPI (Python)         |
| AI       | Groq API (LLaMA 3.3 70B) |
| Database | PostgreSQL               |

---

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL installed and running
- Groq API key → [console.groq.com](https://console.groq.com)

---

### 1. Clone the repo

```bash
git clone https://github.com/Reena1912/Ai-content.git
cd Ai-content
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
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

Create a database in pgAdmin or psql:

```sql
CREATE DATABASE repurposeai;
```

### 5. Configure environment variables

Create a `.env` file in the root folder:

```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/repurposeai
```

### 6. Run the backend

```bash
uvicorn main:app --reload
```

You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 7. Open the frontend

Open `index.html` directly in your browser (double-click or use VS Code Live Server).

---

## API Endpoints

| Method | Endpoint     | Description                     |
| ------ | ------------ | ------------------------------- |
| `GET`  | `/`          | Health check                    |
| `POST` | `/repurpose` | Generate content for a platform |
| `GET`  | `/history`   | Get past generations            |

### POST `/repurpose`

**Request:**

```json
{
  "article": "Your long-form article text here...",
  "platform": "twitter"
}
```

**Platforms:** `twitter`, `linkedin`, `instagram`, `newsletter`, `medium`

**Response:**

```json
{
  "platform": "twitter",
  "repurposed_content": "Tweet 1: ..."
}
```

---

## Database Schema

```sql
CREATE TABLE generations (
    id          SERIAL PRIMARY KEY,
    platform    TEXT NOT NULL,
    input_text  TEXT NOT NULL,
    output_text TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Project Structure

```
ai-content/
├── main.py           # FastAPI backend
├── index.html        # Frontend UI
├── requirements.txt  # Python dependencies
├── .env              # Environment variables (not in git)
├── .gitignore
├── README.md
└── venv/             # Virtual environment (not in git)
```

---

## Screenshots

_Coming soon_

---

## License

MIT

---

## Author

Built by [@Reena1912](https://github.com/Reena1912)
