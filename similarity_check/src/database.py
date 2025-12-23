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
