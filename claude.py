#claude.py
import json
import os
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ANTHROPIC_API_KEY = os.getenv("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")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-2025-02-19")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY not set. Set it before starting the server.")

app = FastAPI(title="Claude Attractions Proxy")

# Allow your local dev site / frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod (e.g., ["https://your-site.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Schemas ----------

class CorridorContext(BaseModel):
    origin: str
    destination: str
    totalMiles: Optional[int] = Field(None, description="Rounded total miles")
    totalHours: Optional[float] = Field(None, description="Rounded total hours")
    corridorPlaces: List[str] = Field(default_factory=list, description="Cities/towns along route")

class ClaudeRequest(BaseModel):
    context: CorridorContext
    max_results: int = 40

class Attraction(BaseModel):
    name: str
    city: Optional[str] = None
    snippet: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    url: Optional[str] = None

class ClaudeResponse(BaseModel):
    attractions: List[Attraction] = Field(default_factory=list)

# ---------- Routes ----------

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/api/claude-attractions", response_model=ClaudeResponse)
async def claude_attractions(body: ClaudeRequest):
    """
    Ask Claude for attractions along/near a drive corridor.
    Returns normalized JSON: { "attractions": [ ... ] }
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Server missing ANTHROPIC_API_KEY")

    ctx = body.context
    max_items = max(1, min(body.max_results, 60))

    system_prompt = f"""You are a road-trip concierge. Given a drive corridor (origin, destination,
and a short list of cities/towns along the way), suggest HIGH-VALUE, iconic, or family-friendly
attractions that are plausibly along or near the route.

Rules:
- Keep it on/near the corridor from origin to destination.
- Avoid generic restaurants/hotels unless truly iconic.
- Each item needs: name, city, a concise 1–2 sentence snippet, category, a typical rating (0–5 with 0.1 precision),
  and a helpful official page URL if known.
- Output STRICT JSON with a top-level "attractions" array. No extra commentary.
- Maximum {max_items} items."""

    user_context = {
        "origin": ctx.origin,
        "destination": ctx.destination,
        "total_miles": ctx.totalMiles,
        "total_hours": ctx.totalHours,
        "corridor_places": ctx.corridorPlaces,
    }

    user_prompt = (
        "CORRIDOR CONTEXT (JSON):\n"
        + json.dumps(user_context, indent=2)
        + """

Return ONLY JSON like:
{
  "attractions": [
    {"name":"...","city":"...","snippet":"...","category":"...","rating":4.6,"url":"https://..."}
  ]
}
"""
    )

    headers = {
        "content-type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1200,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Claude error: {r.text}")
            data = r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Claude timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upstream error: {e}")

    # Anthropic returns a "content" array; we expect text JSON in content[0].text
    text = ""
    try:
        text = (data.get("content") or [{}])[0].get("text", "") or ""
        parsed = json.loads(text)
    except Exception:
        parsed = {"attractions": []}

    # Normalize & validate
    items = parsed.get("attractions") or []
    clean: List[Attraction] = []
    for it in items:
        try:
            clean.append(Attraction(**it))
        except Exception:
            # best-effort coercion
            clean.append(
                Attraction(
                    name=str(it.get("name", "Attraction")),
                    city=(it.get("city") or None),
                    snippet=(it.get("snippet") or None),
                    category=(it.get("category") or None),
                    rating=float(it["rating"]) if "rating" in it and str(it["rating"]).replace(".","",1).isdigit() else None,
                    url=(it.get("url") or None),
                )
            )

    return ClaudeResponse(attractions=clean)