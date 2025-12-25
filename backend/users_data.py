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
        # ---------------------------------------------------------
        # 2. Check if user is a TEACHER
        # ---------------------------------------------------------
        cursor.execute("SELECT * FROM teachers WHERE email = %s", (email,))
        teacher_row = cursor.fetchone()
        
        if teacher_row:
            teacher = dict(teacher_row)
            if 'password' in teacher: del teacher['password']
            teacher['role'] = 'teacher'
            
            # --- Fetch Mentored Projects, Team Details & Phases ---
            # Added sp.similar_project_titles to the SELECT list
            query_mentored = """
                SELECT 
                    sp.submitted_project_id, 
                    sp.team_id, 
                    sp.project_title, 
                    sp.project_synopsis, 
                    sp.status, 
                    sp.similarity_score, 
                    sp.similar_projects_id, 
                    sp.similar_project_titles,
                    sp.similarity_description,
                    t.team_name, 
                    t.team_size, 
                    t.team_members,
                    pp.phase_id,
                    pp.phase1_marks, pp.phase1_remarks,
                    pp.phase2_marks, pp.phase2_remarks,
                    pp.phase3_marks, pp.phase3_remarks
                FROM submitted_projects sp
                JOIN teams t ON sp.team_id = t.team_id
                LEFT JOIN project_phases pp ON sp.submitted_project_id = pp.submitted_project_id
                WHERE sp.mentor_id = %s
            """
            cursor.execute(query_mentored, (teacher['teacher_id'],))
            projects_rows = cursor.fetchall()

            teacher['mentored_projects'] = []
            
            for row in projects_rows:
                # Basic Project Data
                project_data = {
                    "submitted_project_id": row['submitted_project_id'],
                    "project_title": row['project_title'],
                    "project_synopsis": row['project_synopsis'],
                    "status": row['status'],
                    "similarity_score": row['similarity_score'],
                    "similar_projects_id": row['similar_projects_id'],
                    "similar_project_titles": row['similar_project_titles'], # Added here
                    "similarity_description": row['similarity_description'],
                    "team_details": {
                        "team_id": row['team_id'],
                        "team_name": row['team_name'],
                        "team_size": row['team_size'],
                        "team_members": row['team_members']
                    },
                    "project_phases": None # Default to None
                }
                
                # CONDITIONAL FETCH: Only include phases if status is 'approved'
                if row['status'] == 'approved':
                    project_data["project_phases"] = {
                        "phase_id": row['phase_id'],
                        "phase1": {
                            "marks": row['phase1_marks'] or 0,
                            "remarks": row['phase1_remarks']
                        },
                        "phase2": {
                            "marks": row['phase2_marks'] or 0,
                            "remarks": row['phase2_remarks']
                        },
                        "phase3": {
                            "marks": row['phase3_marks'] or 0,
                            "remarks": row['phase3_remarks']
                        }
                    }

                teacher['mentored_projects'].append(project_data)

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