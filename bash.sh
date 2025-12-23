#!/bin/bash

# 1. Create the directory
echo "Setting up 'backend' folder..."
mkdir -p backend
cd backend

# 2. Create the .env file
echo "Creating .env file..."
cat <<EOF > .env
DB_NAME=truedb
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=trueproject-db.c07cik8ugpex.us-east-1.rds.amazonaws.com
DB_PORT=5432
EOF

# 3. Create requirements.txt
echo "Creating requirements.txt..."
cat <<EOF > requirements.txt
fastapi
uvicorn
pydantic
psycopg2-binary
python-dotenv
EOF

# 4. Create database.py (Updated: Does NOT touch 'projects' table)
echo "Creating database.py..."
cat <<EOF > database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def init_db():
    """Creates tables if they don't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Students Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                usn TEXT UNIQUE NOT NULL,
                year INTEGER NOT NULL,
                sem INTEGER NOT NULL,
                dept TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # 2. Teachers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                dept TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # 3. Teams Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                team_id SERIAL PRIMARY KEY,
                team_name TEXT UNIQUE NOT NULL,
                team_size INTEGER NOT NULL,
                team_members JSONB NOT NULL
            )
        ''')

        # 4. Submitted Projects Table (New table for intake)
        # Note: We are NOT creating or touching a table named 'projects' here.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submitted_projects (
                project_id SERIAL PRIMARY KEY,
                team_id INTEGER REFERENCES teams(team_id),
                project_title TEXT NOT NULL,
                project_synopsis TEXT NOT NULL,
                status TEXT DEFAULT 'not approved'
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized (Ensured 'submitted_projects' exists; 'projects' untouched).")
    except Exception as e:
        print(f"Initialization error: {e}")
EOF

# 5. Create auth.py (Unchanged)
echo "Creating auth.py..."
cat <<EOF > auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
from database import get_db_connection

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class StudentRegister(BaseModel):
    name: str
    usn: str
    year: int
    sem: int
    dept: str
    email: str
    password: str

class TeacherRegister(BaseModel):
    name: str
    email: str
    dept: str
    password: str

@router.post("/register/student")
def register_student(student: StudentRegister):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO students (name, usn, year, sem, dept, email, password) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"
        cursor.execute(query, (student.name, student.usn, student.year, student.sem, student.dept, student.email, student.password))
        new_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return {"message": "Student registered successfully", "id": new_id, "email": student.email}
    except psycopg2.errors.UniqueViolation:
        conn.close()
        raise HTTPException(status_code=400, detail="Student with this Email or USN already exists")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login/student")
def login_student(creds: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE email = %s AND password = %s", (creds.email, creds.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"message": "Student login successful", "user_id": user['id'], "name": user['name'], "role": "student"}
    else:
        raise HTTPException(status_code=401, detail="Invalid student credentials")

@router.post("/register/teacher")
def register_teacher(teacher: TeacherRegister):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO teachers (name, dept, email, password) VALUES (%s, %s, %s, %s) RETURNING id"
        cursor.execute(query, (teacher.name, teacher.dept, teacher.email, teacher.password))
        new_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return {"message": "Teacher registered successfully", "id": new_id, "email": teacher.email}
    except psycopg2.errors.UniqueViolation:
        conn.close()
        raise HTTPException(status_code=400, detail="Teacher with this Email already exists")
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login/teacher")
def login_teacher(creds: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE email = %s AND password = %s", (creds.email, creds.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"message": "Teacher login successful", "user_id": user['id'], "name": user['name'], "role": "teacher"}
    else:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")
EOF

# 6. Create users_data.py (Unchanged)
echo "Creating users_data.py..."
cat <<EOF > users_data.py
from fastapi import APIRouter, HTTPException
from database import get_db_connection

router = APIRouter()

@router.get("/user/{email}")
def get_user_details(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        student = cursor.fetchone()
        if student:
            if 'password' in student: del student['password']
            student['role'] = 'student'
            return student
        
        cursor.execute("SELECT * FROM teachers WHERE email = %s", (email,))
        teacher = cursor.fetchone()
        if teacher:
            if 'password' in teacher: del teacher['password']
            teacher['role'] = 'teacher'
            return teacher

        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
EOF

# 7. Create teams.py (Updated: Inserts into 'submitted_projects')
echo "Creating teams.py..."
cat <<EOF > teams.py
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
EOF

# 8. Create main.py (Unchanged)
echo "Creating main.py..."
cat <<EOF > main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

# Import routers
from auth import router as auth_router
from users_data import router as users_router
from teams import router as teams_router

app = FastAPI()

# --- CORS ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)

# --- STARTUP ---
@app.on_event("startup")
def on_startup():
    init_db()
EOF

# 9. Final Instructions
echo "----------------------------------------------------"
echo "Setup Complete!"
echo ""
echo "To run the server:"
echo "1. cd backend"
echo "2. pip install -r requirements.txt"
echo "3. uvicorn main:app --reload"
echo "----------------------------------------------------"