import os
from dotenv import load_dotenv

load_dotenv()

class Config:
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
    BASE_DIR = os.getcwd()
    DATA_DIR = os.path.join(BASE_DIR, "data")
    INDEX_PATH = os.path.join(DATA_DIR, "project_vectors.index")
    METADATA_PATH = os.path.join(DATA_DIR, "project_metadata.pkl")

    # Models
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    
    # --- MODEL SELECTION (TRY THESE IF ONE FAILS) ---
    # Option 1: DeepSeek R1 Distill Llama 70B (Free) - Best balance of reasoning/uptime
    LLM_MODEL = 'mistralai/devstral-2512:free'
    
    # Option 2: DeepSeek R1 (Older free checkpoint) - Try if Option 1 fails
    # LLM_MODEL = 'deepseek/deepseek-r1-0528:free'
    
    # Option 3: Gemini 2.0 Flash (Free) - Extremely fast & reliable backup
    # LLM_MODEL = 'google/gemini-2.0-flash-exp:free'