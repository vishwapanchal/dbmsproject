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

# --------------------------
# STUDENT ROUTES
# --------------------------

@router.post("/register/student")
def register_student(student: StudentRegister):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # UPDATED: Returns 'student_id' instead of 'id'
        query = """
        INSERT INTO students (name, usn, year, sem, dept, email, password) 
        VALUES (%s, %s, %s, %s, %s, %s, %s) 
        RETURNING student_id
        """
        cursor.execute(query, (student.name, student.usn, student.year, student.sem, student.dept, student.email, student.password))
        
        # UPDATED: Access 'student_id'
        new_id = cursor.fetchone()['student_id']
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
        # UPDATED: Access 'student_id'
        return {"message": "Student login successful", "user_id": user['student_id'], "name": user['name'], "role": "student"}
    else:
        raise HTTPException(status_code=401, detail="Invalid student credentials")

# --------------------------
# TEACHER ROUTES
# --------------------------

@router.post("/register/teacher")
def register_teacher(teacher: TeacherRegister):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # UPDATED: Returns 'teacher_id' instead of 'id'
        query = "INSERT INTO teachers (name, dept, email, password) VALUES (%s, %s, %s, %s) RETURNING teacher_id"
        cursor.execute(query, (teacher.name, teacher.dept, teacher.email, teacher.password))
        
        # UPDATED: Access 'teacher_id'
        new_id = cursor.fetchone()['teacher_id']
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
        # UPDATED: Access 'teacher_id'
        return {"message": "Teacher login successful", "user_id": user['teacher_id'], "name": user['name'], "role": "teacher"}
    else:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")