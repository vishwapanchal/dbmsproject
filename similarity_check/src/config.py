import os
from dotenv import load_dotenv

class Config:
    # --- PATH SETUP ---
    # 1. Get the directory of THIS file (src/)
    SRC_DIR = os.path.dirname(os.path.abspath(__file__))
    # 2. Go up one level to 'similarity_check/'
    BASE_DIR = os.path.dirname(SRC_DIR)
    # 3. Define path to .env file explicitly
    ENV_PATH = os.path.join(BASE_DIR, '.env')
    
    # --- LOAD ENVIRONMENT VARIABLES ---
    # This loads the vars from .env into Python's os.environ
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)
    else:
        print(f"⚠️ Warning: .env file not found at {ENV_PATH}")

    # Database Config
    DB_PARAMS = {
        "dbname": os.getenv("DB_NAME", "truedb"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT", "5432")
    }

    # API Config - OPENROUTER
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Paths
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True) 

    INDEX_PATH = os.path.join(DATA_DIR, "project_vectors.index")
    METADATA_PATH = os.path.join(DATA_DIR, "project_metadata.pkl")

    # Models
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    LLM_MODEL = 'xiaomi/mimo-v2-flash:free'

# --- DEBUG CHECK ---
if not Config.OPENROUTER_API_KEY:
    print(f"❌ ERROR: Could not read OPENROUTER_API_KEY from {Config.ENV_PATH}")
    print("Make sure your .env file has: OPENROUTER_API_KEY=sk-or-v1-...")
else:
    print(f"✅ Config Loaded. Key found in .env: {Config.OPENROUTER_API_KEY[:5]}...")