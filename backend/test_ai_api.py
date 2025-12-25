import sys
import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# --- 1. PATH & CONFIG SETUP ---
# Determine paths relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))      # .../backend
project_root = os.path.dirname(current_dir)                   # .../trueProject
similarity_dir = os.path.join(project_root, 'similarity_check') 

# Load .env explicitly from 'similarity_check' folder
similarity_env_path = os.path.join(similarity_dir, '.env')
if os.path.exists(similarity_env_path):
    load_dotenv(similarity_env_path)
    print(f"✅ Loaded config from: {similarity_env_path}")
else:
    print(f"⚠️ Warning: No .env file found at {similarity_env_path}")

# Add 'similarity_check' to sys.path to allow imports
if similarity_dir not in sys.path:
    sys.path.append(similarity_dir)

# --- 2. IMPORT MODULES ---
try:
    from src.vector_engine import VectorEngine
    from src.llm_judge import GeminiJudge
    print("✅ Successfully imported VectorEngine and GeminiJudge")
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    sys.exit(1) # Stop app if we can't import

# --- 3. HELPER FUNCTIONS ---
def remove_emojis(text):
    if not text: return ""
    return text.encode('ascii', 'ignore').decode('ascii')

# --- 4. FASTAPI APP SETUP ---
app = FastAPI(title="AI Similarity Test API")

# Define Request Model
class ProjectRequest(BaseModel):
    title: str
    synopsis: str

@app.get("/")
def health_check():
    return {"status": "active", "message": "AI Test API is up and running"}

@app.post("/test-similarity")
def check_similarity_endpoint(request: ProjectRequest):
    """
    Endpoint to trigger the full AI Check manually.
    """
    print(f"\n📨 Received Request: {request.title}")
    
    try:
        # A. Initialize Engine
        engine = VectorEngine()
        if not engine.load_index():
            raise HTTPException(status_code=500, detail="Vector Index not found in similarity_check folder")

        # B. Initialize Judge
        judge = GeminiJudge()

        # C. Perform Search
        matches = engine.search(request.title, request.synopsis)
        
        # D. Get AI Verdict
        print("⚖️ Asking AI Judge...")
        raw_verdict = judge.get_verdict(
            {"title": request.title, "synopsis": request.synopsis}, 
            matches
        )
        
        # E. Clean and Return
        clean_verdict = remove_emojis(raw_verdict)
        
        # Parse JSON string back to Object for cleaner API response
        try:
            verdict_json = json.loads(clean_verdict)
        except json.JSONDecodeError:
            verdict_json = {"raw_text": clean_verdict}

        return {
            "status": "success",
            "matches_found": len(matches),
            "top_match_score": matches[0]['similarity'] if matches else 0,
            "ai_response": verdict_json
        }

    except Exception as e:
        print(f"❌ Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. RUN SERVER ---
if __name__ == "__main__":
    # Runs on http://localhost:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)