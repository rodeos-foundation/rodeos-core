from fastapi import FastAPI
from rodeos.core.database import init_db
from rodeos.api.observations import router as observations_router

app = FastAPI(title="RodeOS", version="1.0.0")

# Initialize database tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Register API routers
app.include_router(observations_router)

@app.get("/")
def read_root():
    return {"project": "RodeOS", "status": "active"}