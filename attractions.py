# attractions.py
# Usage:
#   export GOOGLE_MAPS_API_KEY="YOUR_KEY"
#   python3 attractions.py "San Diego, CA" "Phoenix, AZ" --n 8 --step-km 60 --radius-km 12
#
# Outputs:
#   - Prints 5–10 top attractions along the route
#   - Writes an interactive map file: map.html (open it in a browser)

import os
import sys
import json
import math
import argparse
import urllib.request
import urllib.parse

GOOGLE_KEY = "AIzaSyCr1WhJtX6cLLu6UCMUVGiKm4mnmuGD6E8"
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
PLACES_NEARBY_V1 = "https://places.googleapis.com/v1/places:searchNearby"

# ---------- small helpers ----------

def http_post_json(url, body_dict, headers):
    data = json.dumps(body_dict).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_get(url, params):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full) as resp:
        return json.loads(resp.read().decode("utf-8"))

def haversine_km(a, b):
    # a=(lat,lng), b=(lat,lng)
    R = 6371.0088
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(h))

def distance_point_to_segment_km(p, a, b):
    # perpendicular distance from p to line segment ab (in km)
    # convert to Cartesian on unit sphere approx via equirectangular projection (good for short segments)
    lat_avg = math.radians((a[0]+b[0])/2.0)
    x1, y1 = math.radians(a[1]), math.radians(a[0])
    x2, y2 = math.radians(b[1]), math.radians(b[0])
    xp, yp = math.radians(p[1]), math.radians(p[0])

    scale_x = math.cos(lat_avg)
    ax, ay = (x1*scale_x, y1)
    bx, by = (x2*scale_x, y2)
    px, py = (xp*scale_x, yp)

    # projection
    vx, vy = (bx-ax, by-ay)
    wx, wy = (px-ax, py-ay)
    v2 = vx*vx + vy*vy
    if v2 == 0:
        return haversine_km(p, a)
    t = max(0, min(1, (wx*vx + wy*vy)/v2))
    projx, projy = (ax + t*vx, ay + t*vy)
    # convert back to degrees for haversine distance
    proj = (math.degrees(projy), math.degrees(projx/scale_x))
    return haversine_km(p, proj)

def min_distance_point_to_polyline_km(p, poly):
    best = 1e9
    for i in range(len(poly)-1):
        d = distance_point_to_segment_km(p, poly[i], poly[i+1])
        if d < best: best = d
    return best

# ----- polyline decoding (Google’s algorithm) -----

def decode_polyline(polyline_str):
    coords = []
    index = lat = lng = 0
    length = len(polyline_str)

    while index < length:
        shift = result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else (result >> 1)
        lat += dlat

        shift = result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else (result >> 1)
        lng += dlng

        coords.append((lat / 1e5, lng / 1e5))
    return coords

# sample every step_km along polyline by walking arc length
def sample_along(poly, step_km):
    if not poly: return []
    out = [poly[0]]
    acc = 0.0
    for i in range(1, len(poly)):
        seg = haversine_km(poly[i-1], poly[i])
        while acc + seg >= step_km:
            remain = step_km - acc
            t = remain / seg if seg > 0 else 0
            lat = poly[i-1][0] + t*(poly[i][0]-poly[i-1][0])
            lng = poly[i-1][1] + t*(poly[i][1]-poly[i-1][1])
            out.append((lat, lng))
            seg -= remain
            acc = 0.0
        acc += seg
    out.append(poly[-1])
    return out

# ---------- Google calls ----------

def get_route(origin, destination, key):
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "alternatives": "false",
        "key": key,
        "departure_time": "now"
    }
    data = http_get(DIRECTIONS_URL, params)
    if data.get("status") != "OK" or not data.get("routes"):
        raise RuntimeError(f"Directions error: {data.get('status')}")
    route = data["routes"][0]
    leg = route["legs"][0]
    poly = decode_polyline(route["overview_polyline"]["points"])
    total_km = sum(l["distance"]["value"] for l in route["legs"]) / 1000.0
    total_sec = sum(l["duration"]["value"] for l in route["legs"])
    return {
        "overview_poly": poly,
        "overview_poly_encoded": route["overview_polyline"]["points"],
        "start": leg["start_address"],
        "end": leg["end_address"],
        "total_km": total_km,
        "total_hours": round(total_sec / 3600.0, 2)
    }

def places_nearby_v1(center_lat, center_lng, radius_m, key, max_count=20):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.primaryType"
    }
    body = {
        "includedTypes": ["tourist_attraction","park","museum","art_gallery"],
        "maxResultCount": max_count,
        "rankPreference": "POPULARITY",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": center_lat, "longitude": center_lng},
                "radius": float(radius_m)
            }
        }
    }
    j = http_post_json(PLACES_NEARBY_V1, body, headers)
    return j.get("places", [])

# ---------- core ranking ----------

def score_place(p, route_poly, max_corridor_km):
    lat = p["location"]["latitude"]
    lng = p["location"]["longitude"]
    rating = p.get("rating", 0) or 0
    ur = p.get("userRatingCount", 0) or 0
    dist_km = min_distance_point_to_polyline_km((lat,lng), route_poly)
    # soft-penalize beyond corridor
    corridor_penalty = 0.0 if dist_km <= max_corridor_km else (dist_km - max_corridor_km) * 0.2
    # combine rating + volume + distance penalty
    return (rating) + 0.005 * math.log1p(max(0, ur)) - corridor_penalty, dist_km

def find_attractions_along_route(route_poly, step_km=60, radius_km=12, key=None, want=8, max_corridor_km=20):
    samples = sample_along(route_poly, step_km)
    by_id = {}
    for (lat, lng) in samples:
        places = places_nearby_v1(lat, lng, radius_km*1000, key, max_count=20)
        for p in places:
            pid = p.get("id") or p.get("name")  # v1 has "id"
            if not pid: 
                continue
            if pid not in by_id:
                by_id[pid] = p

    # rank with score
    ranked = []
    for pid, p in by_id.items():
        s, dkm = score_place(p, route_poly, max_corridor_km)
        ranked.append((s, dkm, p))
    ranked.sort(key=lambda x: x[0], reverse=True)

    # final top N, prefer within corridor
    picks = []
    seen_names = set()
    for s, dkm, p in ranked:
        name = p["displayName"]["text"]
        if name.lower() in seen_names:
            continue
        picks.append({
            "name": name,
            "lat": p["location"]["latitude"],
            "lng": p["location"]["longitude"],
            "rating": p.get("rating", None),
            "reviews": p.get("userRatingCount", 0),
            "mapsUri": p.get("googleMapsUri", ""),
            "type": p.get("primaryType", ""),
            "distanceFromRouteKm": round(dkm, 2)
        })
        seen_names.add(name.lower())
        if len(picks) >= want:
            break
    return picks

# ---------- HTML output ----------

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Route + Attractions</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body{margin:0;font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial}
    #map{height:70vh;width:100%}
    .wrap{max-width:1000px;margin:12px auto;padding:0 12px}
    h1{font-size:20px;margin:12px 0}
    .card{border:1px solid #e6e8ee;border-radius:12px;padding:10px;margin:8px 0}
    .muted{color:#6b7280;font-size:14px}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="wrap">
    <h1>Top attractions along: {start} → {end}</h1>
    <div class="muted">~{km} km • ~{hrs} hours • showing {count} picks</div>
    {cards}
  </div>

  <script>
    const polylineEncoded = "{poly}";
    const attractions = {markers_json};

    function decodePolyline(str) {{
      let index = 0, lat = 0, lng = 0, coords = [];
      while (index < str.length) {{
        let b, shift = 0, result = 0;
        do {{ b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; }} while (b >= 0x20);
        const dlat = (result & 1) ? ~(result >> 1) : (result >> 1); lat += dlat;
        shift = 0; result = 0;
        do {{ b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; }} while (b >= 0x20);
        const dlng = (result & 1) ? ~(result >> 1) : (result >> 1); lng += dlng;
        coords.push({{lat: lat/1e5, lng: lng/1e5}});
      }}
      return coords;
    }}

    let map, path;
    function init() {{
      map = new google.maps.Map(document.getElementById('map'), {{
        center: {{lat: 39.5, lng: -98.35}}, zoom: 5, mapTypeControl:false
      }});

      const pts = decodePolyline(polylineEncoded);
      path = new google.maps.Polyline({{
        path: pts, map, strokeWeight: 6
      }});

      // fit bounds
      const b = new google.maps.LatLngBounds();
      pts.forEach(p => b.extend(p));
      attractions.forEach(a => b.extend({{lat:a.lat,lng:a.lng}}));
      map.fitBounds(b);

      // markers
      attractions.forEach((a, i) => {{
        const m = new google.maps.Marker({{
          position: {{lat:a.lat,lng:a.lng}}, map, label: String(i+1)
        }});
        const html = `<div><strong>${{i+1}}. ${{a.name}}</strong><br>
          Rating: ${{a.rating ?? '—'}} (${{
            a.reviews ?? 0
          }} reviews)<br>
          ~${{a.distanceFromRouteKm}} km off route<br>
          <a href="${{a.mapsUri}}" target="_blank" rel="noopener">Open in Google Maps</a></div>`;
        const inf = new google.maps.InfoWindow({{content: html}});
        m.addListener('click', () => inf.open({{map, anchor: m}}));
      }});
    }}
    window.initMap = init;
  </script>
  <script src="https://maps.googleapis.com/maps/api/js?key={key}&callback=init" async defer></script>
</body>
</html>
"""

def render_cards(items):
    out = []
    for i,a in enumerate(items, start=1):
        out.append(
            f'<div class="card"><strong>{i}. {a["name"]}</strong><br>'
            f'Rating: {a.get("rating","—")} ({a.get("reviews",0)} reviews) • '
            f'~{a["distanceFromRouteKm"]} km off route<br>'
            f'<a href="{a.get("mapsUri","")}" target="_blank" rel="noopener">Open in Google Maps</a></div>'
        )
    return "\n".join(out)

# ---------- main ----------

def main():
    if not GOOGLE_KEY:
        print("ERROR: Set GOOGLE_MAPS_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    ap = argparse.ArgumentParser()
    ap.add_argument("origin", help="Start address or place")
    ap.add_argument("destination", help="Destination address or place")
    ap.add_argument("--n", type=int, default=8, help="How many attractions to return (5–10 recommended)")
    ap.add_argument("--step-km", type=float, default=60.0, help="Sampling interval along the route (km)")
    ap.add_argument("--radius-km", type=float, default=12.0, help="Search radius around each sample (km)")
    ap.add_argument("--corridor-km", type=float, default=20.0, help="Soft corridor width before distance penalty (km)")
    args = ap.parse_args()

    route = get_route(args.origin, args.destination, GOOGLE_KEY)
    picks = find_attractions_along_route(
        route["overview_poly"],
        step_km=args.step_km,
        radius_km=args.radius_km,
        key=GOOGLE_KEY,
        want=max(5, min(args.n, 10)),
        max_corridor_km=args.corridor_km
    )

    # Print results
    print(f"\nRoute: {route['start']} → {route['end']}  (~{round(route['total_km'])} km, ~{route['total_hours']} h)")
    if not picks:
        print("No attractions found near the route. Try increasing --radius-km or --step-km.")
    else:
        for i,a in enumerate(picks, start=1):
            print(f"{i}. {a['name']}  | ⭐ {a.get('rating','—')} ({a.get('reviews',0)} reviews) "
                  f"| {a['distanceFromRouteKm']} km off | {a.get('mapsUri','')}")

    # Write map
    cards_html = render_cards(picks)
    html = HTML_TEMPLATE.format(
        start=route["start"],
        end=route["end"],
        km=round(route["total_km"]),
        hrs=route["total_hours"],
        count=len(picks),
        poly=route["overview_poly_encoded"],
        markers_json=json.dumps(picks),
        key=GOOGLE_KEY,
        cards=cards_html
    )
    with open("map.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\nWrote map.html — open it in your browser to view the route + markers.")

if __name__ == "__main__":
    main()
