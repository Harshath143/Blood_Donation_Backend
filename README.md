# 🩸 LifeDrop Backend

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)

LifeDrop Backend is a production-grade, asynchronous REST API designed for **LifeDrop**—a healthcare platform that connects blood donors, hospitals, and blood banks in real time. It utilizes PostGIS-powered geospatial queries to search and match donors within dynamic distances, schedules and processes asynchronous task queues, and utilizes WebSockets for real-time dispatch and notification updates.

---

## 🚀 Key Features

* **Geospatial Donor Search**: Uses PostGIS and GeoAlchemy2 to execute `ST_DWithin` and `ST_Distance` queries, enabling fast location-based matching of eligible donors to blood requests.
* **Dynamic Matching & Scoring Engine**: Ranks compatible donors by proximity, availability, emergency flags, and donation history using a multi-factor mathematical formula.
* **Real-time Communication**: Persistent WebSocket connection manager for instant match alerts and notification dispatches to users and hospitals.
* **Background Worker Queues**: Celery task runner for asynchronous email dispatch (welcome, OTP, request alerts, donation reminders) and database/cache cleanup jobs.
* **Robust Security & Auth**: Password hashing using `bcrypt`, JWT access/refresh token rotation, endpoint-level role checks, and Redis-backed rate limiting.
* **Structured Logging & Auditing**: JSON-formatted structured logging via `structlog` for observability, along with persistent audit logging for critical operations.
* **Database Migrations**: Streamlined database schema version control using Alembic.

---

## 🛠️ Technology Stack

* **Web Framework**: [FastAPI](https://fastapi.tiangolo.com) (Asynchronous REST API)
* **Database ORM**: [SQLAlchemy (Asyncio)](https://www.sqlalchemy.org)
* **Database Driver**: [asyncpg](https://github.com/MagicStack/asyncpg) (Async PostgreSQL driver)
* **Spatial Extensions**: [GeoAlchemy2](https://geoalchemy2.readthedocs.io) & [PostGIS](https://postgis.net)
* **Caching & Queue Broker**: [Redis](https://redis.io)
* **Background Task Queue**: [Celery](https://docs.celeryq.dev) & [Flower](https://github.com/mher/flower) (Task dashboard)
* **Security & Encryption**: [python-jose](https://github.com/mpdavis/python-jose) (JWT), [passlib](https://passlib.readthedocs.io) & [bcrypt](https://github.com/pyca/bcrypt)
* **Configuration Management**: [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
* **Logging**: [structlog](https://www.structlog.org)
* **Testing**: [pytest](https://docs.pytest.org) & [httpx](https://www.python-httpx.org)

---

## 📂 Project Structure

The project follows a modular, clean-architecture/DDD structure:

```text
Blood_Donation_Backend/
├── app/
│   ├── api/                   # Routing & controller layer
│   │   └── v1/
│   │       ├── endpoints/     # Feature-specific endpoints (auth, donors, blood_requests, etc.)
│   │       └── router.py      # Root API v1 router definition
│   ├── core/                  # Security, rate limiting, middlewares & system exceptions
│   ├── models/                # SQLAlchemy database models (PostgreSQL & PostGIS schemas)
│   ├── repositories/          # Data access layer (encapsulating SQLAlchemy database queries)
│   ├── services/              # Business logic layer (auth, matching, geolocation, notifications)
│   ├── tasks/                 # Celery workers and task schedules (email, reminders, matching)
│   ├── templates/             # Jinja2 templates (transactional email templates)
│   ├── websocket/             # WebSocket connections and broadcast managers
│   ├── config.py              # Configuration schemas & environment loading
│   ├── database.py            # Database engines, sessions, and pool configurations
│   ├── dependencies.py        # Shared FastAPI dependencies (authentication, rate-limiters, etc.)
│   └── main.py                # Application entrypoint & exception handlers
├── migrations/                # Alembic database migration scripts
├── tests/                     # Asynchronous test suite (pytest)
├── alembic.ini                # Alembic configuration
├── pyproject.toml             # Python package dependencies & tool settings
└── .env.example               # Example template for environment variables
```

---

## 🧠 Core Systems Detail

### 1. Geospatial Donor Matching Algorithm

When a blood request is created, the system attempts to find eligible, compatible donors in expanding distance bands: **10 km ➔ 25 km ➔ 50 km ➔ 100 km**.

The query filters out donors who:

* Are set to `unavailable` or have donated within the last **56 days** (standard red blood cell donation recovery period).
* Do not have a compatible blood type.
* Are not verified/active users.

#### Donor Scoring Formula (Max 100 Points)

For matches within the range, candidates are scored and ranked to notify the best matches first:

1. **Blood Type Match (`+40 pts`)**: Awarded if the donor's blood type exactly matches the requested type.
2. **Proximity (`Max 30 pts`)**: Calculated as `30 - (distance_km * 0.3)`. Closer donors receive a higher score.
3. **Emergency Status (`+15 pts`)**: Awarded if the donor has enabled their emergency availability flag.
4. **General Availability (`+10 pts`)**: Awarded if the donor's availability is set to `always`.
5. **Donation History (`Capped at 5 pts`)**: `+1 pt` per verified past donation.

### 2. Real-Time WebSocket Updates

A persistent connection manager handles WebSocket channels for logged-in users and hospitals. When a match is made, the platform instantly triggers a `match_found` event to the requester, displaying matching donor statistics, search radii, and coordinates.

---

## ⚙️ Setup & Local Installation

### Prerequisites

* **Python**: `>= 3.12`
* **PostgreSQL**: `>= 14` with the **PostGIS** extension installed.
* **Redis**: Local server or cloud instance (used as a cache, rate limiter, and Celery broker).

### Step-by-Step Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/your-username/Blood_Donation_Backend.git
   cd Blood_Donation_Backend
   ```
2. **Create a Virtual Environment**:

   ```bash
   # Create the environment
   python -m venv .venv

   # Activate the environment (Windows)
   .venv\Scripts\activate

   # Activate the environment (macOS/Linux)
   source .venv/bin/activate
   ```
3. **Install Dependencies**:

   ```bash
   pip install -e .[dev]
   ```
4. **Configure Environment Variables**:
   Copy the example template and fill in your local system coordinates and credentials:

   ```bash
   cp .env.example .env
   ```

   *Note: Fill in the `DATABASE_URL` (with PostGIS enabled on the target DB), `REDIS_URL`, and SMTP credentials for emails.*
5. **Run Database Migrations**:
   Apply the database schema schemas using Alembic:

   ```bash
   alembic upgrade head
   ```
6. **Run the Web Application**:
   Start the FastAPI application development server:

   ```bash
   uvicorn app.main:app --reload
   ```

   The Swagger documentation page will be accessible at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📬 Celery Background Workers

Background tasks require a running Redis instance and a Celery worker.

* **Run the Worker**:
  ```bash
  celery -A app.tasks.celery_app.celery_app worker --loglevel=info
  ```
* **Run the Beat Scheduler (for periodic reminders)**:
  ```bash
  celery -A app.tasks.celery_app.celery_app beat --loglevel=info
  ```
* **Start the Flower Task Monitor (Optional)**:
  ```bash
  celery -A app.tasks.celery_app.celery_app flower --port=5555
  ```

  Visit the dashboard at [http://localhost:5555](http://localhost:5555) to view tasks processing in real time.

---

## 🧪 Testing

The project uses `pytest` alongside `pytest-asyncio` for full integration coverage.

Run the tests using the virtual environment module runner:

```bash
# Windows
.venv\Scripts\python -m pytest

# macOS/Linux
.venv/bin/python -m pytest
```

To run with coverage reporting:

```bash
.venv\Scripts\python -m pytest --cov=app tests/
```
#   B l o o d _ D o n a t i o n _ B a c k e n d  
 