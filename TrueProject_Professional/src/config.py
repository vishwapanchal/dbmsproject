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

    # API Config
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Paths
    BASE_DIR = os.getcwd()
    DATA_DIR = os.path.join(BASE_DIR, "data")
    INDEX_PATH = os.path.join(DATA_DIR, "project_vectors.index")
    METADATA_PATH = os.path.join(DATA_DIR, "project_metadata.pkl")

    # Models
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    LLM_MODEL = 'gemini-2.0-flash'
