# Trippy.ai

A simple AI-powered road trip planner that builds an itinerary, finds gas stops, and suggests attractions — all from just your start and end locations.

---

## 🚗 Overview

Trippy.ai helps you plan long drives easily. Just enter where you're starting and where you’re headed, and it automatically:

* Finds **attractions** along the route
* Builds a clean, organized **itinerary**

Everything runs right in your browser with a lightweight backend built using FastAPI.

---

## ✨ Features

* Automatic itinerary generation
* Attraction suggestions using built-in data
* Simple and mobile-friendly interface
* Fast, clean HTML/CSS/JS frontend

---

## 🧠 How It Works

**Frontend:** Handles routes, timings, and displays the itinerary.

**Backend:** A small FastAPI service that fetches stop and attraction data and structures it for the frontend.

```bash
frontend → FastAPI → route + attraction data → JSON response → browser display
```

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/nibacar/Trippy.ai.git
cd Trippy.ai
```

### 2. Backend (FastAPI)

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn httpx python-dotenv
```

Run the backend:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend

Open `planner.html` in your browser or serve locally:

```bash
python -m http.server 5173
```

If needed, update your API URL in the script:

```js
const API_BASE = "http://127.0.0.1:8000";
```

---

## 🧩 Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Python, FastAPI
* **Routing:** OSRM or Google Maps API
* **Hosting:** Railway or Netlify

---

## 🗺️ Roadmap

* [ ] Optimize gas stop selection based on price or rating
* [ ] Export itinerary to Google Calendar
* [ ] Shareable trip links
* [ ] Car model → MPG lookup

---

## 🤝 Contributing

1. Fork the repo
2. Create a new branch: `git checkout -b feature/idea`
3. Commit and push changes
4. Open a PR

---

## 🪪 License

MIT License © 2025 Trippy.ai
