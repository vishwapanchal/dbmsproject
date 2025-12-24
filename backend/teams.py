import json
import psycopg2
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection

router = APIRouter()

# --- MODELS ---
class TeamMember(BaseModel):
    name: str
    usn: str
    email: str
    dept: str

class TeamCreate(BaseModel):
    team_name: str
    team_size: int
    team_members: List[TeamMember]
    project_title: str
    project_synopsis: str

# --- CREATE TEAM (Strict Unique USN + Strict Mentor) ---
@router.post("/create-team")
def create_team(team_data: TeamCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ---------------------------------------------------------
        # 0. VALIDATION: Check for Duplicates in the INPUT LIST
        # ---------------------------------------------------------
        # This ensures you didn't accidentally send the same USN twice in the same request
        input_usns = [m.usn for m in team_data.team_members]
        if len(input_usns) != len(set(input_usns)):
            raise HTTPException(
                status_code=400, 
                detail="Duplicate USNs found in the request. A student cannot be added twice to the same team."
            )

        # ---------------------------------------------------------
        # 1. VALIDATION: Check Global Uniqueness in DATABASE
        # ---------------------------------------------------------
        # Check if ANY student is already in ANY other team in the database
        for member in team_data.team_members:
            # This query scans ALL teams (FROM teams t)
            check_query = """
                SELECT team_name 
                FROM teams t, jsonb_array_elements(t.team_members) as m 
                WHERE m->>'usn' = %s
            """
            cursor.execute(check_query, (member.usn,))
            existing_team = cursor.fetchone()
            
            if existing_team:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Student '{member.name}' (USN: {member.usn}) is already registered in team '{existing_team['team_name']}'."
                )

        # ---------------------------------------------------------
        # 2. INSERT TEAM
        # ---------------------------------------------------------
        members_json = json.dumps([member.dict() for member in team_data.team_members])

        cursor.execute("""
            INSERT INTO teams (team_name, team_size, team_members)
            VALUES (%s, %s, %s)
            RETURNING team_id
        """, (team_data.team_name, team_data.team_size, members_json))
        
        team_id = cursor.fetchone()['team_id']

        # ---------------------------------------------------------
        # 3. INSERT PROJECT
        # ---------------------------------------------------------
        cursor.execute("""
            INSERT INTO submitted_projects (team_id, project_title, project_synopsis)
            VALUES (%s, %s, %s)
            RETURNING submitted_project_id
        """, (team_id, team_data.project_title, team_data.project_synopsis))
        
        project_id = cursor.fetchone()['submitted_project_id']

        # ---------------------------------------------------------
        # 4. ASSIGN MENTOR LOGIC (Strict)
        # ---------------------------------------------------------
        if not team_data.team_members:
            conn.rollback()
            raise HTTPException(status_code=400, detail="Cannot assign mentor: Team has no members.")

        # Get dept from the first student
        first_student_dept = team_data.team_members[0].dept

        # Find the "next" available mentor
        cursor.execute("""
            SELECT teacher_id, name, total_projects 
            FROM teachers 
            WHERE dept = %s AND total_projects < 5 
            ORDER BY teacher_id ASC 
            LIMIT 1 
            FOR UPDATE
        """, (first_student_dept,))
        
        mentor = cursor.fetchone()

        # FAIL IF NO MENTOR
        if not mentor:
            conn.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"Submission Failed: No eligible mentor found in {first_student_dept} department. Project was not submitted."
            )

        mentor_id = mentor['teacher_id']
        
        # Link mentor & Update count
        cursor.execute("""
            UPDATE submitted_projects 
            SET mentor_id = %s 
            WHERE submitted_project_id = %s
        """, (mentor_id, project_id))

        cursor.execute("""
            UPDATE teachers 
            SET total_projects = total_projects + 1 
            WHERE teacher_id = %s
        """, (mentor_id,))
        
        assigned_mentor_info = f"Assigned to {mentor['name']} (ID: {mentor_id})"

        conn.commit()
        
        return {
            "message": "Team created successfully",
            "team_id": team_id,
            "project_id": project_id,
            "mentor_status": assigned_mentor_info
        }

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Team Name already exists")
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- FETCH TEAM BY MEMBER EMAIL ---
@router.get("/my-team/{email}")
def get_team_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT team_members 
            FROM teams t, jsonb_array_elements(t.team_members) as member 
            WHERE member->>'email' = %s
        """
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found in any team")
            
        return result['team_members']
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
