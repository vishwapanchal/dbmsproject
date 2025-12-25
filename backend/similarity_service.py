import sys
import os
import json
from dotenv import load_dotenv

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
similarity_dir = os.path.join(project_root, 'similarity_check') 

# Load .env
similarity_env_path = os.path.join(similarity_dir, '.env')
if os.path.exists(similarity_env_path):
    load_dotenv(similarity_env_path)

# Add similarity_check to path
if similarity_dir not in sys.path:
    sys.path.append(similarity_dir)

def remove_emojis(text):
    if not text: return ""
    return text.encode('ascii', 'ignore').decode('ascii')

def perform_similarity_check(title: str, synopsis: str):
    print(f"🔄 Starting Similarity Check for: {title}")
    
    try:
        from src.vector_engine import VectorEngine
        from src.llm_judge import GeminiJudge
    except ImportError as e:
        print(f"❌ Critical Import Error: {e}")
        return {
            "similarity_score": 0,
            "similar_projects_id": [],
            "similar_project_titles": [], # Added this
            "similarity_description": json.dumps({"error": f"Import Failed: {e}"})
        }

    try:
        # 1. Initialize Vector Engine
        engine = VectorEngine()
        if not engine.load_index():
            print("⚠️ Index not found. Skipping check.")
            return {
                "similarity_score": 0,
                "similar_projects_id": [],
                "similar_project_titles": [], # Added this
                "similarity_description": json.dumps({"error": "Index not found"})
            }
            
        # 2. Initialize Judge
        judge = GeminiJudge()

        # 3. Vector Search
        matches = engine.search(title, synopsis)
        
        # 4. Extract IDs AND Titles directly from the matches
        top_score = float(matches[0].get('similarity', 0)) if matches else 0.0
        
        match_ids = []
        match_titles = []
        
        if matches:
            for m in matches:
                # Get ID
                match_ids.append(m.get('id'))
                # Get Title (key is 'name' in vector engine metadata)
                match_titles.append(m.get('name', 'Unknown Title'))

        # 5. Get AI Verdict
        print("⚖️ Asking AI Judge...")
        raw_verdict = judge.get_verdict({"title": title, "synopsis": synopsis}, matches)
        clean_verdict = remove_emojis(raw_verdict)

        print("✅ Check Complete.")
        
        return {
            "similarity_score": top_score,
            "similar_projects_id": match_ids,
            "similar_project_titles": match_titles, # Return titles here
            "similarity_description": clean_verdict 
        }

    except Exception as e:
        print(f"❌ Check Failed: {e}")
        return {
            "similarity_score": 0,
            "similar_projects_id": [],
            "similar_project_titles": [],
            "similarity_description": json.dumps({"error": str(e)})
        }