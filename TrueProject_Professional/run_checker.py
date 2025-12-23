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
        # PRINTING THE SCORE HERE
        print(f"   Match #{i+1}: {m['name']} (Similarity: {m['similarity']}%)")

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