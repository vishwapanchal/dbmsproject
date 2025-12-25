import json
import psycopg2
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from database import get_db_connection

# IMPORT THE NEW SERVICE
from similarity_service import perform_similarity_check

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

# --- CREATE TEAM ---
@router.post("/create-team")
def create_team(team_data: TeamCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. VALIDATION (Duplicate USNs)
        input_usns = [m.usn for m in team_data.team_members]
        if len(input_usns) != len(set(input_usns)):
            raise HTTPException(status_code=400, detail="Duplicate USNs in request.")

        # 2. VALIDATION (Global Uniqueness)
        for member in team_data.team_members:
            check_query = """
                SELECT team_name 
                FROM teams t, jsonb_array_elements(t.team_members) as m 
                WHERE m->>'usn' = %s
            """
            cursor.execute(check_query, (member.usn,))
            existing_team = cursor.fetchone()
            if existing_team:
                raise HTTPException(status_code=400, detail=f"Student {member.usn} is already in team '{existing_team['team_name']}'.")

        # 3. INSERT TEAM
        members_json = json.dumps([member.dict() for member in team_data.team_members])
        cursor.execute("""
            INSERT INTO teams (team_name, team_size, team_members)
            VALUES (%s, %s, %s)
            RETURNING team_id
        """, (team_data.team_name, team_data.team_size, members_json))
        team_id = cursor.fetchone()['team_id']

        # 4. INSERT PROJECT
        cursor.execute("""
            INSERT INTO submitted_projects (team_id, project_title, project_synopsis)
            VALUES (%s, %s, %s)
            RETURNING submitted_project_id
        """, (team_id, team_data.project_title, team_data.project_synopsis))
        project_id = cursor.fetchone()['submitted_project_id']

        # ------------------------------------------------------------------
        # 🌟 NEW: RUN SIMILARITY CHECK & UPDATE DB
        # ------------------------------------------------------------------
        # Perform the check
        similarity_results = perform_similarity_check(team_data.project_title, team_data.project_synopsis)

        if similarity_results:
            # Extract data directly from the service results
            # The service now ensures these lists match and are populated from the index
            sim_ids = similarity_results.get('similar_projects_id', [])
            sim_titles = similarity_results.get('similar_project_titles', [])

            cursor.execute("""
                UPDATE submitted_projects
                SET similarity_score = %s,
                    similar_projects_id = %s,
                    similar_project_titles = %s,
                    similarity_description = %s
                WHERE submitted_project_id = %s
            """, (
                similarity_results.get('similarity_score', 0),
                json.dumps(sim_ids),    # Direct list of IDs
                json.dumps(sim_titles), # Direct list of Titles
                similarity_results.get('similarity_description', ""),
                project_id
            ))
        # ------------------------------------------------------------------

        # 5. ASSIGN MENTOR
        if not team_data.team_members:
             raise HTTPException(status_code=400, detail="No members.")
        
        first_dept = team_data.team_members[0].dept
        
        cursor.execute("""
            SELECT teacher_id, name, total_projects 
            FROM teachers 
            WHERE dept = %s AND total_projects < 5 
            ORDER BY teacher_id ASC 
            LIMIT 1 
            FOR UPDATE
        """, (first_dept,))
        mentor = cursor.fetchone()

        if not mentor:
            conn.rollback() 
            raise HTTPException(status_code=400, detail=f"No mentor available in {first_dept}.")

        mentor_id = mentor['teacher_id']
        cursor.execute("UPDATE submitted_projects SET mentor_id = %s WHERE submitted_project_id = %s", (mentor_id, project_id))
        cursor.execute("UPDATE teachers SET total_projects = total_projects + 1 WHERE teacher_id = %s", (mentor_id,))
        
        conn.commit()
        
        return {
            "message": "Team created and Project Submitted successfully",
            "team_id": team_id,
            "project_id": project_id,
            "mentor": mentor['name'],
            "similarity_score": similarity_results['similarity_score'] if similarity_results else 0
        }

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Team Name already exists")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()