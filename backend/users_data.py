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
