# attraction.py
import os
import sys
import json
import math
import argparse
import urllib.request
import urllib.parse

GOOGLE_KEY = os.getenv("GOOGLE_KEY", "REPLACE_ME_FOR_LOCAL_DEV")

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
PLACES_NEARBY_V1 = "https://places.googleapis.com/v1/places:searchNearby"

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
    R = 6371.0088
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(h))

def distance_point_to_segment_km(p, a, b):
    lat_avg = math.radians((a[0]+b[0])/2.0)
    x1, y1 = math.radians(a[1]), math.radians(a[0])
    x2, y2 = math.radians(b[1]), math.radians(b[0])
    xp, yp = math.radians(p[1]), math.radians(p[0])

    scale_x = math.cos(lat_avg)
    ax, ay = (x1*scale_x, y1)
    bx, by = (x2*scale_x, y2)
    px, py = (xp*scale_x, yp)

    vx, vy = (bx-ax, by-ay)
    wx, wy = (px-ax, py-ay)
    v2 = vx*vx + vy*vy
    if v2 == 0:
        return haversine_km(p, a)
    t = max(0, min(1, (wx*vx + wy*vy)/v2))
    projx, projy = (ax + t*vx, ay + t*vy)
    proj = (math.degrees(projy), math.degrees(projx/scale_x))
    return haversine_km(p, proj)

def min_distance_point_to_polyline_km(p, poly):
    best = 1e9
    for i in range(len(poly)-1):
        d = distance_point_to_segment_km(p, poly[i], poly[i+1])
        if d < best: best = d
    return best

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
            if b < 0x20: break
        dlat = ~(result >> 1) if result & 1 else (result >> 1)
        lat += dlat
        shift = result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20: break
        dlng = ~(result >> 1) if result & 1 else (result >> 1)
        lng += dlng
        coords.append((lat / 1e5, lng / 1e5))
    return coords

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

def score_place(p, route_poly, max_corridor_km):
    lat = p["location"]["latitude"]
    lng = p["location"]["longitude"]
    rating = p.get("rating", 0) or 0
    ur = p.get("userRatingCount", 0) or 0
    dist_km = min_distance_point_to_polyline_km((lat,lng), route_poly)
    corridor_penalty = 0.0 if dist_km <= max_corridor_km else (dist_km - max_corridor_km) * 0.2
    return (rating) + 0.005 * math.log1p(max(0, ur)) - corridor_penalty, dist_km

def find_attractions_along_route(route_poly, step_km=60, radius_km=12, key=None, want=8, max_corridor_km=20):
    samples = sample_along(route_poly, step_km)
    by_id = {}
    for (lat, lng) in samples:
        places = places_nearby_v1(lat, lng, radius_km*1000, key, max_count=20)
        for p in places:
            pid = p.get("id") or p.get("name")
            if not pid:
                continue
            if pid not in by_id:
                by_id[pid] = p

    ranked = []
    for pid, p in by_id.items():
        s, dkm = score_place(p, route_poly, max_corridor_km)
        ranked.append((s, dkm, p))
    ranked.sort(key=lambda x: x[0], reverse=True)

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
