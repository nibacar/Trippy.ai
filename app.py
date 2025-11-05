# app.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from attraction import get_route, find_attractions_along_route

GOOGLE_KEY = os.getenv("GOOGLE_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")  # tighten in prod

app = FastAPI(title="Trippy Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve /public as /
app.mount("/", StaticFiles(directory="public", html=True), name="static")

class AttrReq(BaseModel):
    origin: str
    destination: str
    n: int = 8
    step_km: float = 60.0
    radius_km: float = 12.0
    corridor_km: float = 20.0

@app.post("/api/attractions")
def api_attractions(req: AttrReq):
    if not GOOGLE_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: GOOGLE_KEY not set.")
    try:
        route = get_route(req.origin, req.destination, GOOGLE_KEY)
        picks = find_attractions_along_route(
            route["overview_poly"],
            step_km=req.step_km,
            radius_km=req.radius_km,
            key=GOOGLE_KEY,
            want=max(5, min(req.n, 10)),
            max_corridor_km=req.corridor_km
        )
        return {
            "route": {
                "start": route["start"],
                "end": route["end"],
                "total_km": route["total_km"],
                "total_hours": route["total_hours"],
                "overview_poly_encoded": route["overview_poly_encoded"],
            },
            "picks": picks
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
