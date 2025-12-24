#!/bin/bash

# Define the file paths
STATUS_FILE="backend/project_status.py"
MAIN_FILE="backend/main.py"

echo "--------------------------------------------------"
echo "1. Creating ${STATUS_FILE}..."
echo "--------------------------------------------------"

# Create the new file with the Python logic
cat > "$STATUS_FILE" << 'EOF'
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
EOF

echo "File ${STATUS_FILE} created."
echo ""

echo "--------------------------------------------------"
echo "2. Updating ${MAIN_FILE} to register the new router..."
echo "--------------------------------------------------"

# Check if main.py exists
if [ ! -f "$MAIN_FILE" ]; then
    echo "Error: $MAIN_FILE not found!"
    exit 1
fi

# 1. Add Import Statement
# We verify if it exists, otherwise we insert it after 'phases_router'
if grep -q "from project_status import router as status_router" "$MAIN_FILE"; then
    echo "Import already exists in ${MAIN_FILE}. Skipping..."
else
    if grep -q "from project_phases import router as phases_router" "$MAIN_FILE"; then
        sed -i '/from project_phases import router as phases_router/a from project_status import router as status_router' "$MAIN_FILE"
        echo "Added import statement."
    else
        # Fallback if phases_router isn't found, add to end of imports
        sed -i '/from projects import router as projects_router/a from project_status import router as status_router' "$MAIN_FILE"
        echo "Added import statement (fallback location)."
    fi
fi

# 2. Add Include Router Statement
# We verify if it exists, otherwise we insert it after 'phases_router'
if grep -q "app.include_router(status_router)" "$MAIN_FILE"; then
    echo "Router registration already exists in ${MAIN_FILE}. Skipping..."
else
    if grep -q "app.include_router(phases_router)" "$MAIN_FILE"; then
        sed -i '/app.include_router(phases_router)/a app.include_router(status_router)' "$MAIN_FILE"
        echo "Added router registration."
    else
        # Fallback if phases_router isn't found
        sed -i '/app.include_router(projects_router)/a app.include_router(status_router)' "$MAIN_FILE"
        echo "Added router registration (fallback location)."
    fi
fi

echo ""
echo "--------------------------------------------------"
echo "Update Complete. Restart your backend server."
echo "--------------------------------------------------"