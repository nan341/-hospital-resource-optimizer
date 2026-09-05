# Intelligent Hospital Resource Optimizer

A full-stack, real-time hospital resource-orchestration system. It ingests patient arrival data, predicts near-term demand per department via seasonal rolling ML models, dynamically allocates beds, staff, and diagnostic facilities using acuity-based priority logic with critical overflow routing, manages outpatient appointment queues (OPD & ENT), and provides **three role-separated interfaces** (Admin, Clinical Staff, and Patient Portal) over WebSockets and REST APIs.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│               React + Vite Frontend (3 Distinct Interfaces)            │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌─────────────────┐  │
│  │   /admin (Dashboard) │ │ /staff (Staff Portal)│ │ /patient (Portal│  │
│  │  - Bed Map & Queue   │ │ - Duty Roster        │ │ - Public Avail  │  │
│  │  - ICU Surge Controls│ │ - Case Notifications │ │ - OPD/ENT Appts │  │
│  │  - 2hr Demand Chart  │ │ - Active Consults    │ │ - Live Ticket Q │  │
│  └──────────────────────┘ └──────────────────────┘ └─────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST APIs (JWT Auth) + WebSocket (/ws/live)
┌───────────────────────────────────▼────────────────────────────────────┐
│                             FastAPI Backend                            │
│  ┌───────────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │    Data Pipeline      │→ │ Demand Forecast  │→ │ Priority-Queue   │ │
│  │ (Poisson + Surge Sim) │  │ (Rolling + Season)│  │ Allocation Engine│ │
│  └───────────────────────┘  └──────────────────┘  └─────────┬────────┘ │
│                                                             │          │
│  ┌───────────────────────┐  ┌──────────────────┐            │          │
│  │  Outpatient Scheduler │  │ Role Auth System │            │          │
│  │ (OPD/ENT Doctor Queue)│  │ (Admin & Staff)  │←───────────┘          │
│  └───────────────────────┘  └──────────────────┘                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy ORM
┌───────────────────────────────────▼────────────────────────────────────┐
│                    SQLite Database (data/hospital.db)                  │
│  departments, beds, staff, diagnostic_facilities, patients,            │
│  appointments, staff_notifications, events_log                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Authentication & Portals

The application features three isolated interfaces with strict role separation:

| Portal | URL Route | Access Control | Features |
|---|---|---|---|
| **Landing Gateway** | `/` | Public | Portal selection interface |
| **Administration** | `/admin` | `admin` JWT (Pass: `changeme`) | Executive dashboard, bed map, ICU overflow, staff rebalancing, ML forecast, simulation & surge controls |
| **Clinical Staff** | `/staff` | `staff` JWT (Code: `staff123`) | Duty roster, on/off-duty toggle, active admitted patients with age/chief complaint, live doctor consultation queue, alert notifications |
| **Patient Services** | `/patient` | **Public (No Login)** | Qualitative service availability (Available / Full, no raw numbers leaked), OPD & ENT online appointment booking, live ticket queue checker |

---

## 🚀 Quickstart & Setup

### 1. Backend Setup

From the project root:

```powershell
# 1. Activate virtual environment
.\venv\Scripts\activate

# 2. Initialize and seed database
python src/db/init_db.py --reset

# 3. Start FastAPI server
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open your browser at: **`http://127.0.0.1:5173`**

---

## 🌐 LAN / Client-Server Deployment

To run the backend server on one laptop and connect multiple client devices (e.g. tablet for patient portal, doctor laptop for staff portal, admin station for hospital command center) over the same local network:

### 1. Server Laptop Configuration:
1. Find your Server Laptop's local IP address:
   ```powershell
   # In Windows PowerShell:
   ipconfig
   # Look for IPv4 Address under your Wi-Fi/Ethernet adapter (e.g., 192.168.1.50)
   ```
2. Start the FastAPI backend listening on all network interfaces:
   ```powershell
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Ensure Windows Firewall allows inbound TCP connections on port `8000`.

### 2. Client Device Configuration:
1. In `frontend/.env` (or via environment variables), set the server IP:
   ```env
   VITE_API_BASE=http://192.168.1.50:8000
   VITE_WS_BASE=ws://192.168.1.50:8000
   ```
2. Run the frontend or build for distribution:
   ```powershell
   npm run dev -- --host
   ```
3. Navigate to `http://192.168.1.50:5173` from any phone, tablet, or laptop connected to the same Wi-Fi.

---

## 🧪 Automated Testing

Run the full pytest suite (17 tests covering allocation, forecasting, auth, patient portal, and staff portal):

```powershell
.\venv\Scripts\pytest tests/ -v
```

---

## 📊 Summary of Core Algorithms

- **Priority Queue Allocation**: Acuity-weighted sorting (Critical ESI 1 $\rightarrow$ Moderate ESI 2-3 $\rightarrow$ Low ESI 4-5 $\rightarrow$ FIFO arrival timestamp).
- **Critical Overflow Routing**: When intensive care or primary wards are at 100% capacity, critical patients are safely diverted to the lowest-occupancy compatible department.
- **Protected Staff Rebalancing**: Overloaded departments receive reallocated staff from slack departments (General Ward) while clinical safety invariants strictly protect ICU from donating staff.
- **Load-Aware Staff Assignment**: Inpatient arrivals and outpatient appointments are dispatched to the least-burdened on-duty physician or nurse.
- **Outpatient Scheduling**: OPD & ENT consultations are scheduled with instant queue position tickets, automated queue advancement, and direct physician notifications.
