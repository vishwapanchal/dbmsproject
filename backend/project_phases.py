from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection

router = APIRouter()

# --- Pydantic Model ---
class ProjectPhaseUpdate(BaseModel):
    submitted_project_id: int
    phase1_marks: Optional[int] = None
    phase1_remarks: Optional[str] = None
    phase2_marks: Optional[int] = None
    phase2_remarks: Optional[str] = None
    phase3_marks: Optional[int] = None
    phase3_remarks: Optional[str] = None

# --- API ENDPOINT ---
@router.put("/update-project-phases")
def update_project_phases(data: ProjectPhaseUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Check if a phase record already exists
        check_query = "SELECT submitted_project_id FROM project_phases WHERE submitted_project_id = %s"
        cursor.execute(check_query, (data.submitted_project_id,))
        exists = cursor.fetchone()

        if exists:
            # OPTION A: UPDATE (Preserve existing values if new ones are None)
            update_query = """
                UPDATE project_phases
                SET 
                    phase1_marks = COALESCE(%s, phase1_marks),
                    phase1_remarks = COALESCE(%s, phase1_remarks),
                    phase2_marks = COALESCE(%s, phase2_marks),
                    phase2_remarks = COALESCE(%s, phase2_remarks),
                    phase3_marks = COALESCE(%s, phase3_marks),
                    phase3_remarks = COALESCE(%s, phase3_remarks)
                WHERE submitted_project_id = %s
            """
            cursor.execute(update_query, (
                data.phase1_marks, data.phase1_remarks,
                data.phase2_marks, data.phase2_remarks,
                data.phase3_marks, data.phase3_remarks,
                data.submitted_project_id
            ))
            message = "Project phases updated successfully."

        else:
            # OPTION B: INSERT (Create new record with defaults)
            insert_query = """
                INSERT INTO project_phases (
                    submitted_project_id, 
                    phase1_marks, phase1_remarks, 
                    phase2_marks, phase2_remarks, 
                    phase3_marks, phase3_remarks
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                data.submitted_project_id,
                data.phase1_marks or 0, data.phase1_remarks or "",
                data.phase2_marks or 0, data.phase2_remarks or "",
                data.phase3_marks or 0, data.phase3_remarks or ""
            ))
            message = "Project phases created successfully."

        conn.commit()
        return {"message": message, "submitted_project_id": data.submitted_project_id}

    except Exception as e:
        conn.rollback()
        print(f"Error updating project phases: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        conn.close()
