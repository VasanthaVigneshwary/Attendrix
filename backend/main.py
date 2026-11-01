import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routes import students, attendance, dashboard, evaluation
from backend.database import init_db

# ─── App factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="ATTENDRIX",
    description="Smart Classroom Attendance System Using Deep Learning-Based Face Recognition",
    version="1.0.0",
)

# Allow browser requests from any origin (OK for academic prototype)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(dashboard.router)
app.include_router(evaluation.router)

# ─── Serve the frontend ───────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    init_db()
    print("ATTENDRIX backend started. Database initialized.")

# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "app": "ATTENDRIX"}
