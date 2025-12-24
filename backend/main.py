from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

# Import routers
from auth import router as auth_router
from users_data import router as users_router
from teams import router as teams_router
from projects import router as projects_router
from project_phases import router as phases_router
from project_status import router as status_router

app = FastAPI()

origins = [
    "http://localhost:3000",  # React default port
"http://localhost:5173",  # Vite default port (if you used Vite)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],    # Allow all methods (POST, GET, etc.)
    allow_headers=["*"],
)

# --- ROUTES ---
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(teams_router)
app.include_router(projects_router)
app.include_router(phases_router)
app.include_router(status_router)

# --- STARTUP ---
@app.on_event("startup")
def on_startup():
    init_db()
