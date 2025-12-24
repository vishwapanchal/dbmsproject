#!/bin/bash

# Navigate to backend
cd backend || exit

echo "Updating users_data.py to match actual DB schema..."

# Overwrite users_data.py
cat <<PYTHON_EOF > users_data.py
from fastapi import APIRouter, HTTPException
from database import get_db_connection

router = APIRouter()

@router.get("/user/{email}")
def get_user_details(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # ---------------------------------------------------------
        # 1. Check if user is a STUDENT
        # ---------------------------------------------------------
        # Schema: student_id, name, usn, year, sem, dept, email, password
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        student_row = cursor.fetchone()
        
        if student_row:
            # Convert RealDictRow to a standard python dict to ensure it's mutable
            student = dict(student_row)
            
            # Remove password for security
            if 'password' in student: del student['password']
            student['role'] = 'student'
            
            # Initialize extra fields
            student['team_members'] = []
            student['project_title'] = None
            student['project_status'] = None
            student['mentor_id'] = None
            student['mentor_name'] = None

            # --- A. Find Team ---
            # Search inside the JSONB array 'team_members' for the matching email
            # Schema: team_id, team_members
            query_team = """
                SELECT t.team_id, t.team_members 
                FROM teams t, jsonb_array_elements(t.team_members) as member 
                WHERE member->>'email' = %s
            """
            cursor.execute(query_team, (email,))
            team_row = cursor.fetchone()
            
            if team_row:
                # Attach Team Members
                student['team_members'] = team_row['team_members']
                
                # --- B. Find Project & Mentor ---
                # Join 'submitted_projects' with 'teachers' to get the mentor's name
                # Schema: submitted_projects (team_id, mentor_id, project_title, status)
                # Schema: teachers (teacher_id, name)
                query_project = """
                    SELECT 
                        sp.project_title, 
                        sp.status, 
                        sp.mentor_id, 
                        t.name as mentor_name
                    FROM submitted_projects sp
                    LEFT JOIN teachers t ON sp.mentor_id = t.teacher_id
                    WHERE sp.team_id = %s
                """
                cursor.execute(query_project, (team_row['team_id'],))
                project_row = cursor.fetchone()
                
                if project_row:
                    student['project_title'] = project_row['project_title']
                    student['project_status'] = project_row['status']
                    student['mentor_id'] = project_row['mentor_id']
                    student['mentor_name'] = project_row['mentor_name']
            
            return student
        
        # ---------------------------------------------------------
        # 2. Check if user is a TEACHER
        # ---------------------------------------------------------
        # Schema: teacher_id, name, dept, email, password, total_projects
        cursor.execute("SELECT * FROM teachers WHERE email = %s", (email,))
        teacher_row = cursor.fetchone()
        
        if teacher_row:
            teacher = dict(teacher_row)
            if 'password' in teacher: del teacher['password']
            teacher['role'] = 'teacher'
            return teacher

        # ---------------------------------------------------------
        # 3. Not Found
        # ---------------------------------------------------------
        raise HTTPException(status_code=404, detail="User not found")
        
    except Exception as e:
        print(f"Error in get_user_details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
PYTHON_EOF

echo "----------------------------------------------------"
echo "✅ users_data.py updated!"
echo "   - Adapted to schema: students(student_id), teachers(teacher_id)"
echo "   - Adapted to schema: submitted_projects(team_id, mentor_id)"
echo "----------------------------------------------------"
