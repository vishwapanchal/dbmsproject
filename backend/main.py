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
