from fastapi import APIRouter, HTTPException
from database import get_db_connection

router = APIRouter()

@router.get("/projects")
def get_all_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch data from the 'projects' table exactly as shown in your terminal
        query = "SELECT project_id, title, synopsis FROM projects"
        
        cursor.execute(query)
        projects = cursor.fetchall()
        
        return projects
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
