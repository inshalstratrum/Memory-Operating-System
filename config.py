import os
from pathlib import Path

# ==========================================
# 🧠 MEMORY OS v5 - GLOBAL CONFIGURATION
# ==========================================

# --- 1. API & LLM SETTINGS ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "") 
DEFAULT_MODEL = os.environ.get("SHALI_MODEL", "openai/gpt-oss-20b")

# --- 2. SECURITY SETTINGS ---
# Shali will ask for this PIN before revealing sensitive memory data
MASTER_PIN = os.environ.get("SHALI_MASTER_PIN", "0000")

# --- 3. SYSTEM PATHS (WINDOWS SAFE) ---
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "chroma_db"
WORKSPACE_DIR = DATA_DIR / "workspace"
LOGS_DIR = DATA_DIR / "logs"

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# --- 4. VOICE SETTINGS ---
VOICE_CONFIG = {
    "tone": "friendly",
    "rate": 175,
    "volume": 1.0
}

# --- 5. EMBEDDING SETTINGS ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
