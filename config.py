import os
from pathlib import Path

from dotenv import load_dotenv


# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# GEMINI CONFIGURATION
# --------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()


# --------------------------------------------------
# PROJECT DIRECTORIES
# --------------------------------------------------

KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"

VECTOR_DB_DIR = BASE_DIR / "vector_db"

WORKSPACE_DIR = BASE_DIR / "workspace"


# --------------------------------------------------
# CREATE DIRECTORIES IF NOT PRESENT
# --------------------------------------------------

KNOWLEDGE_BASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

VECTOR_DB_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

WORKSPACE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. Check your .env file."
    )

if not GEMINI_MODEL:
    raise ValueError(
        "GEMINI_MODEL is missing. Check your .env file."
    )