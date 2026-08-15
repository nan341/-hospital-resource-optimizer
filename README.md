# Intelligent Hospital Resource Optimizer

A full-stack, real-time hospital resource-orchestration system. It ingests patient arrival data (empirical & Poisson simulated), predicts near-term demand per hospital department via seasonal rolling ML models, dynamically allocates beds, staff, and diagnostic facilities using acuity-based priority logic with critical overflow handling, and streams decision events live to a React command-center dashboard over WebSockets.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                   React + Vite Frontend (Tailwind CSS)                 │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────┐ │
│  │    Bed Map    │ │ Patient Queue │ │  Event Feed   │ │ Surge Alert │ │
│  │ (Status Grid) │ │ (Acuity/FIFO) │ │ (Live Stream) │ │ & Simulation│ │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST APIs + Live WebSocket (/ws/live)
┌───────────────────────────────────▼────────────────────────────────────┐
│                             FastAPI Backend                            │
│  ┌───────────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │    Data Pipeline      │→ │ Demand Forecast  │→ │ Priority-Queue   │ │
│  │ (Poisson + Surge Sim) │  │ (Rolling + Season)│  │ Allocation Engine│ │
│  └───────────────────────┘  └──────────────────┘  └──────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy ORM
┌───────────────────────────────────▼────────────────────────────────────┐
│                    SQLite Database (data/hospital.db)                  │
│  departments, beds, staff, diagnostic_facilities, patients, events_log │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
hospital-resource-optimizer/
├── data/
│   ├── raw/                      # Downloaded Kaggle CSVs (optional)
│   ├── processed/                # Calibrated distributions (calibration.json)
│   ├── synthetic/                # Generated simulation data
│   └── hospital.db               # SQLite database
├── models/
│   ├── demand_forecast/          # Saved model parameters
│   └── allocation/               # Learned allocation policies
├── src/
│   ├── data_pipeline/
│   │   ├── kaggle_loader.py       # Kaggle dataset loader with fallback
│   │   ├── calibration.py         # Hourly multipliers, acuity mix, LOS params
│   │   └── synthetic_generator.py # Time-varying Poisson arrival simulator & surge engine
│   ├── models/
│   │   ├── forecasting.py         # Seasonality-adjusted demand forecaster
│   │   └── train.py               # Empirical recalibration entrypoint
│   ├── allocation/
│   │   ├── engine.py              # Priority-queue bed, diagnostic, and staff allocation
│   │   └── rules.py               # Critical overflow search and staff rebalancing
│   ├── api/
│   │   ├── main.py                # FastAPI application, CORS & WebSocket manager
│   │   ├── db.py                  # SQLAlchemy engine and session dependency
│   │   ├── schemas.py             # Pydantic v2 validation models
│   │   └── routes/
│   │       ├── patients.py        # Patient query endpoints
│   │       ├── beds.py            # Bed status endpoints
│   │       ├── staff.py           # Clinical staff endpoints
│   │       └── events.py          # Event log feed endpoints
│   └── db/
│       ├── models.py              # SQLAlchemy ORM models
│       └── init_db.py             # Schema creation & seeding script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── BedMap.jsx         # Live bed grid by department & diagnostic badge
│   │   │   ├── PatientQueue.jsx   # Priority triage queue (ESI 1-5)
│   │   │   ├── EventFeed.jsx      # Streaming decision event feed
│   │   │   └── SurgeAlert.jsx     # Capacity warning banner & simulation controls
│   │   ├── App.jsx                # Command center dashboard with KPI ribbon & forecast charts
│   │   ├── api.js                 # Axios API client & WebSocket URL
│   │   └── index.css              # Tailwind CSS styles
│   └── package.json
├── tests/
│   ├── test_allocation.py         # Priority queue, overflow & diagnostic unit tests
│   ├── test_forecasting.py        # Demand forecasting tests
│   └── test_api.py                # FastAPI REST endpoint integration tests
├── scripts/
│   ├── seed_db.py                 # Clean database reset utility
│   └── run_simulation.py          # Standalone simulation CLI runner
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quickstart & Setup

### 1. Backend Setup

From the `hospital-resource-optimizer/` directory:

```bash
# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies (already installed in workspace)
pip install -r requirements.txt

# Reset and seed database
python scripts/seed_db.py
```

### 2. Start the FastAPI Backend

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

* API Docs (Swagger UI): `http://127.0.0.1:8000/docs`
* Live WebSocket Endpoint: `ws://127.0.0.1:8000/ws/live`

### 3. Start the React Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

* Open your browser at: `http://127.0.0.1:5173`

---

## Live Demo Scenario (Surge & Critical Overflow)

1. Open the dashboard at `http://127.0.0.1:5173`.
2. Click **Start Sim** in the simulation ribbon to start Poisson arrivals (running at 2.5x speed).
3. Observe patient arrivals queueing in the **Triage Waiting Queue** and automatically being assigned beds in the **Bed Map**.
4. In the **Surge Controller**, select `Emergency Room (ER)` and `8 pts (Saturate)` and click **Trigger Surge**.
5. Watch the automated allocation decisions in the **Real-Time Decisions Feed**:
   - Primary ER beds become fully occupied (8/8).
   - Subsequent critical trauma patients automatically trigger **CRITICAL OVERFLOW ROUTING** to available beds in General Ward or ICU.
   - Diagnostic facilities (e.g. Trauma CT Scanner, Emergency Digital X-Ray) are paired with admitted patients.
   - Staff rebalancing evaluates 2-hour projected load and reassigns personnel to high-burden departments.
6. Click **Reset DB** at any time to restore fresh baseline capacity.

---

## Running the Automated Test Suite

Run the full pytest suite:

```bash
pytest tests/ -v
```

All 11 unit and integration tests verify:
- Priority-queue severity ordering (`critical` > `moderate` > `low`) and FIFO tiebreaking.
- Primary bed assignment and automatic diagnostic facility pairing (`in_use` status).
- Critical overflow routing to the lowest-occupancy alternative department.
- Demand forecasting calculation with 80% Poisson confidence intervals.
- All REST endpoints (`/departments`, `/beds`, `/patients`, `/staff`, `/events`, `/diagnostics`, `/forecast/{id}`, `/simulation/*`).

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/departments` | List all departments with bed counts, occupancy %, and diagnostic availability |
| `GET` | `/beds?department_id=` | List beds with status (`available`, `occupied`, `cleaning`, `reserved`) |
| `GET` | `/patients?status=waiting` | List patients with optional status and department filter |
| `GET` | `/diagnostics?department_id=` | List diagnostic equipment with current operational status |
| `GET` | `/staff?department_id=` | List medical staff on duty |
| `GET` | `/events?limit=50` | Recent allocation and simulation event audit trail |
| `GET` | `/forecast/{department_id}` | 2-hour rolling demand forecast with confidence intervals |
| `POST` | `/simulation/start` | Start synthetic patient Poisson arrival background loop |
| `POST` | `/simulation/stop` | Pause synthetic simulator |
| `POST` | `/simulation/surge` | Trigger deterministic burst of critical patients |
| `POST` | `/simulation/reset` | Reset database to clean seeded initial state |
| `GET` | `/simulation/status` | Current simulation status and patient metrics |
| `WS` | `/ws/live` | Bidirectional WebSocket pushing state updates every 2.5s |
