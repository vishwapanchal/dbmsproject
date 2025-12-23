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
