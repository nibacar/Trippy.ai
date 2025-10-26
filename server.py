# server.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

# Your existing logic module
import attractions  # must be in the same folder as this file

app = Flask(__name__, static_folder=".", static_url_path="")
# CORS is harmless here and useful if you ever open the HTML from file:// by accident
CORS(app, resources={r"/api/*": {"origins": "*"}})

def _resolve_api_key():
    """
    Prefer the key defined in attractions.py (GOOGLE_KEY),
    otherwise fall back to the environment variable.
    """
    key = getattr(attractions, "GOOGLE_KEY", None)
    if key and isinstance(key, str) and key.strip():
        return key.strip()
    env_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if env_key:
        return env_key
    return None

@app.get("/api/health")
def health():
    return jsonify({"ok": True})

@app.get("/")
def home():
    # Serve your planner.html from the same folder as server.py
    return send_from_directory(".", "planner.html")

@app.post("/api/attractions")
def api_attractions():
    """
    Body:
      {
        "origin": "San Diego, CA",
        "destination": "Phoenix, AZ",
        // optional tuning:
        "n": 8,
        "step_km": 60.0,
        "radius_km": 12.0,
        "corridor_km": 20.0
      }
    """
    data = request.get_json(silent=True) or {}
    origin = data.get("origin")
    destination = data.get("destination")

    if not origin or not destination:
        return jsonify({"error": "Missing 'origin' or 'destination'"}), 400

    # Optional knobs (defaults mirror your script)
    want = int(data.get("n", 8))
    step_km = float(data.get("step_km", 60.0))
    radius_km = float(data.get("radius_km", 12.0))
    corridor_km = float(data.get("corridor_km", 20.0))

    key = _resolve_api_key()
    if not key:
        return jsonify({"error": "No Google Maps API key found. Set attractions.GOOGLE_KEY or GOOGLE_MAPS_API_KEY."}), 500

    try:
        # 1) Get route (polyline, distance, etc.)
        route = attractions.get_route(origin, destination, key)

        # 2) Find attractions along the route
        picks = attractions.find_attractions_along_route(
            route_poly=route["overview_poly"],
            step_km=step_km,
            radius_km=radius_km,
            key=key,
            want=max(5, min(want, 10)),       # keep 5–10 like your CLI
            max_corridor_km=corridor_km
        )

        return jsonify({
            "route": {
                "start": route["start"],
                "end": route["end"],
                "total_km": round(route["total_km"]),
                "total_hours": route["total_hours"],
                "polyline": route["overview_poly_encoded"]
            },
            "attractions": picks
        })
    except Exception as e:
        # Bubble up a readable error to the UI & console
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500

if __name__ == "__main__":
    # Use 5001 to match your planner.html flow; same-origin when you visit http://127.0.0.1:5001/
    app.run(host="0.0.0.0", port=5001, debug=True)
