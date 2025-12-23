#!/bin/bash

# Define the project name
PROJECT_NAME="TrueProject_Professional"

echo "🚀 Starting Project Setup: $PROJECT_NAME..."

# 1. Create Directory Structure
mkdir -p "$PROJECT_NAME/data"
mkdir -p "$PROJECT_NAME/src"
echo "✅ Directories created."

# 2. Create requirements.txt
cat <<EOF > "$PROJECT_NAME/requirements.txt"
psycopg2-binary
faiss-cpu
sentence-transformers
numpy
google-genai
python-dotenv
EOF
echo "📄 requirements.txt created."

# 3. Create .env (With placeholders)
cat <<EOF > "$PROJECT_NAME/.env"
# AWS RDS Credentials
DB_NAME=truedb
DB_USER=postgres
DB_PASSWORD=YOUR_DB_PASSWORD_HERE
DB_HOST=trueproject-db.c07cik8ugpex.us-east-1.rds.amazonaws.com
DB_PORT=5432

# Google Gemini API
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
EOF
echo "🔐 .env created (Please update your passwords!)."

# 4. Create Source Code Files

# src/__init__.py
touch "$PROJECT_NAME/src/__init__.py"

# src/config.py
cat <<EOF > "$PROJECT_NAME/src/config.py"
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
    LLM_MODEL = 'gemini-1.5-flash'
EOF

# src/database.py
cat <<EOF > "$PROJECT_NAME/src/database.py"
import psycopg2
from src.config import Config

class DatabaseHandler:
    @staticmethod
    def fetch_projects():
        """Fetches (id, title, synopsis) from AWS RDS."""
        print(f"📡 Connecting to Database at {Config.DB_PARAMS['host']}...")
        
        conn = None
        try:
            conn = psycopg2.connect(**Config.DB_PARAMS)
            cur = conn.cursor()
            
            # Fetching data
            query = "SELECT project_id, title, synopsis FROM projects"
            cur.execute(query)
            rows = cur.fetchall()
            
            print(f"✅ Successfully fetched {len(rows)} projects from RDS.")
            return rows

        except Exception as e:
            print(f"❌ Database Error: {e}")
            return []
        
        finally:
            if conn:
                conn.close()
EOF

# src/vector_engine.py
cat <<EOF > "$PROJECT_NAME/src/vector_engine.py"
import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import Config

class VectorEngine:
    def __init__(self):
        # Create data directory if it doesn't exist
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

        print(f"🧠 Loading Embedding Model ({Config.EMBEDDING_MODEL})...")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.index = None
        self.metadata = []

    def build_index(self, db_rows):
        """Creates vectors from DB rows and saves them."""
        if not db_rows:
            print("⚠️ No data to index.")
            return

        print("⚙️  Vectorizing projects...")
        texts = []
        self.metadata = []

        for pid, title, synopsis in db_rows:
            clean_synopsis = synopsis if synopsis else ""
            full_text = f"{title}: {clean_synopsis}"
            
            texts.append(full_text)
            self.metadata.append({
                "id": pid, 
                "name": title, 
                "synopsis": clean_synopsis
            })

        # Generate Embeddings
        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        
        # Build FAISS Index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        # Save to disk
        self._save()

    def _save(self):
        """Internal method to save index and metadata."""
        print(f"💾 Saving index to {Config.DATA_DIR}...")
        faiss.write_index(self.index, Config.INDEX_PATH)
        with open(Config.METADATA_PATH, "wb") as f:
            pickle.dump(self.metadata, f)
        print("✅ Index saved successfully.")

    def load_index(self):
        """Loads the index from disk."""
        if os.path.exists(Config.INDEX_PATH) and os.path.exists(Config.METADATA_PATH):
            self.index = faiss.read_index(Config.INDEX_PATH)
            with open(Config.METADATA_PATH, "rb") as f:
                self.metadata = pickle.load(f)
            return True
        return False

    def search(self, title, synopsis, top_k=3):
        """Searches for similar projects."""
        if self.index is None:
            raise FileNotFoundError("Index not loaded. Run indexer first.")

        query_text = f"{title}: {synopsis}"
        query_vector = self.model.encode([query_text])
        query_vector = np.array(query_vector).astype('float32')

        distances, indices = self.index.search(query_vector, k=top_k)
        
        results = []
        for i in range(top_k):
            idx = indices[0][i]
            if idx != -1 and idx < len(self.metadata):
                match = self.metadata[idx]
                results.append(match)
        
        return results
EOF

# src/llm_judge.py
cat <<EOF > "$PROJECT_NAME/src/llm_judge.py"
import os
import time
from google import genai
from src.config import Config

class GeminiJudge:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY missing in .env file")
        
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.LLM_MODEL

    def get_verdict(self, new_project, similar_projects):
        """Sends data to Gemini for analysis."""
        
        # Format the evidence
        evidence_text = ""
        for i, proj in enumerate(similar_projects):
            evidence_text += f"\n[EXISTING PROJECT #{i+1}]\n"
            evidence_text += f"Title: {proj['name']}\n"
            evidence_text += f"Synopsis: {proj['synopsis'][:500]}...\n"

        # The Prompt
        prompt = f"""
        You are an expert Plagiarism Detection System for a University.
        
        === NEW STUDENT PROPOSAL ===
        Title: {new_project['title']}
        Synopsis: {new_project['synopsis']}

        === EVIDENCE (TOP MATCHES FROM DATABASE) ===
        {evidence_text}

        === TASK ===
        Compare the NEW PROPOSAL against the EVIDENCE.
        1. Determine if the core idea is copied (even if rephrased).
        2. Provide an "Originality Score" (0% = Copied, 100% = Unique).
        3. Explain your reasoning briefly.

        === OUTPUT FORMAT ===
        Verdict: [Unique / Suspicious / Plagiarized]
        Score: [0-100]%
        Reasoning: [Your analysis]
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"❌ Error contacting Gemini: {e}"
EOF
echo "📦 Source code files created."

# 5. Create Execution Scripts

# run_indexer.py
cat <<EOF > "$PROJECT_NAME/run_indexer.py"
from src.database import DatabaseHandler
from src.vector_engine import VectorEngine

def main():
    print("--- 🚀 STARTING INDEXER ---")
    
    # 1. Fetch Data from AWS RDS
    projects = DatabaseHandler.fetch_projects()
    
    if not projects:
        print("⚠️ No projects found. Exiting.")
        return

    # 2. Build and Save Vector Index
    engine = VectorEngine()
    engine.build_index(projects)
    
    print("\n✅ INDEXING COMPLETE. You can now run 'run_checker.py'")

if __name__ == "__main__":
    main()
EOF

# run_checker.py
cat <<EOF > "$PROJECT_NAME/run_checker.py"
from src.vector_engine import VectorEngine
from src.llm_judge import GeminiJudge

def check_proposal(title, synopsis):
    print(f"\n🔎 Analyzing Proposal: '{title}'...")

    # 1. Initialize Engines
    try:
        engine = VectorEngine()
        if not engine.load_index():
            print("❌ Error: Index files not found. Please run 'run_indexer.py' first.")
            return
        
        judge = GeminiJudge()
    except Exception as e:
        print(f"❌ Initialization Error: {e}")
        return

    # 2. Vector Search
    print("   ...Searching database for similarities...")
    matches = engine.search(title, synopsis)
    
    print(f"\n--- 🤖 FOUND {len(matches)} POTENTIAL MATCHES ---")
    for i, m in enumerate(matches):
        print(f"   Match #{i+1}: {m['name']}")

    # 3. AI Verdict
    print("\n⚖️  Sending evidence to Gemini Judge...")
    verdict = judge.get_verdict({"title": title, "synopsis": synopsis}, matches)
    
    print("\n" + "="*50)
    print("📢 FINAL REPORT")
    print("="*50)
    print(verdict)
    print("="*50)

if __name__ == "__main__":
    # --- TEST INPUT ---
    new_title = "Smart Traffic Control System"
    new_synopsis = "A system that uses cameras and AI to change traffic lights based on vehicle density."
    
    check_proposal(new_title, new_synopsis)
EOF
echo "🏃 Execution scripts created."

echo ""
echo "=========================================="
echo "🎉 PROJECT SETUP COMPLETE!"
echo "=========================================="
echo "Next Steps:"
echo "1. cd $PROJECT_NAME"
echo "2. Open .env and add your AWS Password & Gemini API Key."
echo "3. Run: pip install -r requirements.txt"
echo "4. Run: python run_indexer.py (To build the DB)"
echo "5. Run: python run_checker.py (To test it)"
echo "=========================================="