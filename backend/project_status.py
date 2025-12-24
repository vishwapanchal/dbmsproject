from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from database import get_db_connection

router = APIRouter()

# --- Pydantic Model ---
class ProjectStatusUpdate(BaseModel):
    submitted_project_id: int
    status: str

    # Validate that status is one of the allowed values
    @field_validator('status')
    def validate_status(cls, v):
        allowed = {'approved', 'rejected', 'pending'}
        if v.lower() not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v.lower()

# --- API ENDPOINT ---
@router.put("/update-project-status")
def update_project_status(data: ProjectStatusUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Check if the project exists
        check_query = "SELECT submitted_project_id FROM submitted_projects WHERE submitted_project_id = %s"
        cursor.execute(check_query, (data.submitted_project_id,))
        project = cursor.fetchone()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2. Update the status
        update_query = """
            UPDATE submitted_projects
            SET status = %s
            WHERE submitted_project_id = %s
        """
        cursor.execute(update_query, (data.status, data.submitted_project_id))
        
        conn.commit()
        
        return {
            "message": f"Project status updated to '{data.status}' successfully.",
            "submitted_project_id": data.submitted_project_id,
            "new_status": data.status
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        print(f"Error updating project status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        conn.close()
