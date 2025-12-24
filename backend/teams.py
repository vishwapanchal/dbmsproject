import json
import psycopg2
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection

router = APIRouter()

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

@router.post("/create-team")
def create_team(team_data: TeamCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. INSERT TEAM
        members_json = json.dumps([member.dict() for member in team_data.team_members])

        cursor.execute("""
            INSERT INTO teams (team_name, team_size, team_members)
            VALUES (%s, %s, %s)
            RETURNING team_id
        """, (team_data.team_name, team_data.team_size, members_json))
        
        team_id = cursor.fetchone()['team_id']

        # 2. INSERT PROJECT (Initially without a mentor)
        cursor.execute("""
            INSERT INTO submitted_projects (team_id, project_title, project_synopsis)
            VALUES (%s, %s, %s)
            RETURNING submitted_project_id
        """, (team_id, team_data.project_title, team_data.project_synopsis))
        
        project_id = cursor.fetchone()['submitted_project_id']

        assigned_mentor_info = "No eligible mentor found"

        # 3. ASSIGN MENTOR LOGIC
        if team_data.team_members:
            # Get dept from the first student
            first_student_dept = team_data.team_members[0].dept

            # Find the "next" available mentor in that Dept with < 5 projects
            # FOR UPDATE locks the row briefly to prevent two teams grabbing the last slot at the exact same ms
            cursor.execute("""
                SELECT teacher_id, name, total_projects 
                FROM teachers 
                WHERE dept = %s AND total_projects < 5 
                ORDER BY teacher_id ASC 
                LIMIT 1 
                FOR UPDATE
            """, (first_student_dept,))
            
            mentor = cursor.fetchone()

            if mentor:
                mentor_id = mentor['teacher_id']
                
                # A. Link this mentor to the submitted project
                cursor.execute("""
                    UPDATE submitted_projects 
                    SET mentor_id = %s 
                    WHERE submitted_project_id = %s
                """, (mentor_id, project_id))

                # B. Increment the mentor's project count
                cursor.execute("""
                    UPDATE teachers 
                    SET total_projects = total_projects + 1 
                    WHERE teacher_id = %s
                """, (mentor_id,))
                
                assigned_mentor_info = f"Assigned to {mentor['name']} (ID: {mentor_id})"

        conn.commit()
        
        return {
            "message": "Team created and Project submitted successfully",
            "team_id": team_id,
            "project_id": project_id,
            "mentor_status": assigned_mentor_info,
            "project_status": "not approved"
        }

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Team Name already exists")
    except Exception as e:
        conn.rollback()
        # Print error to console for debugging
        print(f"Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()