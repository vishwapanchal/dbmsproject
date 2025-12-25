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
            client_encoding='UTF8',
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

        # 4. Submitted Projects Table
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
        print("Database initialized.")
    except Exception as e:
        print(f"Initialization error: {e}")
