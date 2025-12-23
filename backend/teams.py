import json
import psycopg2
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection

router = APIRouter()

# --- PYDANTIC MODELS ---

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

# --- ENDPOINT ---

@router.post("/create-team")
def create_team(team_data: TeamCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Insert into TEAMS table
        members_json = json.dumps([member.dict() for member in team_data.team_members])

        cursor.execute("""
            INSERT INTO teams (team_name, team_size, team_members)
            VALUES (%s, %s, %s)
            RETURNING team_id
        """, (team_data.team_name, team_data.team_size, members_json))
        
        team_id = cursor.fetchone()['team_id']

        # 2. Insert into SUBMITTED_PROJECTS table
        cursor.execute("""
            INSERT INTO submitted_projects (team_id, project_title, project_synopsis)
            VALUES (%s, %s, %s)
        """, (team_id, team_data.project_title, team_data.project_synopsis))

        conn.commit()
        
        return {
            "message": "Team created and Project submitted successfully",
            "team_id": team_id,
            "project_status": "not approved"
        }

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Team Name already exists")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
