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
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        student_row = cursor.fetchone()
        
        if student_row:
            # Convert RealDictRow to dict
            student = dict(student_row)
            
            # Remove password for security
            if 'password' in student: del student['password']
            student['role'] = 'student'
            
            # Initialize extra fields with defaults
            student['team_members'] = []
            student['project_title'] = None
            student['project_status'] = None
            student['mentor_id'] = None
            student['mentor_name'] = None
            
            # Initialize Phase details
            student['project_phases'] = {
                'phase1': {'marks': 0, 'remarks': None},
                'phase2': {'marks': 0, 'remarks': None},
                'phase3': {'marks': 0, 'remarks': None}
            }

            # --- A. Find Team ---
            # Search inside the JSONB array 'team_members'
            query_team = """
                SELECT t.team_id, t.team_members 
                FROM teams t, jsonb_array_elements(t.team_members) as member 
                WHERE member->>'email' = %s
            """
            cursor.execute(query_team, (email,))
            team_row = cursor.fetchone()
            
            if team_row:
                student['team_members'] = team_row['team_members']
                
                # --- B. Find Project, Mentor & Phases ---
                # We JOIN submitted_projects with teachers (for mentor name)
                # AND project_phases (for marks/remarks) using submitted_project_id
                query_project = """
                    SELECT 
                        sp.submitted_project_id,
                        sp.project_title, 
                        sp.status, 
                        sp.mentor_id, 
                        t.name as mentor_name,
                        pp.phase1_marks, pp.phase1_remarks,
                        pp.phase2_marks, pp.phase2_remarks,
                        pp.phase3_marks, pp.phase3_remarks
                    FROM submitted_projects sp
                    LEFT JOIN teachers t ON sp.mentor_id = t.teacher_id
                    LEFT JOIN project_phases pp ON sp.submitted_project_id = pp.submitted_project_id
                    WHERE sp.team_id = %s
                """
                cursor.execute(query_project, (team_row['team_id'],))
                project_row = cursor.fetchone()
                
                if project_row:
                    student['project_title'] = project_row['project_title']
                    student['project_status'] = project_row['status']
                    student['mentor_id'] = project_row['mentor_id']
                    student['mentor_name'] = project_row['mentor_name']
                    
                    # Map the flat DB row to the structured dictionary
                    # We use 'or 0' because LEFT JOIN might return None if phases aren't initialized yet
                    student['project_phases'] = {
                        'phase1': {
                            'marks': project_row['phase1_marks'] or 0,
                            'remarks': project_row['phase1_remarks']
                        },
                        'phase2': {
                            'marks': project_row['phase2_marks'] or 0,
                            'remarks': project_row['phase2_remarks']
                        },
                        'phase3': {
                            'marks': project_row['phase3_marks'] or 0,
                            'remarks': project_row['phase3_remarks']
                        }
                    }
            
            return student
        
        # ---------------------------------------------------------
        # 2. Check if user is a TEACHER
        # ---------------------------------------------------------
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